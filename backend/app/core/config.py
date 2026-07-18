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


settings = Settings()
