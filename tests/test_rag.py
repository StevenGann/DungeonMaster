"""Tests for RAG chunking and store (ChromaDB with in-memory or temp persist)."""

import sys

import pytest

from dungeonmaster.ai.rag import _chunk_text, RAGStore
from dungeonmaster.data.vault import Vault

# ChromaDB/pydantic may be incompatible with Python 3.14+
pytestmark = pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="ChromaDB not yet compatible with Python 3.14+",
)


def test_chunk_text_empty():
    assert _chunk_text("") == []
    assert _chunk_text("   ") == []


def test_chunk_text_small():
    assert _chunk_text("hello", chunk_size=10) == ["hello"]


def test_chunk_text_with_overlap():
    text = "a" * 600
    chunks = _chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 5
    assert all(len(c) <= 100 for c in chunks)


@pytest.mark.asyncio
async def test_rag_ingest_and_query(tmp_path):
    """Use EphemeralClient to avoid PersistentClient SQLite hang in CI."""
    import chromadb

    vault = Vault(tmp_path)
    vault.ensure_all_dirs()
    (vault.systems_dir() / "rules.md").write_text(
        "Strength checks use d20. Dexterity saves are common for traps."
    )

    async def embed_fn(texts):
        return [[0.1] * 64 for _ in texts]

    # In-memory client avoids PersistentClient migration/lock hangs on CI
    ephemeral = chromadb.EphemeralClient()
    rag = RAGStore(
        vault=vault,
        embed_fn=embed_fn,
        chunk_size=100,
        chunk_overlap=0,
        top_k=2,
        chroma_client=ephemeral,
    )
    n = await rag.ingest_path(vault.systems_dir() / "rules.md")
    assert n >= 1
    results = await rag.query("strength check")
    assert len(results) >= 1
    assert any("Strength" in r or "d20" in r for r in results)
