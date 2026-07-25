import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 0.5


async def wait_for_postgres(
    max_retries: int = MAX_RETRIES,
    backoff_base: float = BACKOFF_BASE,
) -> bool:
    if settings.is_sqlite:
        logger.info("SQLite in use — skipping PostgreSQL health check")
        return True

    url = settings.DATABASE_URL
    if "+" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    kwargs = {"echo": False, "pool_size": 1, "max_overflow": 0}

    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    ssl_required = "ssl=require" in url or "sslmode=require" in url

    ssl_mode = settings.DATABASE_SSL
    if ssl_required:
        kwargs["connect_args"] = {"ssl": "require"}
    elif ssl_mode and ssl_mode.lower() not in ("disable", ""):
        kwargs["connect_args"] = {"ssl": ssl_mode}
    else:
        kwargs["connect_args"] = {}

    engine = create_async_engine(url, **kwargs)
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL ready after %d attempt(s)", attempt)
            await engine.dispose()
            return True
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                wait = backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "PostgreSQL not ready (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt, max_retries, e, wait,
                )
                await asyncio.sleep(wait)

    await engine.dispose()

    if ssl_required or (ssl_mode and ssl_mode.lower() != "disable"):
        logger.warning(
            "PostgreSQL at %s rejected SSL — try setting DATABASE_SSL=disable or "
            "check your server's SSL configuration",
            settings.database_display_url,
        )

    logger.error(
        "PostgreSQL not available after %d retries: %s",
        max_retries, last_exception,
    )
    return False


async def wait_for_qdrant(
    max_retries: int = MAX_RETRIES,
    backoff_base: float = BACKOFF_BASE,
) -> None:
    import httpx

    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.QDRANT_URL}/health")
                if response.status_code < 500:
                    logger.info("Qdrant ready after %d attempt(s)", attempt)
                    return
                last_exception = Exception(f"Qdrant returned status {response.status_code}")
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                wait = backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Qdrant not ready (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt, max_retries, e, wait,
                )
                await asyncio.sleep(wait)

    raise ConnectionError(
        f"Qdrant not available after {max_retries} retries: {last_exception}"
    )


async def wait_for_dependencies() -> None:
    pg_ok = await wait_for_postgres()
    if not pg_ok and settings.is_postgres:
        if settings.DEBUG or settings.HOST in ("0.0.0.0", "127.0.0.1", "localhost"):
            from app.core.database import switch_to_sqlite
            logger.warning(
                "PostgreSQL unavailable and running locally — "
                "automatically falling back to SQLite"
            )
            switch_to_sqlite()
        else:
            raise ConnectionError(
                f"PostgreSQL not available after {MAX_RETRIES} retries in "
                f"non-local environment — cannot proceed"
            )

    if settings.is_sqlite:
        logger.info("SQLite in use — skipping Qdrant dependency check")
    else:
        try:
            await wait_for_qdrant()
        except Exception as e:
            logger.warning("Qdrant not available at startup: %s (continuing anyway)", e)

    logger.info("All service dependencies ready")
