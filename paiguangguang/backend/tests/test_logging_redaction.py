from __future__ import annotations

import json

from app.core import logging as logging_module


def test_log_event_redacts_sensitive_keys_and_nested_values(monkeypatch) -> None:
    captured: list[str] = []

    monkeypatch.setattr(logging_module._LOGGER, "info", lambda message: captured.append(message))

    logging_module.log_event(
        "security.test",
        authorization="Bearer abc123",
        api_key="key-123",
        token="token-123",
        password="secret-123",
        redis_url="redis://user:pass@redis.internal:6379/0",
        callback="https://user:pass@example.com/callback",
        nested={
            "Authorization": "Bearer nested",
            "items": [
                {"Api_Key": "nested-key", "value": "kept"},
                "https://public.example.com/plain",
                "https://user:pass@example.com/secure",
            ],
            "details": {"PASSWORD": "nested-password", "visible": "yes"},
        },
        safe_list=["alpha", {"visible": "beta"}],
    )

    assert len(captured) == 1
    payload = json.loads(captured[0])

    assert payload["authorization"] == "[redacted]"
    assert payload["api_key"] == "[redacted]"
    assert payload["token"] == "[redacted]"
    assert payload["password"] == "[redacted]"
    assert payload["redis_url"] == "[redacted]"
    assert payload["callback"] == "https://***:***@example.com/callback"
    assert payload["nested"]["Authorization"] == "[redacted]"
    assert payload["nested"]["items"][0]["Api_Key"] == "[redacted]"
    assert payload["nested"]["items"][0]["value"] == "kept"
    assert payload["nested"]["items"][1] == "https://public.example.com/plain"
    assert payload["nested"]["items"][2] == "https://***:***@example.com/secure"
    assert payload["nested"]["details"]["PASSWORD"] == "[redacted]"
    assert payload["nested"]["details"]["visible"] == "yes"
    assert payload["safe_list"][0] == "alpha"
    assert payload["safe_list"][1]["visible"] == "beta"
    assert "Bearer abc123" not in captured[0]
    assert "user:pass@" not in captured[0]
