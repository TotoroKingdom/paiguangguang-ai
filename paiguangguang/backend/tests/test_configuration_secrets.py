from __future__ import annotations

import re
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE_PATHS = [
    BACKEND_DIR / ".env.example",
    BACKEND_DIR / "dev.env",
    BACKEND_DIR / "prod.env",
]
CREDENTIAL_URL_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@")
RAW_API_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9._-]+\b")


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    return values


def test_backend_env_files_do_not_ship_raw_secrets() -> None:
    expected_values = {
        "JWT_SECRET_KEY": "replace-me-with-a-long-random-secret",
        "ADMIN_USER_PASSWORD": "replace-me-with-a-strong-password",
        "DASHSCOPE_API_KEY": "replace-me-with-a-dashscope-api-key",
        "DEEPSEEK_API_KEY": "replace-me-with-a-deepseek-api-key",
    }

    for path in ENV_FILE_PATHS:
        content = path.read_text(encoding="utf-8")
        values = _parse_env_file(path)

        assert not RAW_API_KEY_RE.search(content), f"{path} contains a raw API key"
        assert not CREDENTIAL_URL_RE.search(content), f"{path} contains a credentialed database URL"
        assert values["DATABASE_URL"] == "postgresql+psycopg://localhost/knowledge_rag_agent?sslmode=require"
        assert values["TEST_DATABASE_URL"] == "postgresql+psycopg://localhost/knowledge_rag_agent_test?sslmode=require"

        for key, expected_value in expected_values.items():
            assert values[key] == expected_value
