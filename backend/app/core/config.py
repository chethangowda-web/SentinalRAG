from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "SentinelRAG"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinelrag"
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
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
    EMBEDDING_BATCH_SIZE: int = 32
    QDRANT_COLLECTION: str = "documents"


settings = Settings()
