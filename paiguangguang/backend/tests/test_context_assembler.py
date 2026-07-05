from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.context_assembler import ContextAssembler
from app.services.hybrid_retrieval import HybridRetrievalHit
from app.storage.rag_documents import RagChunkRecord, RagDocumentRecord, RagDocumentRepository


def _create_repository(tmp_path, filename: str = "context-assembler.sqlite3") -> RagDocumentRepository:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return RagDocumentRepository(session_factory=session_factory)


def _seed_document(repository: RagDocumentRepository, *, document_id: str, chunks: list[str]) -> None:
    repository.upsert_document(
        RagDocumentRecord(
            document_id=document_id,
            title=f"Title {document_id}",
            text="\n".join(chunks),
            content_hash=f"hash-{document_id}",
            owner_user_id="user-1",
            workspace_id="workspace-1",
            permission_scope="workspace",
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
                chunk_id=f"{document_id}-chunk-{index:04d}",
                document_id=document_id,
                chunk_index=index,
                text=text,
                start_char=index * 10,
                end_char=index * 10 + len(text),
                page_number=1,
                metadata={"chunk_index": index, "start_char": index * 10, "end_char": index * 10 + len(text)},
            )
            for index, text in enumerate(chunks)
        ],
    )


def _make_hit(document_id: str, chunk_index: int, text: str, *, score: float = 0.9, rerank_score: float | None = None):
    return HybridRetrievalHit(
        doc_id=document_id,
        chunk_id=f"{document_id}-chunk-{chunk_index:04d}",
        title=f"Title {document_id}",
        page_number=1,
        chunk_index=chunk_index,
        text=text,
        score=score,
        start_char=chunk_index * 10,
        end_char=chunk_index * 10 + len(text),
        metadata={
            "doc_id": document_id,
            "chunk_id": f"{document_id}-chunk-{chunk_index:04d}",
            "title": f"Title {document_id}",
            "page_number": 1,
            "chunk_index": chunk_index,
            "workspace_id": "workspace-1",
            "permission_scope": "workspace",
            "start_char": chunk_index * 10,
            "end_char": chunk_index * 10 + len(text),
        },
        rerank_score=rerank_score,
        route_scores={"vector": score},
    )


def test_context_assembler_deduplicates_primary_hits(tmp_path) -> None:
    repository = _create_repository(tmp_path)
    _seed_document(repository, document_id="doc-alpha", chunks=["Alpha first chunk", "Alpha second chunk"])
    assembler = ContextAssembler(repository=repository, include_adjacent_chunks=False, max_context_chars=500)

    result = assembler.assemble([
        _make_hit("doc-alpha", 0, "Alpha first chunk"),
        _make_hit("doc-alpha", 0, "Alpha first chunk"),
    ])

    assert result.truncated is False
    assert [source.chunk_id for source in result.selected_sources] == ["doc-alpha-chunk-0000"]
    assert result.context_text.count("doc-alpha-chunk-0000") == 1


def test_context_assembler_includes_adjacent_chunks_within_budget(tmp_path) -> None:
    repository = _create_repository(tmp_path)
    _seed_document(repository, document_id="doc-alpha", chunks=["Chunk zero", "Chunk one", "Chunk two"])
    assembler = ContextAssembler(repository=repository, include_adjacent_chunks=True, adjacent_chunk_window=1, max_context_chars=2000)

    result = assembler.assemble([
        _make_hit("doc-alpha", 1, "Chunk one", rerank_score=0.8),
    ])

    assert [source.chunk_id for source in result.selected_sources] == [
        "doc-alpha-chunk-0000",
        "doc-alpha-chunk-0001",
        "doc-alpha-chunk-0002",
    ]
    assert "selection=primary" in result.context_text
    assert "selection=adjacent" in result.context_text
    assert result.truncated is False


def test_context_assembler_enforces_context_budget(tmp_path) -> None:
    repository = _create_repository(tmp_path)
    _seed_document(repository, document_id="doc-alpha", chunks=["A" * 20, "B" * 20, "C" * 20])
    assembler = ContextAssembler(repository=repository, include_adjacent_chunks=False, adjacent_chunk_window=1, max_context_chars=400)

    result = assembler.assemble([
        _make_hit("doc-alpha", 0, "A" * 20),
        _make_hit("doc-alpha", 1, "B" * 20),
    ])

    assert result.total_characters <= 400
    assert len(result.selected_sources) == 1
    assert result.selected_sources[0].chunk_id == "doc-alpha-chunk-0000"
    assert result.truncated is True
