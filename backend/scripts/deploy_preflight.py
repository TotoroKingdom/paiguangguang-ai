"""Validate production deployment environment without printing secret values."""

from __future__ import annotations

import os
from collections.abc import Mapping


REQUIRED_PRODUCTION_ENVIRONMENT = (
    "ASSISTANT_OWNER_COOKIE_SECRET",
    "ASSISTANT_ALLOWED_ORIGINS",
    "ASSISTANT_LLM_PROVIDER",
    "ASSISTANT_LLM_BASE_URL",
    "ASSISTANT_LLM_MODEL",
    "ASSISTANT_LLM_API_KEY",
)


def missing_required_environment(environment: Mapping[str, str | None]) -> list[str]:
    return [
        name
        for name in REQUIRED_PRODUCTION_ENVIRONMENT
        if not str(environment.get(name) or "").strip()
    ]


def validate_environment(environment: Mapping[str, str | None]) -> None:
    missing = missing_required_environment(environment)
    if missing:
        raise RuntimeError(
            "missing required production configuration: " + ", ".join(missing)
        )
    if str(environment.get("ASSISTANT_ENVIRONMENT", "")).strip().lower() not in {
        "production",
        "prod",
    }:
        raise RuntimeError("ASSISTANT_ENVIRONMENT must be production")


def main() -> None:
    validate_environment(os.environ)
    from app.config import settings

    settings.validate_runtime()
    print("deployment preflight passed")


if __name__ == "__main__":
    main()
