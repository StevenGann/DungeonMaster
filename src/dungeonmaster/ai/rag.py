"""
RAG (Retrieval-Augmented Generation) store for system-agnostic rules and lore.

Reads Markdown/TXT from the vault's systems/ directory, chunks with a sliding
window, embeds via an async embed_fn (e.g. Ollama), and stores vectors in ChromaDB
(persisted under vault/_index/chroma). Query returns the top-k most similar
chunks for a given string, for injection into the DM's system prompt.
"""

from pathlib import Path
from typing import Callable, Awaitable

from dungeonmaster.data.vault import Vault


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Sliding-window chunking by character count. Overlap characters are shared between adjacent chunks."""
    if not text or chunk_size <= 0:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
        if start >= len(text):
            break
    return chunks


class RAGStore:
    """
    Ingest Markdown/TXT from vault systems/, chunk, embed, store in ChromaDB.
    Retrieve relevant chunks for a query (system-agnostic rule context).
    """

    def __init__(
        self,
        vault: Vault,
        embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        top_k: int = 5,
        collection_name: str = "dungeonmaster_systems",
    ):
        self._vault = vault
        self._embed_fn = embed_fn
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._top_k = top_k
        self._collection_name = collection_name
        persist_dir = str(vault.index_dir() / "chroma")
        import chromadb
        from chromadb.config import Settings
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "System rulebooks and source content"},
        )

    def _chunk_file(self, path: Path) -> list[tuple[str, str]]:
        """Return list of (chunk_text, source_path) for a file."""
        try:
            text = self._vault.read_text(path)
        except Exception:
            return []
        chunks = _chunk_text(
            text,
            chunk_size=self._chunk_size,
            overlap=self._chunk_overlap,
        )
        return [(c, str(path)) for c in chunks]

    async def ingest_path(self, path: Path) -> int:
        """
        Ingest one file: chunk, embed, add to ChromaDB. Returns number of chunks added.
        """
        pairs = self._chunk_file(path)
        if not pairs:
            return 0
        texts = [p[0] for p in pairs]
        embeddings = await self._embed_fn(texts)
        if len(embeddings) != len(texts):
            return 0
        ids = [f"{path.stem}_{i}" for i in range(len(texts))]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"source": p[1]} for p in pairs],
        )
        return len(texts)

    async def ingest_all(self) -> int:
        """Ingest all system files from the vault. Returns total chunks added."""
        files = self._vault.list_system_files()
        total = 0
        for path in files:
            total += await self.ingest_path(path)
        return total

    async def query(self, query_text: str, top_k: int | None = None) -> list[str]:
        """
        Retrieve top_k most relevant chunks for the query. Returns list of chunk texts.
        """
        k = top_k if top_k is not None else self._top_k
        if k <= 0:
            return []
        query_emb = await self._embed_fn([query_text])
        if not query_emb:
            return []
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(
            query_embeddings=query_emb,
            n_results=min(k, count),
            include=["documents"],
        )
        docs = results.get("documents")
        if not docs or not docs[0]:
            return []
        return list(docs[0])

    def delete_by_source(self, source_path: str) -> None:
        """Remove all chunks that came from the given source path (for re-ingestion)."""
        # ChromaDB filter by metadata
        existing = self._collection.get(include=["metadatas"])
        ids_to_delete = [
            id_
            for id_, meta in zip(
                existing["ids"],
                existing["metadatas"] or [],
            )
            if (meta or {}).get("source") == source_path
        ]
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
