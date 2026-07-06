from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagSearchHit:
    doc_id: str
    chunk_id: str
    title: str | None
    page_number: int | None
    chunk_index: int
    text: str
    score: float
    start_char: int
    end_char: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class RagSearchAccessContext:
    workspace_id: str | None = None
    user_id: str | None = None
    is_system_admin: bool = False
    allowed_permission_scopes: tuple[str, ...] = ("workspace",)
    allow_legacy_metadata: bool = False


def normalize_rag_search_metadata(chunk_id: str, metadata: dict[str, object] | None) -> dict[str, object]:
    metadata = dict(metadata or {})
    doc_id = metadata.get("doc_id") or metadata.get("document_id") or _derive_doc_id(chunk_id)
    title = metadata.get("title") or None
    page_number = metadata.get("page_number")
    chunk_index = metadata.get("chunk_index")
    start_char = metadata.get("start_char")
    end_char = metadata.get("end_char")
    permission_scope = metadata.get("permission_scope") or None
    workspace_id = metadata.get("workspace_id") or None
    owner_user_id = metadata.get("owner_user_id") or None
    original_filename = metadata.get("original_filename") or None
    content_hash = metadata.get("content_hash") or None
    kb_version = metadata.get("kb_version")
    lifecycle_version = metadata.get("lifecycle_version")
    normalized = {
        "doc_id": str(doc_id),
        "title": title,
        "page_number": int(page_number) if page_number not in (None, "") else 1,
        "chunk_index": int(chunk_index) if chunk_index not in (None, "") else 0,
        "start_char": int(start_char) if start_char not in (None, "") else 0,
        "end_char": int(end_char) if end_char not in (None, "") else 0,
        "permission_scope": permission_scope,
        "workspace_id": workspace_id,
        "owner_user_id": owner_user_id,
        "original_filename": original_filename,
        "content_hash": content_hash,
        "kb_version": int(kb_version) if kb_version not in (None, "") else int(lifecycle_version) if lifecycle_version not in (None, "") else 1,
        "lifecycle_version": int(lifecycle_version) if lifecycle_version not in (None, "") else 1,
        "chunk_id": str(chunk_id),
    }
    normalized.update(metadata)
    return normalized


def is_rag_search_accessible(
    metadata: dict[str, object],
    access_context: RagSearchAccessContext | None,
) -> bool:
    if access_context is None:
        return True

    workspace_id = metadata.get("workspace_id")
    permission_scope = metadata.get("permission_scope")
    if workspace_id in (None, "") or permission_scope in (None, ""):
        return access_context.allow_legacy_metadata

    if access_context.is_system_admin:
        return True

    if access_context.workspace_id is not None and str(workspace_id) != access_context.workspace_id:
        return False

    return str(permission_scope) in access_context.allowed_permission_scopes


def _derive_doc_id(chunk_id: str) -> str:
    if "-chunk-" in chunk_id:
        return chunk_id.rsplit("-chunk-", 1)[0]
    return chunk_id
