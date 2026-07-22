import asyncio
import logging
import time
from functools import partial
from typing import Any

from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.core.qdrant import get_qdrant_client
from app.services.embedding_service import generate_embeddings

logger = logging.getLogger(__name__)


class VectorSearchResult:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        score: float,
        page_number: int | None = None,
        section: str | None = None,
        filename: str | None = None,
        chunk_index: int | None = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.score = score
        self.page_number = page_number
        self.section = section
        self.filename = filename
        self.chunk_index = chunk_index


def search_vector(query_text: str, top_k: int = 20) -> list[VectorSearchResult]:
    start = time.perf_counter()

    embed_start = time.perf_counter()
    vectors = generate_embeddings([query_text])
    embed_elapsed = round((time.perf_counter() - embed_start) * 1000, 1)

    if not vectors:
        logger.warning("Embedding generation returned empty result")
        return []

    vector = vectors[0]

    search_start = time.perf_counter()
    client = get_qdrant_client()

    try:
        results = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
            score_threshold=0.0,
        )
    except UnexpectedResponse as e:
        logger.error("Qdrant search failed: %s", e)
        return []

    search_elapsed = round((time.perf_counter() - search_start) * 1000, 1)
    total_elapsed = round((time.perf_counter() - start) * 1000, 1)

    logger.info(
        "Vector search: embed=%.1fms search=%.1fms total=%.1fms returned=%d",
        embed_elapsed, search_elapsed, total_elapsed, len(results),
    )

    parsed: list[VectorSearchResult] = []
    for res in results:
        payload: dict[str, Any] = res.payload or {}
        parsed.append(VectorSearchResult(
            chunk_id=payload.get("chunk_id", ""),
            document_id=payload.get("document_id", ""),
            text=payload.get("text", ""),
            score=round(float(res.score), 4),
            page_number=payload.get("page_number"),
            section=payload.get("section"),
            filename=payload.get("filename"),
            chunk_index=payload.get("chunk_index"),
        ))

    return parsed


async def search_vector_async(query_text: str, top_k: int = 20) -> list[VectorSearchResult]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(search_vector, query_text, top_k))
