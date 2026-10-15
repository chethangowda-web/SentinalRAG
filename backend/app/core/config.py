import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "change-me-in-production"


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

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = ""
    DATABASE_SSL: str = "disable"
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    SECRET_KEY: str = _DEFAULT_SECRET_KEY

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    LOG_LEVEL: str = "INFO"

    UPLOAD_DIR: Path = Path("uploads")
    PROCESSED_DIR: Path = Path("processed")
    MAX_FILE_SIZE: int = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".png", ".jpg", ".jpeg"}
    ALLOWED_CONTENT_TYPES: set[str] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }
    OCR_LANGUAGE: str = "eng"
    TEXT_MIN_LENGTH_FOR_PDF: int = 50

    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 50
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 24
    QDRANT_COLLECTION: str = "documents"
    # Load the embedding and reranker models at startup instead of on first use.
    # Off by default: both models together need ~1 GB RAM, which small hosts can't spare.
    PRELOAD_MODELS: bool = False

    # Directory holding the exported frontend to serve at "/" (default: ./static if it exists)
    FRONTEND_DIST: str = ""

    # Google Gemini (preferred when its key is set), via Google's OpenAI-compatible endpoint
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # gemini-3.1-flash-lite has a far higher free-tier request limit than gemini-2.5-flash (5/min)
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    # Tried in order when GEMINI_MODEL has used up its daily quota (each model has its own allowance).
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash-lite,gemini-3.5-flash"

    # DeepSeek (fallback LLM provider)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1
    MAX_RETRIES: int = 2

    # Featherless (alternative LLM provider, used before DeepSeek if set)
    FEATHERLESS_API_KEY: str = ""
    FEATHERLESS_BASE_URL: str = ""
    FEATHERLESS_MODEL: str = ""

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440

    # Comma-separated emails allowed to see global metrics and change settings
    ADMIN_EMAILS: str = ""

    LLM_MAX_TOKENS: int = 1024
    # Simultaneous in-flight LLM calls; keeps bursts from tripping per-minute limits.
    LLM_MAX_CONCURRENCY: int = 4
    # Remember generated answers for identical question + retrieved-passage sets (entries).
    ANSWER_CACHE_SIZE: int = 256

    # Index (chunk + embed) a document in the background right after upload.
    AUTO_INDEX_ON_UPLOAD: bool = True
    # Run the per-document quality evaluation after indexing. Off by default: it spends ~8 LLM calls per upload.
    AUTO_EVALUATE_ON_UPLOAD: bool = False

    # Abuse protection. Registration is open by default; set REGISTRATION_CODE to require an invite.
    REGISTRATION_CODE: str = ""
    MAX_DOCUMENTS_PER_USER: int = 25
    MAX_STORAGE_MB_PER_USER: int = 200
    MAX_CHATS_PER_USER_PER_DAY: int = 100
    REGISTER_LIMIT_PER_HOUR: int = 5       # sign-ups per client IP
    LOGIN_FAILURES_PER_10_MIN: int = 8     # failed logins per client IP and per email
    # Optional reasoning_effort passed to the LLM (e.g. "none" to stop Gemini spending tokens on hidden thinking)
    LLM_REASONING_EFFORT: str = ""

    @property
    def admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    @property
    def effective_jwt_secret(self) -> str:
        return self.JWT_SECRET or self.SECRET_KEY

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def llm_provider(self) -> str:
        """Which provider the LLM calls use: gemini, featherless, deepseek, or none."""
        if self.GEMINI_API_KEY:
            return "gemini"
        if self.FEATHERLESS_API_KEY:
            return "featherless"
        if self.DEEPSEEK_API_KEY:
            return "deepseek"
        return "none"

    @property
    def effective_llm_api_key(self) -> str:
        return self.GEMINI_API_KEY or self.FEATHERLESS_API_KEY or self.DEEPSEEK_API_KEY

    @property
    def effective_llm_base_url(self) -> str:
        # Base URL and model follow the provider whose key is in use, never a different one's.
        if self.llm_provider == "gemini":
            return self.GEMINI_BASE_URL
        if self.llm_provider == "featherless":
            return self.FEATHERLESS_BASE_URL or self.DEEPSEEK_BASE_URL
        return self.DEEPSEEK_BASE_URL

    @property
    def effective_llm_model(self) -> str:
        if self.llm_provider == "gemini":
            return self.GEMINI_MODEL
        if self.llm_provider == "featherless":
            return self.FEATHERLESS_MODEL or self.LLM_MODEL
        return self.LLM_MODEL

    @property
    def llm_model_candidates(self) -> list[str]:
        """Models to try, in order. Only Gemini has configurable fallbacks."""
        primary = self.effective_llm_model
        if self.llm_provider != "gemini":
            return [primary] if primary else []
        extras = [m.strip() for m in self.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]
        return [primary] + [m for m in extras if m != primary]

    @property
    def effective_llm_reasoning_effort(self) -> str:
        return self.LLM_REASONING_EFFORT

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite") or not self.DATABASE_URL

    @property
    def database_display_url(self) -> str:
        if not self.DATABASE_URL:
            return "sqlite+aiosqlite:///./sentinelrag.db (default, no env override)"
        import re as _re
        return _re.sub(r"(://[^:]+:)[^@]+@", r"\1****@", self.DATABASE_URL)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY is required. Set it in .env or environment variables.")
        elif not self.JWT_SECRET and (self.SECRET_KEY == _DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32):
            # SECRET_KEY signs the JWTs, so a known or short value lets anyone forge tokens.
            errors.append(
                "SECRET_KEY (or JWT_SECRET) must be a random value of at least 32 characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        if not self.effective_llm_api_key:
            errors.append("No LLM API key configured (GEMINI_API_KEY, DEEPSEEK_API_KEY or FEATHERLESS_API_KEY). LLM features will not work.")
        if self.DATABASE_URL and not self.is_postgres and not self.is_sqlite:
            errors.append("DATABASE_URL should use async PostgreSQL or SQLite.")
        return errors


settings = Settings()

if not settings.DATABASE_URL:
    settings.DATABASE_URL = "sqlite+aiosqlite:///./sentinelrag.db"
    logger.info("DATABASE_URL not set — defaulting to SQLite for local development")

_validation_errors = settings.validate()
for e in _validation_errors:
    logger.error("Configuration error: %s", e)
if _validation_errors:
    # A weak signing key lets anyone forge login tokens, so it is fatal on SQLite too
    # (a SQLite deploy can still be public). Only DEBUG tolerates it.
    secret_problem = any("SECRET_KEY" in e for e in _validation_errors)
    if settings.DEBUG or (settings.is_sqlite and not secret_problem):
        logger.warning("Proceeding despite configuration errors (debug/dev mode)")
    else:
        raise SystemExit(
            "Fatal configuration errors detected. Fix them before starting the server.\n"
            + "\n".join(f"  - {e}" for e in _validation_errors)
        )
