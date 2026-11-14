from pathlib import Path

import pytest
from pydantic import SecretStr

from app.config import Settings
from scripts.deploy_preflight import missing_required_environment


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
DOCKERFILE = ROOT / "backend" / "Dockerfile"


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "production",
        "database_url": "sqlite:///./production-check.db",
        "owner_cookie_secret": "x" * 40,
        "owner_cookie_secure": True,
        "admin_cookie_secure": True,
        "user_cookie_secure": True,
        "demo_catalog_enabled": False,
        "allowed_origins": "https://example.com",
        "llm_provider": "openai",
        "llm_base_url": "https://llm.example.com/v1",
        "llm_model": "approved-test-model",
        "llm_api_key": SecretStr("test-key"),
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_blank_real_provider_configuration():
    for field, value in (
        ("llm_base_url", ""),
        ("llm_model", ""),
        ("llm_api_key", SecretStr("")),
    ):
        with pytest.raises(RuntimeError, match="ASSISTANT_LLM_"):
            production_settings(**{field: value}).validate_runtime()


def test_deploy_preflight_identifies_missing_values_without_echoing_secrets():
    environment = {
        "ASSISTANT_ENVIRONMENT": "production",
        "ASSISTANT_OWNER_COOKIE_SECRET": "owner-secret",
        "ASSISTANT_ALLOWED_ORIGINS": "https://example.com",
        "ASSISTANT_LLM_PROVIDER": "openai",
        "ASSISTANT_LLM_BASE_URL": "https://llm.example.com/v1",
        "ASSISTANT_LLM_MODEL": "model",
    }

    assert missing_required_environment(environment) == ["ASSISTANT_LLM_API_KEY"]


def test_deploy_workflow_injects_llm_config_and_preflights_before_start():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for variable in (
        "ASSISTANT_LLM_PROVIDER",
        "ASSISTANT_LLM_BASE_URL",
        "ASSISTANT_LLM_MODEL",
        "ASSISTANT_LLM_API_KEY",
    ):
        assert variable in workflow
        assert f"printf '{variable}=%s\\n' \"${variable}\"" in workflow

    assert "envs: IMAGE_NAME,BACKEND_IMAGE_NAME,DEPLOY_COMMIT,GHCR_USERNAME,GHCR_TOKEN,ASSISTANT_OWNER_COOKIE_SECRET,ASSISTANT_ALLOWED_ORIGINS,ASSISTANT_ADMIN_USERNAME,ASSISTANT_ADMIN_PASSWORD,ASSISTANT_LLM_PROVIDER,ASSISTANT_LLM_BASE_URL,ASSISTANT_LLM_MODEL,ASSISTANT_LLM_API_KEY" in workflow
    assert "docker compose config --quiet" in workflow
    assert "printf 'ASSISTANT_ENVIRONMENT=production\\n'" in workflow
    compose_pull = workflow.index("docker compose pull")
    compose_start = workflow.index("docker compose up -d --remove-orphans", compose_pull)
    assert workflow.index("docker compose config --quiet") < compose_start
    assert "docker inspect paiguangguang-ai-frontend" in workflow
    assert "docker inspect paiguangguang-ai-backend" in workflow


def test_deploy_workflow_requires_joint_backup_before_migration_and_restores_on_failure():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts.backup_restore create" in workflow
    assert "scripts.backup_restore restore" in workflow
    assert "--storage /data/user-files" in workflow
    assert "docker compose stop backend frontend" in workflow
    assert ".rollback-backup-dir" in workflow
    assert "joint SQLite and user-file backup created" in workflow
    assert "refusing to restart an unverified rollback" in workflow
    assert "chown" in workflow and "app:app" in workflow

    backup = workflow.index("scripts.backup_restore create")
    compose_start = workflow.index("docker compose up -d --remove-orphans", backup)
    assert backup < compose_start

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "scripts/backup_restore.py ./scripts/backup_restore.py" in dockerfile

