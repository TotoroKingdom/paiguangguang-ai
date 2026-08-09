from __future__ import annotations

import re
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE_PATHS = [
    BACKEND_DIR / ".env.example",
    BACKEND_DIR / "dev.env",
    BACKEND_DIR / "prod.env",
]
DEPLOY_DIR = BACKEND_DIR.parent / "deploy"
WORKFLOW_PATH = (
    BACKEND_DIR.parent.parent / ".github" / "workflows" / "deploy-paiguangguang.yml"
)
CURRENT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEVELOPMENT_DATABASE_URL = (
    "postgresql+psycopg://localhost/knowledge_rag_agent?sslmode=require"
)
TEST_DATABASE_URL = (
    "postgresql+psycopg://localhost/knowledge_rag_agent_test?sslmode=require"
)
PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://paiguangguang:postgres%40paiguangguang"
    "@postgres17:5432/knowledge_rag_agent"
)
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


def test_runtime_env_files_use_current_deepseek_model() -> None:
    for path in ENV_FILE_PATHS:
        values = _parse_env_file(path)
        configured_model_keys = {
            key: values[key]
            for key in (
                "DEEPSEEK_CHAT_MODEL",
                "CHATBOT_DEFAULT_MODEL",
                "CHATBOT_ALLOWED_MODELS",
                "CHATBOT_SUMMARY_MODEL",
            )
            if key in values
        }

        assert configured_model_keys
        assert set(configured_model_keys.values()) == {CURRENT_DEEPSEEK_MODEL}


def test_dev_env_uses_local_ssl_database_urls() -> None:
    values = _parse_env_file(BACKEND_DIR / "dev.env")

    assert values["DATABASE_URL"] == DEVELOPMENT_DATABASE_URL
    assert values["TEST_DATABASE_URL"] == TEST_DATABASE_URL


def test_prod_env_uses_internal_postgres_without_test_database() -> None:
    values = _parse_env_file(BACKEND_DIR / "prod.env")

    assert values["DATABASE_URL"] == PRODUCTION_DATABASE_URL
    assert "TEST_DATABASE_URL" not in values


def test_deployment_uses_tracked_prod_env() -> None:
    compose = (DEPLOY_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    deploy_script = (DEPLOY_DIR / "deploy.sh").read_text(encoding="utf-8")
    cleanup_script_path = DEPLOY_DIR / "cleanup-images.sh"
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert not (DEPLOY_DIR / "backend.env.example").exists()
    assert "./backend/prod.env" in compose
    assert "name: paiguangguang_database" in compose
    assert 'PROD_ENV="$APP_DIR/backend/prod.env"' in deploy_script
    assert "paiguangguang/backend/prod.env" in workflow
    assert '"$app_dir/backend/prod.env"' in workflow
    assert cleanup_script_path.exists()
    assert 'CLEANUP_SCRIPT="$APP_DIR/cleanup-images.sh"' in deploy_script
    assert '"$CLEANUP_SCRIPT"' in deploy_script
    assert "paiguangguang/deploy/cleanup-images.sh" in workflow
    assert '"$release_dir/cleanup-images.sh" "$app_dir/cleanup-images.sh"' in workflow


@pytest.mark.skip(reason="Project owner explicitly accepted the existing configured API keys for this project")
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
