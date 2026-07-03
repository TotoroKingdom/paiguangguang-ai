from __future__ import annotations

from dataclasses import dataclass

import chromadb

from app.storage.chroma_store import ChromaRagStore
from app.storage.rag_documents import RagChunkRecord


@dataclass(frozen=True)
class FakeEmbeddingProvider:
    dimension: int = 3

    def embed(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "alpha" in lowered else 0.0,
                    1.0 if "beta" in lowered else 0.0,
                    1.0 if "gamma" in lowered else 0.0,
                ]
            )
        return vectors


def test_chroma_store_indexes_and_searches_chunks() -> None:
    client = chromadb.EphemeralClient()
    store = ChromaRagStore(client=client, embedding_provider=FakeEmbeddingProvider())

    chunks = [
        RagChunkRecord(
            chunk_id="doc-1-chunk-0000",
            index=0,
            start_char=0,
            end_char=24,
            text="Alpha system architecture",
        ),
        RagChunkRecord(
            chunk_id="doc-1-chunk-0001",
            index=1,
            start_char=25,
            end_char=48,
            text="Beta deployment notes",
        ),
    ]

    indexed = store.index_ingestion(
        "portfolio_knowledge",
        doc_id="doc-1",
        title="Notes",
        content_hash="hash-1",
        chunks=chunks,
    )

    hits = store.search("portfolio_knowledge", "alpha workflow", top_k=2)

    assert indexed == 2
    assert len(hits) == 2
    assert hits[0].chunk_id == "doc-1-chunk-0000"
    assert hits[0].doc_id == "doc-1"
    assert hits[0].text == "Alpha system architecture"
    assert hits[0].score >= hits[1].score
