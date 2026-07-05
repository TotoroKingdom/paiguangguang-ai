from __future__ import annotations

from dataclasses import dataclass

import chromadb

from app.storage.chroma_store import ChromaRagStore, RagSearchAccessContext
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
    collection_name = "portfolio_knowledge_basic"

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
        collection_name,
        doc_id="doc-1",
        title="Notes",
        content_hash="hash-1",
        chunks=chunks,
    )

    hits = store.search(collection_name, "alpha workflow", top_k=2)

    assert indexed == 2
    assert len(hits) == 2
    assert hits[0].chunk_id == "doc-1-chunk-0000"
    assert hits[0].doc_id == "doc-1"
    assert hits[0].text == "Alpha system architecture"
    assert hits[0].score >= hits[1].score


def test_chroma_store_writes_authorization_and_citation_metadata() -> None:
    client = chromadb.EphemeralClient()
    store = ChromaRagStore(client=client, embedding_provider=FakeEmbeddingProvider())
    collection_name = "portfolio_knowledge_metadata"

    chunks = [
        RagChunkRecord(
            chunk_id="doc-2-chunk-0000",
            index=0,
            start_char=0,
            end_char=24,
            text="Alpha workspace document",
            page_number=3,
            metadata={"chunk_index": 0, "start_char": 0, "end_char": 24},
        )
    ]

    store.index_ingestion(
        collection_name,
        doc_id="doc-2",
        title="Alpha Notes",
        content_hash="hash-2",
        owner_user_id="user-1",
        workspace_id="workspace-1",
        permission_scope="workspace",
        lifecycle_version=7,
        chunks=chunks,
    )

    hits = store.search(collection_name, "alpha workspace", top_k=1)

    assert len(hits) == 1
    assert hits[0].metadata["doc_id"] == "doc-2"
    assert hits[0].metadata["owner_user_id"] == "user-1"
    assert hits[0].metadata["workspace_id"] == "workspace-1"
    assert hits[0].metadata["permission_scope"] == "workspace"
    assert hits[0].metadata["content_hash"] == "hash-2"
    assert hits[0].metadata["page_number"] == 3
    assert hits[0].metadata["chunk_index"] == 0
    assert hits[0].metadata["lifecycle_version"] == 7
    assert hits[0].page_number == 3
    assert hits[0].chunk_index == 0


def test_chroma_store_filters_results_by_access_context() -> None:
    client = chromadb.EphemeralClient()
    store = ChromaRagStore(client=client, embedding_provider=FakeEmbeddingProvider())
    collection_name = "portfolio_knowledge_access"

    store.index_ingestion(
        collection_name,
        doc_id="doc-workspace",
        title="Workspace Notes",
        content_hash="hash-workspace",
        owner_user_id="user-1",
        workspace_id="workspace-1",
        permission_scope="workspace",
        chunks=[
            RagChunkRecord(
                chunk_id="doc-workspace-chunk-0000",
                index=0,
                start_char=0,
                end_char=20,
                text="Alpha workspace data",
            )
        ],
    )
    store.index_ingestion(
        collection_name,
        doc_id="doc-admin",
        title="Admin Notes",
        content_hash="hash-admin",
        owner_user_id="user-2",
        workspace_id="workspace-1",
        permission_scope="admin",
        chunks=[
            RagChunkRecord(
                chunk_id="doc-admin-chunk-0000",
                index=0,
                start_char=0,
                end_char=18,
                text="Alpha admin data",
            )
        ],
    )

    user_hits = store.search(
        collection_name,
        "alpha",
        top_k=5,
        access_context=RagSearchAccessContext(
            workspace_id="workspace-1",
            allowed_permission_scopes=("workspace",),
        ),
    )
    admin_hits = store.search(
        collection_name,
        "alpha",
        top_k=5,
        access_context=RagSearchAccessContext(
            workspace_id="workspace-1",
            is_system_admin=True,
        ),
    )

    assert [hit.doc_id for hit in user_hits] == ["doc-workspace"]
    assert {hit.doc_id for hit in admin_hits} == {"doc-workspace", "doc-admin"}


def test_chroma_store_can_delete_all_chunks_for_a_document() -> None:
    client = chromadb.EphemeralClient()
    store = ChromaRagStore(client=client, embedding_provider=FakeEmbeddingProvider())
    collection_name = "portfolio_knowledge_delete"

    store.index_ingestion(
        collection_name,
        doc_id="doc-delete",
        title="Delete Notes",
        content_hash="hash-delete",
        chunks=[
            RagChunkRecord(
                chunk_id="doc-delete-chunk-0000",
                index=0,
                start_char=0,
                end_char=20,
                text="Alpha delete target",
            )
        ],
    )

    before_delete = store.search(collection_name, "alpha delete", top_k=1)
    store.delete_document(collection_name, doc_id="doc-delete")
    after_delete = store.search(collection_name, "alpha delete", top_k=1)

    assert len(before_delete) == 1
    assert after_delete == []


def test_chroma_store_legacy_metadata_fallback_is_safe() -> None:
    client = chromadb.EphemeralClient()
    store = ChromaRagStore(client=client, embedding_provider=FakeEmbeddingProvider())
    collection_name = "portfolio_knowledge_legacy"
    collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
    collection.upsert(
        ids=["legacy-doc-chunk-0000"],
        documents=["Alpha legacy record"],
        embeddings=[[1.0, 0.0, 0.0]],
        metadatas=[{"doc_id": "legacy-doc"}],
    )

    hits = store.search(
        collection_name,
        "alpha legacy",
        top_k=1,
        access_context=RagSearchAccessContext(
            workspace_id="workspace-legacy",
            allow_legacy_metadata=True,
        ),
    )

    assert len(hits) == 1
    assert hits[0].doc_id == "legacy-doc"
    assert hits[0].metadata["doc_id"] == "legacy-doc"
    assert hits[0].metadata["lifecycle_version"] == 1
    assert hits[0].metadata["page_number"] == 1
