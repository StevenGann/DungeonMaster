"""Tests for RAG chunking and store (ChromaDB with in-memory or temp persist)."""

import os
import sys
import pytest

from dungeonmaster.ai.rag import _chunk_text, RAGStore
from dungeonmaster.data.vault import Vault

# ChromaDB/pydantic may be incompatible with Python 3.14+
pytestmark = pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="ChromaDB not yet compatible with Python 3.14+",
)

# Skip the test that instantiates ChromaDB in CI (can hang for hours on GH runners)
skip_chromadb_in_ci = pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true",
    reason="ChromaDB PersistentClient can hang in GitHub Actions; run RAG store test locally",
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


@skip_chromadb_in_ci
@pytest.mark.asyncio
async def test_rag_ingest_and_query(tmp_path):
    vault = Vault(tmp_path)
    vault.ensure_all_dirs()
    (vault.systems_dir() / "rules.md").write_text(
        "Strength checks use d20. Dexterity saves are common for traps."
    )

    async def embed_fn(texts):
        # Fake embeddings: same dim for each
        return [[0.1] * 64 for _ in texts]

    rag = RAGStore(
        vault=vault,
        embed_fn=embed_fn,
        chunk_size=100,
        chunk_overlap=0,
        top_k=2,
    )
    n = await rag.ingest_path(vault.systems_dir() / "rules.md")
    assert n >= 1
    results = await rag.query("strength check")
    assert len(results) >= 1
    assert any("Strength" in r or "d20" in r for r in results)
