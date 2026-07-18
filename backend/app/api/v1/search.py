import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    start = time.perf_counter()
    result = await retrieval_service.retrieve(body.query, db)
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info("Search endpoint: %.1fms total for query '%s'", elapsed, body.query[:60])

    return SearchResponse(
        query=result.query,
        confidence=result.confidence,
        confidence_level=result.confidence_level,
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                page=r.page_number,
                section=r.section,
                filename=r.filename,
                vector_score=r.vector_score,
                bm25_score=r.bm25_score,
                rerank_score=r.rerank_score,
            )
            for r in result.results
        ],
        latencies=result.latencies,
    )
