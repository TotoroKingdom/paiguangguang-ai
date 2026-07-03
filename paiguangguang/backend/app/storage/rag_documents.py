from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RagDocumentRecord:
    doc_id: str
    title: str | None
    text: str
    content_hash: str


@dataclass(frozen=True)
class RagChunkRecord:
    chunk_id: str
    index: int
    start_char: int
    end_char: int
    text: str


@dataclass(frozen=True)
class RagIngestionRecord:
    doc_id: str
    title: str | None
    chunk_size: int
    chunk_overlap: int
    chunks: list[RagChunkRecord]


class RagDocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, RagDocumentRecord] = {}
        self._ingestions: dict[str, RagIngestionRecord] = {}
        self._lock = Lock()

    def upsert_document(self, document: RagDocumentRecord) -> RagDocumentRecord:
        with self._lock:
            self._documents[document.doc_id] = document
        return document

    def get_document(self, doc_id: str) -> RagDocumentRecord:
        with self._lock:
            document = self._documents.get(doc_id)
        if document is None:
            raise KeyError(doc_id)
        return document

    def upsert_ingestion(self, ingestion: RagIngestionRecord) -> RagIngestionRecord:
        with self._lock:
            self._ingestions[ingestion.doc_id] = ingestion
        return ingestion

    def get_ingestion(self, doc_id: str) -> RagIngestionRecord:
        with self._lock:
            ingestion = self._ingestions.get(doc_id)
        if ingestion is None:
            raise KeyError(doc_id)
        return ingestion

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
            self._ingestions.clear()


_RAG_DOCUMENT_REPOSITORY = RagDocumentRepository()


def get_rag_document_repository() -> RagDocumentRepository:
    return _RAG_DOCUMENT_REPOSITORY
