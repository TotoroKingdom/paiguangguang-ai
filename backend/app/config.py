from functools import lru_cache
from pydantic import SecretStr
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
    admin_session_cookie_name: str = "paiguangguang_admin"
    admin_csrf_cookie_name: str = "paiguangguang_admin_csrf"
    admin_cookie_secure: bool = False
    admin_session_max_age_seconds: int = 60 * 60 * 8
    admin_login_max_attempts: int = 5
    admin_login_window_seconds: int = 300
    admin_login_lock_seconds: int = 900
    admin_username: str = "admin"
    admin_password: SecretStr | None = None

    user_session_cookie_name: str = "paiguangguang_session"
    user_csrf_cookie_name: str = "paiguangguang_csrf"
    user_cookie_secure: bool = False
    user_session_max_age_seconds: int = 60 * 60 * 24 * 7
    status_session_max_age_seconds: int = 60 * 60
    registration_enabled: bool = True
    user_password_min_length: int = 6
    recovery_code_secret: SecretStr | None = None
    demo_catalog_enabled: bool = True
    encryption_key: SecretStr | None = None
    file_storage_dir: str = ""

    register_rate_per_hour: int = 10
    register_rate_per_day: int = 50
    login_rate_per_window: int = 5
    login_ip_rate_per_window: int = 20
    login_rate_window_seconds: int = 900
    recovery_rate_per_hour: int = 5
    recovery_rate_per_day: int = 20

    llm_provider: str = "fake"
    llm_base_url: str = ""
    llm_api_key: SecretStr | None = None
    llm_model: str = ""
    llm_timeout_seconds: int = 120
    llm_daily_request_limit: int = 20
    run_max_steps: int = 6

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
            if not self.admin_cookie_secure:
                raise RuntimeError("ASSISTANT_ADMIN_COOKIE_SECURE must be true in production")
            if not self.database_url.startswith("sqlite:///"):
                raise RuntimeError("ASSISTANT_DATABASE_URL must use SQLite for this release")
            if (
                not self.allowed_origins.strip()
                or "your-domain.example" in self.allowed_origins
                or "your-org" in self.allowed_origins
            ):
                raise RuntimeError("ASSISTANT_ALLOWED_ORIGINS must be set in production")
            if not self.user_cookie_secure:
                raise RuntimeError("ASSISTANT_USER_COOKIE_SECURE must be true in production")
            if self.demo_catalog_enabled:
                raise RuntimeError("ASSISTANT_DEMO_CATALOG_ENABLED must be false in production")
            bootstrap_password = (
                self.admin_password.get_secret_value()
                if self.admin_password
                else ""
            )
            if bootstrap_password and len(bootstrap_password) < 12:
                raise RuntimeError("ASSISTANT_ADMIN_PASSWORD must contain at least 12 characters")

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

    @property
    def recovery_secret(self) -> str:
        if self.recovery_code_secret is not None:
            return self.recovery_code_secret.get_secret_value()
        return self.owner_cookie_secret

    @property
    def encryption_secret(self) -> str:
        if self.encryption_key is not None:
            return self.encryption_key.get_secret_value()
        return self.owner_cookie_secret

    @property
    def storage_root(self) -> str:
        if self.file_storage_dir.strip():
            return self.file_storage_dir.strip()
        base = self.database_path
        if base:
            from pathlib import Path

            return str(Path(base).resolve().parent / "user-files")
        return "user-files"


@lru_cache
def get_settings() -> Settings:
    result = Settings()
    result.validate_runtime()
    return result


settings = get_settings()

