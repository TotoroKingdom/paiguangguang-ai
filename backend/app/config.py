from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "paiguangguang-assistant"
    database_url: str = "sqlite:///./assistant.db"
    owner_cookie_name: str = "paiguangguang_owner"
    owner_cookie_secret: str = "dev-only-change-me"
    owner_cookie_secure: bool = False
    owner_cookie_max_age: int = 60 * 60 * 24 * 365
    max_body_bytes: int = 256 * 1024
    orphan_generation_after_seconds: int = 30
    allowed_origins: str = ""
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASSISTANT_", extra="ignore")

    @property
    def database_path(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return self.database_url.removeprefix("sqlite:///")
        return ""

    def validate_runtime(self) -> None:
        if self.environment.lower() in {"production", "prod"}:
            secret = self.owner_cookie_secret.lower()
            if (
                self.owner_cookie_secret == "dev-only-change-me"
                or len(self.owner_cookie_secret) < 32
                or "replace-with" in secret
                or "change-me" in secret
            ):
                raise RuntimeError("ASSISTANT_OWNER_COOKIE_SECRET must be a strong production secret")
            if not self.owner_cookie_secure:
                raise RuntimeError("ASSISTANT_OWNER_COOKIE_SECURE must be true in production")
            if not self.database_url.startswith("sqlite:///"):
                raise RuntimeError("ASSISTANT_DATABASE_URL must use SQLite for this release")
            if (
                not self.allowed_origins.strip()
                or "your-domain.example" in self.allowed_origins
                or "your-org" in self.allowed_origins
            ):
                raise RuntimeError("ASSISTANT_ALLOWED_ORIGINS must be set in production")

    @property
    def allowed_origin_values(self) -> set[str]:
        configured = {item.strip().rstrip("/") for item in self.allowed_origins.split(",") if item.strip()}
        if configured or self.environment.lower() in {"production", "prod"}:
            return configured
        return {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3100",
            "http://127.0.0.1:3100",
        }


@lru_cache
def get_settings() -> Settings:
    result = Settings()
    result.validate_runtime()
    return result


settings = get_settings()

