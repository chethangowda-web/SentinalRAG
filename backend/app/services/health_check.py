import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 10
BACKOFF_BASE = 0.5


async def wait_for_postgres(
    max_retries: int = MAX_RETRIES,
    backoff_base: float = BACKOFF_BASE,
) -> None:
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        logger.info("SQLite in use, skipping PostgreSQL health check")
        return

    engine = create_async_engine(url, echo=False, pool_size=1, max_overflow=0)
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL ready after %d attempt(s)", attempt)
            await engine.dispose()
            return
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
    raise ConnectionError(
        f"PostgreSQL not available after {max_retries} retries: {last_exception}"
    )


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
    await wait_for_postgres()
    await wait_for_qdrant()
    logger.info("All service dependencies ready")
