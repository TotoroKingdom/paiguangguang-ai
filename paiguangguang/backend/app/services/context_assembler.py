from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.storage.rag_documents import RagChunkRecord, RagDocumentRepository, RagDocumentRecord, get_rag_document_repository
from app.storage.rag_search import normalize_rag_search_metadata
from app.services.hybrid_retrieval import HybridRetrievalHit


@dataclass(frozen=True)
class ContextAssemblyResult:
    context_text: str
    selected_sources: list[HybridRetrievalHit]
    total_characters: int
    truncated: bool


class ContextAssembler:
    def __init__(
        self,
        repository: RagDocumentRepository | None = None,
        *,
        max_context_chars: int = 8000,
        adjacent_chunk_window: int = 1,
        include_adjacent_chunks: bool = True,
    ) -> None:
        self.repository = repository or get_rag_document_repository()
        self.max_context_chars = max_context_chars
        self.adjacent_chunk_window = max(0, adjacent_chunk_window)
        self.include_adjacent_chunks = include_adjacent_chunks

    def assemble(self, hits: Sequence[HybridRetrievalHit]) -> ContextAssemblyResult:
        primary_hits = self._dedupe_hits(hits)
        if not primary_hits:
            return ContextAssemblyResult(
                context_text="No relevant context was retrieved.",
                selected_sources=[],
                total_characters=len("No relevant context was retrieved."),
                truncated=False,
            )

        selected: list[HybridRetrievalHit] = []
        selected_keys: set[tuple[str, str]] = set()
        used_chars = 0
        truncated = False

        for hit in primary_hits:
            tagged_hit = self._tag_hit(hit, "primary")
            if not self._can_fit(tagged_hit, used_chars, selection_type="primary", is_first=not selected):
                truncated = True
                continue
            selected.append(tagged_hit)
            selected_keys.add((tagged_hit.doc_id, tagged_hit.chunk_id))
            used_chars += self._entry_length(tagged_hit, is_first=len(selected) == 1, selection_type="primary")

            if not (self.include_adjacent_chunks and self.adjacent_chunk_window > 0):
                continue

            document = self._get_document(hit.doc_id)
            if document is None:
                continue
            chunk_map = self._chunk_map(hit.doc_id)
            for neighbor in self._neighbor_chunks(document, chunk_map, hit.chunk_index):
                key = (neighbor.doc_id, neighbor.chunk_id)
                if key in selected_keys:
                    continue
                tagged_neighbor = self._tag_hit(neighbor, "adjacent")
                if not self._can_fit(tagged_neighbor, used_chars, selection_type="adjacent", is_first=not selected):
                    truncated = True
                    continue
                selected.append(tagged_neighbor)
                selected_keys.add(key)
                used_chars += self._entry_length(
                    tagged_neighbor,
                    is_first=len(selected) == 1,
                    selection_type="adjacent",
                )

        context_lines: list[str] = []
        total_chars = 0
        for index, hit in enumerate(selected, start=1):
            selection_type = str(hit.metadata.get("context_selection", "primary"))
            line = self._format_hit(index, hit, selection_type=selection_type)
            context_lines.append(line)
            total_chars += len(line)

        context_text = "\n\n".join(context_lines)
        return ContextAssemblyResult(
            context_text=context_text,
            selected_sources=selected,
            total_characters=len(context_text),
            truncated=truncated or total_chars > self.max_context_chars,
        )

    def _dedupe_hits(self, hits: Sequence[HybridRetrievalHit]) -> list[HybridRetrievalHit]:
        deduped: list[HybridRetrievalHit] = []
        seen: set[tuple[str, str]] = set()
        for hit in hits:
            key = (hit.doc_id, hit.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(hit)
        return deduped

    def _can_fit(
        self,
        hit: HybridRetrievalHit,
        used_chars: int,
        *,
        selection_type: str,
        is_first: bool,
    ) -> bool:
        return used_chars + self._entry_length(hit, is_first=is_first, selection_type=selection_type) <= self.max_context_chars

    def _entry_length(self, hit: HybridRetrievalHit, *, is_first: bool, selection_type: str) -> int:
        block = self._format_hit(0, hit, selection_type=selection_type)
        return len(block) if is_first else len(block) + 2

    def _format_hit(self, index: int, hit: HybridRetrievalHit, *, selection_type: str = "primary") -> str:
        title = f" | title={hit.title}" if hit.title else ""
        page = f" | page={hit.page_number}" if hit.page_number is not None else ""
        rerank = f" | rerank={hit.rerank_score:.4f}" if hit.rerank_score is not None else ""
        route_scores = ""
        if hit.route_scores:
            route_pairs = ", ".join(
                f"{route}={score:.4f}" for route, score in sorted(hit.route_scores.items())
            )
            route_scores = f" | routes={route_pairs}"
        selection = f" | selection={selection_type}"
        metadata = f" | metadata={self._format_metadata(hit)}"
        return (
            f"[{index}] doc_id={hit.doc_id} | chunk_id={hit.chunk_id} | chunk_index={hit.chunk_index}"
            f" | score={hit.score:.4f}{rerank}{title}{page}{selection}{route_scores}{metadata}\n"
            f"{hit.text}"
        )

    @staticmethod
    def _tag_hit(hit: HybridRetrievalHit, selection_type: str) -> HybridRetrievalHit:
        metadata = dict(hit.metadata)
        metadata["context_selection"] = selection_type
        return HybridRetrievalHit(
            doc_id=hit.doc_id,
            chunk_id=hit.chunk_id,
            title=hit.title,
            page_number=hit.page_number,
            chunk_index=hit.chunk_index,
            text=hit.text,
            score=hit.score,
            start_char=hit.start_char,
            end_char=hit.end_char,
            metadata=metadata,
            rerank_score=hit.rerank_score,
            route_scores=dict(hit.route_scores),
        )

    @staticmethod
    def _format_metadata(hit: HybridRetrievalHit) -> str:
        metadata = normalize_rag_search_metadata(hit.chunk_id, hit.metadata)
        ordered_keys = [
            "doc_id",
            "workspace_id",
            "permission_scope",
            "owner_user_id",
            "content_hash",
            "lifecycle_version",
            "start_char",
            "end_char",
        ]
        parts = []
        for key in ordered_keys:
            value = metadata.get(key)
            if value not in (None, ""):
                parts.append(f"{key}={value}")
        return "{" + ", ".join(parts) + "}"

    def _get_document(self, document_id: str) -> RagDocumentRecord | None:
        try:
            return self.repository.get_document(document_id)
        except KeyError:
            return None

    def _chunk_map(self, document_id: str) -> dict[int, RagChunkRecord]:
        return {chunk.chunk_index: chunk for chunk in self.repository.get_chunks(document_id)}

    def _neighbor_chunks(
        self,
        document: RagDocumentRecord,
        chunk_map: dict[int, RagChunkRecord],
        anchor_index: int,
    ) -> list[HybridRetrievalHit]:
        neighbors: list[HybridRetrievalHit] = []
        for offset in range(1, self.adjacent_chunk_window + 1):
            for chunk_index in (anchor_index - offset, anchor_index + offset):
                chunk = chunk_map.get(chunk_index)
                if chunk is None:
                    continue
                neighbors.append(self._chunk_to_hit(document, chunk))
        return neighbors

    @staticmethod
    def _chunk_to_hit(document: RagDocumentRecord, chunk: RagChunkRecord) -> HybridRetrievalHit:
        metadata = {
            "doc_id": document.document_id,
            "title": document.title,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "permission_scope": document.permission_scope,
            "workspace_id": document.workspace_id,
            "owner_user_id": document.owner_user_id,
            "content_hash": document.content_hash,
            "lifecycle_version": chunk.metadata.get("lifecycle_version", 1),
            **dict(chunk.metadata),
        }
        return HybridRetrievalHit(
            doc_id=document.document_id,
            chunk_id=chunk.chunk_id,
            title=document.title,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            score=0.0,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            metadata=metadata,
            rerank_score=None,
            route_scores={},
        )


_CONTEXT_ASSEMBLER = ContextAssembler()


def get_context_assembler() -> ContextAssembler:
    return _CONTEXT_ASSEMBLER
