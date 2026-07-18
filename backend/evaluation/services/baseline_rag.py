import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.answer_generator import generate_answer
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)


class BaselineRAG:
    def __init__(self) -> None:
        logger.info("BaselineRAG initialized")

    async def answer(
        self,
        question: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        start = time.perf_counter()

        search_response = await retrieve(question, db)

        chunks = []
        for r in search_response.results:
            chunks.append({
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "text": r.text,
                "page_number": r.page_number,
                "section": r.section,
                "filename": r.filename,
                "vector_score": r.vector_score,
                "bm25_score": r.bm25_score,
                "rerank_score": r.rerank_score,
            })

        answer_text = generate_answer(question, chunks)

        elapsed = round((time.perf_counter() - start) * 1000, 1)

        latencies = dict(search_response.latencies or {})
        latencies["total"] = elapsed

        citations = []
        for c in chunks:
            citations.append({
                "document_id": c.get("document_id", ""),
                "chunk_id": c.get("chunk_id", ""),
                "page": c.get("page_number"),
                "text": c.get("text", "")[:200],
            })

        return {
            "question": question,
            "answer": answer_text,
            "confidence_score": search_response.confidence,
            "confidence_level": search_response.confidence_level,
            "retrieved_chunks": chunks,
            "citations": citations,
            "latencies": latencies,
            "reasoning_path": ["retrieve", "generate_answer"],
            "contradiction_detected": False,
            "contradiction_reason": None,
            "clarification_needed": False,
            "clarification_question": None,
            "retry_count": 0,
        }
