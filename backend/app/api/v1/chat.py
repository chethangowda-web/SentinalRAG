import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.graph.graph_builder import build_graph
from app.graph.state import GraphState
from app.schemas.chat import ChatRequest, ChatResponse, CitationItem

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    start = time.perf_counter()

    if not body.question or not body.question.strip():
        return ChatResponse(
            answer="Please provide a valid question.",
            confidence=0.0,
            confidence_level="LOW",
            reasoning_path=["validation"],
            citations=[],
        )

    graph = _get_graph()

    initial_state: GraphState = {
        "question": body.question.strip(),
        "rewritten_question": None,
        "retrieved_chunks": [],
        "confidence_score": 0.0,
        "confidence_level": "LOW",
        "confidence_reason": None,
        "retry_count": 0,
        "max_retries": 2,
        "contradiction_detected": False,
        "contradiction_reason": None,
        "clarification_needed": False,
        "clarification_question": None,
        "answer": None,
        "citations": [],
        "reasoning_path": [],
        "latencies": {},
    }

    try:
        result = await graph.ainvoke(initial_state, {"configurable": {"db": db}})
    except Exception as e:
        logger.exception("Graph execution failed: %s", e)
        return ChatResponse(
            answer="An error occurred while processing your question. Please try again.",
            confidence=0.0,
            confidence_level="LOW",
            reasoning_path=["error"],
            citations=[],
        )

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Chat endpoint: %.1fms total, path=%s, confidence=%.1f/%s",
        elapsed, result.get("reasoning_path", []),
        result.get("confidence_score", 0), result.get("confidence_level", "LOW"),
    )

    citations = [
        CitationItem(
            document_id=c.get("document_id", ""),
            chunk_id=c.get("chunk_id", ""),
            page=c.get("page"),
            text=c.get("text"),
        )
        for c in result.get("citations", [])
    ]

    return ChatResponse(
        answer=result.get("answer", "") or (
            "I don't have enough evidence to answer this question reliably."
        ),
        confidence=result.get("confidence_score", 0.0),
        confidence_level=result.get("confidence_level", "LOW"),
        reasoning_path=result.get("reasoning_path", []),
        citations=citations,
        clarification_question=result.get("clarification_question"),
        latencies=result.get("latencies"),
    )
