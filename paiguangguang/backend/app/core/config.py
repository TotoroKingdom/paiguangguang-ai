from __future__ import annotations

from dataclasses import dataclass, field
import os


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Paiguangguang Backend"
    api_v1_prefix: str = "/api/v1"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_timeout_seconds: float = 30.0
    cors_allow_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )


def get_settings() -> Settings:
    return Settings(
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_chat_model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
        deepseek_timeout_seconds=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "30")),
        cors_allow_origins=_parse_origins(os.getenv("CORS_ALLOW_ORIGINS")),
    )
