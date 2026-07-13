from __future__ import annotations

from dataclasses import dataclass, field
import os


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Paiguangguang Backend"
    api_v1_prefix: str = "/api/v1"
    database_url: str = ""
    test_database_url: str = ""
    jwt_secret_key: str = "change-me-in-development-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    admin_user_email: str = ""
    admin_user_password: str = ""
    admin_user_display_name: str = "Admin"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_timeout_seconds: float = 30.0
    chatbot_default_model: str = "deepseek-chat"
    chatbot_allowed_models: list[str] = field(default_factory=lambda: ["deepseek-chat"])
    chatbot_conversation_page_size: int = 20
    query_rewrite_enabled: bool = False
    query_rewrite_model: str = ""
    rerank_provider: str = ""
    rerank_model: str = "qwen3-rerank"
    rerank_timeout_seconds: float = 30.0
    embedding_provider: str = "hash"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v1"
    embedding_timeout_seconds: float = 30.0
    document_max_file_size_bytes: int = 10 * 1024 * 1024
    rag_rate_limit_max_requests: int = 30
    rag_rate_limit_window_seconds: int = 60
    redis_url: str = ""
    chroma_path: str = "./chroma"
    rag_collection_name: str = "portfolio_knowledge"
    cors_allow_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", ""),
        test_database_url=os.getenv("TEST_DATABASE_URL", ""),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-development-secret-key"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        admin_user_email=os.getenv("ADMIN_USER_EMAIL", ""),
        admin_user_password=os.getenv("ADMIN_USER_PASSWORD", ""),
        admin_user_display_name=os.getenv("ADMIN_USER_DISPLAY_NAME", "Admin"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_chat_model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
        deepseek_timeout_seconds=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "30")),
        chatbot_default_model=os.getenv("CHATBOT_DEFAULT_MODEL", "deepseek-chat"),
        chatbot_allowed_models=[
            model.strip()
            for model in os.getenv("CHATBOT_ALLOWED_MODELS", "deepseek-chat").split(",")
            if model.strip()
        ],
        chatbot_conversation_page_size=int(os.getenv("CHATBOT_CONVERSATION_PAGE_SIZE", "20")),
        query_rewrite_enabled=_parse_bool(os.getenv("QUERY_REWRITE_ENABLED"), default=False),
        query_rewrite_model=os.getenv("QUERY_REWRITE_MODEL", ""),
        rerank_provider=os.getenv("RERANK_PROVIDER", ""),
        rerank_model=os.getenv("RERANK_MODEL", "qwen3-rerank"),
        rerank_timeout_seconds=float(os.getenv("RERANK_TIMEOUT_SECONDS", "30")),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "hash"),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        dashscope_base_url=os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-v1"),
        embedding_timeout_seconds=float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "30")),
        document_max_file_size_bytes=int(os.getenv("DOCUMENT_MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024))),
        rag_rate_limit_max_requests=int(os.getenv("RAG_RATE_LIMIT_MAX_REQUESTS", "30")),
        rag_rate_limit_window_seconds=int(os.getenv("RAG_RATE_LIMIT_WINDOW_SECONDS", "60")),
        redis_url=os.getenv("REDIS_URL", ""),
        chroma_path=os.getenv("CHROMA_PATH", "./chroma"),
        rag_collection_name=os.getenv("RAG_COLLECTION_NAME", "portfolio_knowledge"),
        cors_allow_origins=_parse_origins(os.getenv("CORS_ALLOW_ORIGINS")),
    )
