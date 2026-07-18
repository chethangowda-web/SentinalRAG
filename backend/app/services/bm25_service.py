import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BM25Result:
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


async def search_bm25(
    query_text: str,
    db: AsyncSession,
    top_k: int = 20,
) -> list[BM25Result]:
    start = time.perf_counter()

    if not query_text.strip():
        return []

    tsquery = " & ".join(
        word for word in query_text.split() if len(word) > 1
    )
    if not tsquery:
        return []

    sql = text("""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.chunk_text,
            c.page_number,
            c.word_count,
            d.filename
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding_status = 'embedded'
          AND to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', :query)
        ORDER BY ts_rank_cd(to_tsvector('english', c.chunk_text), plainto_tsquery('english', :query)) DESC
        LIMIT :limit
    """)

    try:
        result = await db.execute(sql, {"query": query_text, "limit": top_k})
        rows = result.fetchall()
    except Exception as e:
        logger.error("BM25 search failed: %s", e)
        return []

    elapsed = round((time.perf_counter() - start) * 1000, 1)

    parsed: list[BM25Result] = []
    for row in rows:
        parsed.append(BM25Result(
            chunk_id=str(row.chunk_id),
            document_id=str(row.document_id),
            text=row.chunk_text,
            score=row.word_count or 0.0,
            page_number=row.page_number,
            section=None,
            filename=row.filename,
        ))

    if not parsed:
        return []

    max_score = max(r.score for r in parsed) if parsed else 1.0
    if max_score > 0:
        for r in parsed:
            r.score = round(r.score / max_score, 4)

    logger.info(
        "BM25 search: %.1fms returned=%d query='%s'",
        elapsed, len(parsed), query_text[:60],
    )

    return parsed
