from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import json


class ConversationCursorError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ConversationCursor:
    last_message_at: datetime
    conversation_id: str
    status_filter: str | None = None
    version: int = 1


class MemoryCursorError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MemoryCursor:
    updated_at: datetime
    memory_id: str
    status_filter: str | None = None
    memory_type_filter: str | None = None
    conversation_id_filter: str | None = None
    version: int = 1


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def encode_conversation_cursor(cursor: ConversationCursor) -> str:
    payload = {
        "v": cursor.version,
        "last_message_at": _normalize_datetime(cursor.last_message_at).isoformat(),
        "conversation_id": cursor.conversation_id,
        "status_filter": cursor.status_filter,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_conversation_cursor(token: str, *, expected_status_filter: str | None = None) -> ConversationCursor:
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise ConversationCursorError("Invalid conversation cursor") from exc

    if payload.get("v") != 1:
        raise ConversationCursorError("Unsupported conversation cursor version")

    status_filter = payload.get("status_filter")
    if expected_status_filter != status_filter:
        raise ConversationCursorError("Conversation cursor filter mismatch")

    try:
        last_message_at = datetime.fromisoformat(payload["last_message_at"])
    except Exception as exc:  # pragma: no cover - defensive
        raise ConversationCursorError("Invalid conversation cursor timestamp") from exc

    if last_message_at.tzinfo is None:
        last_message_at = last_message_at.replace(tzinfo=timezone.utc)

    conversation_id = payload.get("conversation_id")
    if not isinstance(conversation_id, str) or not conversation_id:
        raise ConversationCursorError("Invalid conversation cursor conversation_id")

    return ConversationCursor(
        last_message_at=last_message_at.astimezone(timezone.utc),
        conversation_id=conversation_id,
        status_filter=status_filter,
        version=1,
    )


def encode_memory_cursor(cursor: MemoryCursor) -> str:
    payload = {
        "v": cursor.version,
        "updated_at": _normalize_datetime(cursor.updated_at).isoformat(),
        "memory_id": cursor.memory_id,
        "status_filter": cursor.status_filter,
        "memory_type_filter": cursor.memory_type_filter,
        "conversation_id_filter": cursor.conversation_id_filter,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_memory_cursor(
    token: str,
    *,
    expected_status_filter: str | None = None,
    expected_memory_type_filter: str | None = None,
    expected_conversation_id_filter: str | None = None,
) -> MemoryCursor:
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise MemoryCursorError("Invalid memory cursor") from exc

    if payload.get("v") != 1:
        raise MemoryCursorError("Unsupported memory cursor version")

    status_filter = payload.get("status_filter")
    memory_type_filter = payload.get("memory_type_filter")
    conversation_id_filter = payload.get("conversation_id_filter")
    if expected_status_filter != status_filter:
        raise MemoryCursorError("Memory cursor filter mismatch")
    if expected_memory_type_filter != memory_type_filter:
        raise MemoryCursorError("Memory cursor filter mismatch")
    if expected_conversation_id_filter != conversation_id_filter:
        raise MemoryCursorError("Memory cursor filter mismatch")

    try:
        updated_at = datetime.fromisoformat(payload["updated_at"])
    except Exception as exc:  # pragma: no cover - defensive
        raise MemoryCursorError("Invalid memory cursor timestamp") from exc

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    memory_id = payload.get("memory_id")
    if not isinstance(memory_id, str) or not memory_id:
        raise MemoryCursorError("Invalid memory cursor memory_id")

    return MemoryCursor(
        updated_at=updated_at.astimezone(timezone.utc),
        memory_id=memory_id,
        status_filter=status_filter,
        memory_type_filter=memory_type_filter,
        conversation_id_filter=conversation_id_filter,
        version=1,
    )
