import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_qdrant_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient as _QdrantClient

        _client = _QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            timeout=30,
        )
        logger.info("Qdrant client initialized: %s", settings.QDRANT_URL)
    return _client


async def close_qdrant_client():
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("Qdrant client closed")
