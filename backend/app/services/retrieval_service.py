import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.services import (
    bm25_service,
    confidence_service,
    hybrid_search_service,
    query_preprocessor,
    reranker_service,
    vector_search_service,
)

logger = logging.getLogger(__name__)

RERANK_TOP_K = 10
FINAL_TOP_K = 5


class SearchResultItem:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        page_number: int | None = None,
        section: str | None = None,
        filename: str | None = None,
        vector_score: float = 0.0,
        bm25_score: float = 0.0,
        fusion_score: float = 0.0,
        rerank_score: float = 0.0,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.page_number = page_number
        self.section = section
        self.filename = filename
        self.vector_score = vector_score
        self.bm25_score = bm25_score
        self.fusion_score = fusion_score
        self.rerank_score = rerank_score


class SearchResponse:
    def __init__(
        self,
        query: str,
        confidence: float,
        confidence_level: str,
        results: list[SearchResultItem],
        latencies: dict[str, float] | None = None,
    ):
        self.query = query
        self.confidence = confidence
        self.confidence_level = confidence_level
        self.results = results
        self.latencies = latencies


async def retrieve(
    raw_query: str,
    db: AsyncSession,
) -> SearchResponse:
    total_start = time.perf_counter()
    latencies: dict[str, float] = {}

    normalized = query_preprocessor.preprocess_query(raw_query)
    if not normalized:
        raise AppException(status_code=400, detail="Query cannot be empty after preprocessing")

    embed_start = time.perf_counter()
    vector_results = await vector_search_service.search_vector_async(normalized, top_k=20)
    latencies["vector_search"] = round((time.perf_counter() - embed_start) * 1000, 1)

    bm25_start = time.perf_counter()
    bm25_results = await bm25_service.search_bm25(normalized, db, top_k=20)
    latencies["bm25_search"] = round((time.perf_counter() - bm25_start) * 1000, 1)

    fusion_start = time.perf_counter()
    hybrid_results: list[hybrid_search_service.HybridResult] = hybrid_search_service.fuse_results(vector_results, bm25_results, top_k=20)
    latencies["fusion"] = round((time.perf_counter() - fusion_start) * 1000, 1)

    if not hybrid_results:
        logger.info("No results found for query: '%s'", normalized)
        return SearchResponse(
            query=normalized,
            confidence=0.0,
            confidence_level="LOW",
            results=[],
            latencies=latencies,
        )

    rerank_start = time.perf_counter()
    texts_to_rerank = [hr.text for hr in hybrid_results[:RERANK_TOP_K]]
    reranked_indices = reranker_service.rerank(normalized, texts_to_rerank, top_k=FINAL_TOP_K)
    latencies["rerank"] = round((time.perf_counter() - rerank_start) * 1000, 1)

    results: list[SearchResultItem] = []
    vector_scores: list[float] = []
    rerank_scores: list[float] = []

    for orig_idx, rerank_score in reranked_indices:
        hr = hybrid_results[orig_idx]
        results.append(SearchResultItem(
            chunk_id=hr.chunk_id,
            document_id=hr.document_id,
            text=hr.text,
            page_number=hr.page_number,
            section=hr.section,
            filename=hr.filename,
            vector_score=hr.vector_score,
            bm25_score=hr.bm25_score,
            fusion_score=hr.rrf_score,
            rerank_score=rerank_score,
        ))
        vector_scores.append(hr.vector_score)
        rerank_scores.append(rerank_score)

    confidence_start = time.perf_counter()
    conf = confidence_service.calculate_confidence(
        vector_scores=vector_scores,
        rerank_scores=rerank_scores,
        total_results=len(results),
    )
    latencies["confidence"] = round((time.perf_counter() - confidence_start) * 1000, 1)

    total_elapsed = round((time.perf_counter() - total_start) * 1000, 1)
    latencies["total"] = total_elapsed

    logger.info(
        "Retrieval pipeline complete: %.1fms total, %d results, confidence=%.1f/%s",
        total_elapsed, len(results), conf.score, conf.level,
    )
    logger.debug("Latency breakdown: %s", latencies)

    return SearchResponse(
        query=normalized,
        confidence=conf.score,
        confidence_level=conf.level,
        results=results,
        latencies=latencies,
    )
