import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "SentinelRAG"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinelrag"
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    SECRET_KEY: str = "change-me-in-production"

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    LOG_LEVEL: str = "INFO"

    UPLOAD_DIR: Path = Path("uploads")
    PROCESSED_DIR: Path = Path("processed")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".png", ".jpg", ".jpeg"}
    ALLOWED_CONTENT_TYPES: set[str] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }
    OCR_LANGUAGE: str = "eng"
    TEXT_MIN_LENGTH_FOR_PDF: int = 50

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 12
    QDRANT_COLLECTION: str = "documents"

    # DeepSeek (primary LLM provider)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1
    MAX_RETRIES: int = 2

    # Featherless (alternative LLM provider, takes priority if set)
    FEATHERLESS_API_KEY: str = ""
    FEATHERLESS_BASE_URL: str = ""
    FEATHERLESS_MODEL: str = ""

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def effective_llm_api_key(self) -> str:
        return self.FEATHERLESS_API_KEY or self.DEEPSEEK_API_KEY

    @property
    def effective_llm_base_url(self) -> str:
        return self.FEATHERLESS_BASE_URL or self.DEEPSEEK_BASE_URL

    @property
    def effective_llm_model(self) -> str:
        return self.FEATHERLESS_MODEL or self.LLM_MODEL

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY is required. Set it in .env or environment variables.")
        if not self.effective_llm_api_key:
            errors.append("No LLM API key configured (DEEPSEEK_API_KEY or FEATHERLESS_API_KEY). LLM features will not work.")
        if not self.DATABASE_URL.startswith("postgresql") and not self.DATABASE_URL.startswith("sqlite"):
            errors.append("DATABASE_URL should use async PostgreSQL or SQLite.")
        return errors


settings = Settings()

_validation_errors = settings.validate()
for e in _validation_errors:
    logger.error("Configuration error: %s", e)
if _validation_errors:
    if settings.DEBUG or settings.DATABASE_URL.startswith("sqlite"):
        logger.warning("Proceeding despite configuration errors (debug/dev mode)")
    else:
        raise SystemExit(
            "Fatal configuration errors detected. Fix them before starting the server.\n"
            + "\n".join(f"  - {e}" for e in _validation_errors)
        )
