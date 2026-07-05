from __future__ import annotations

import json
import logging
from typing import Any


_LOGGER = logging.getLogger("paiguangguang.backend")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **{key: _json_safe(value) for key, value in fields.items()}}
    _LOGGER.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
