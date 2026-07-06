from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.storage.keyword_retriever import KeywordRetriever
from app.storage.rag_documents import RagChunkRecord, RagDocumentRecord, RagDocumentRepository
from app.storage.rag_search import RagSearchAccessContext


def _create_repository(tmp_path, filename: str = "keyword-retriever.sqlite3") -> RagDocumentRepository:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return RagDocumentRepository(session_factory=session_factory)


def _seed_document(
    repository: RagDocumentRepository,
    *,
    document_id: str,
    title: str,
    text: str,
    workspace_id: str | None,
    permission_scope: str | None,
) -> None:
    repository.upsert_document(
        RagDocumentRecord(
            document_id=document_id,
            title=title,
            original_filename=f"{document_id}.txt",
            text=text,
            content_hash=f"hash-{document_id}",
            owner_user_id="user-1",
            workspace_id=workspace_id,
            permission_scope=permission_scope,
            status="indexed",
            parse_status="completed",
            chunk_status="completed",
            embedding_status="completed",
            index_status="completed",
            is_deleted=False,
        )
    )
    repository.replace_chunks(
        document_id,
        [
            RagChunkRecord(
                chunk_id=f"{document_id}-chunk-0000",
                document_id=document_id,
                chunk_index=0,
                text=text,
                start_char=0,
                end_char=len(text),
                page_number=1,
                metadata={"chunk_index": 0, "start_char": 0, "end_char": len(text)},
            )
        ],
    )


def test_keyword_retriever_finds_normal_keywords_and_identifiers(tmp_path) -> None:
    repository = _create_repository(tmp_path)
    retriever = KeywordRetriever(repository)
    _seed_document(
        repository,
        document_id="doc-alpha",
        title="Alpha Notes",
        text="The deployment guide references app/services/rag_query.py and RagQueryService.",
        workspace_id="workspace-1",
        permission_scope="workspace",
    )

    access_context = RagSearchAccessContext(
        workspace_id="workspace-1",
        allowed_permission_scopes=("workspace",),
    )

    keyword_hits = retriever.search(
        "portfolio_knowledge",
        "deployment guide",
        top_k=5,
        access_context=access_context,
    )
    identifier_hits = retriever.search(
        "portfolio_knowledge",
        "app/services/rag_query.py",
        top_k=5,
        access_context=access_context,
    )

    assert [hit.doc_id for hit in keyword_hits] == ["doc-alpha"]
    assert keyword_hits[0].text.startswith("The deployment guide")
    assert [hit.chunk_id for hit in identifier_hits] == ["doc-alpha-chunk-0000"]
    assert identifier_hits[0].metadata["doc_id"] == "doc-alpha"


def test_keyword_retriever_uses_exact_substring_fallback_for_version_strings(tmp_path) -> None:
    repository = _create_repository(tmp_path, "keyword-version.sqlite3")
    retriever = KeywordRetriever(repository)
    _seed_document(
        repository,
        document_id="doc-release",
        title="Release Notes",
        text="The service shipped as v1.2.3 with a compatibility fix.",
        workspace_id="workspace-1",
        permission_scope="workspace",
    )

    hits = retriever.search(
        "portfolio_knowledge",
        "v1.2.3",
        top_k=5,
        access_context=RagSearchAccessContext(
            workspace_id="workspace-1",
            allowed_permission_scopes=("workspace",),
        ),
    )

    assert len(hits) == 1
    assert hits[0].doc_id == "doc-release"
    assert "v1.2.3" in hits[0].text


def test_keyword_retriever_applies_permission_filters(tmp_path) -> None:
    repository = _create_repository(tmp_path, "keyword-permissions.sqlite3")
    retriever = KeywordRetriever(repository)
    _seed_document(
        repository,
        document_id="doc-workspace",
        title="Workspace Notes",
        text="Alpha deployment notes live here.",
        workspace_id="workspace-1",
        permission_scope="workspace",
    )
    _seed_document(
        repository,
        document_id="doc-admin",
        title="Admin Notes",
        text="Alpha deployment notes live here too.",
        workspace_id="workspace-1",
        permission_scope="admin",
    )

    hits = retriever.search(
        "portfolio_knowledge",
        "alpha deployment",
        top_k=5,
        access_context=RagSearchAccessContext(
            workspace_id="workspace-1",
            allowed_permission_scopes=("workspace",),
        ),
    )

    assert [hit.doc_id for hit in hits] == ["doc-workspace"]


def test_direct_match_retriever_prioritizes_original_filename_and_version_strings(tmp_path) -> None:
    repository = _create_repository(tmp_path, "keyword-direct-match.sqlite3")
    retriever = KeywordRetriever(repository)
    _seed_document(
        repository,
        document_id="doc-release",
        title="Release Notes",
        text="Changelog entry with no filename mention in body.",
        workspace_id="workspace-1",
        permission_scope="workspace",
    )
    repository.update_document_lifecycle("doc-release")
    document = repository.get_document("doc-release")
    repository.upsert_document(
        RagDocumentRecord(
            document_id=document.document_id,
            title=document.title,
            original_filename="release-v1.2.3-notes.pdf",
            text=document.text,
            content_hash=document.content_hash,
            owner_user_id=document.owner_user_id,
            workspace_id=document.workspace_id,
            permission_scope=document.permission_scope,
            status=document.status,
            parse_status=document.parse_status,
            chunk_status=document.chunk_status,
            embedding_status=document.embedding_status,
            index_status=document.index_status,
            is_deleted=document.is_deleted,
        )
    )
    repository.replace_chunks(
        document.document_id,
        [
            RagChunkRecord(
                chunk_id=f"{document.document_id}-chunk-0000",
                document_id=document.document_id,
                chunk_index=0,
                text=document.text,
                start_char=0,
                end_char=len(document.text),
                page_number=1,
                metadata={"chunk_index": 0, "start_char": 0, "end_char": len(document.text)},
            )
        ],
    )

    hits = retriever.search_direct_match(
        "portfolio_knowledge",
        "release-v1.2.3-notes.pdf",
        top_k=5,
        access_context=RagSearchAccessContext(
            workspace_id="workspace-1",
            allowed_permission_scopes=("workspace",),
        ),
    )

    assert len(hits) == 1
    assert hits[0].doc_id == "doc-release"
    assert hits[0].metadata["original_filename"] == "release-v1.2.3-notes.pdf"
