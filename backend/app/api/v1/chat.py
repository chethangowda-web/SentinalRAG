import logging
import time
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.graph.graph_builder import build_graph
from app.graph.state import GraphState
from app.schemas.chat import ChatRequest, ChatResponse, CitationItem
from app.services import trace_service

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
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    start = time.perf_counter()
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    if not body.question or not body.question.strip():
        return ChatResponse(
            answer="Please provide a valid question.",
            confidence=0.0,
            confidence_level="LOW",
            reasoning_path=["validation"],
            citations=[],
            trace_id=trace_id,
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
        "trace_id": trace_id,
        "graph_execution": [],
        "retrieval_details": [],
        "confidence_breakdown": None,
        "llm_observability": None,
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
            trace_id=trace_id,
        )

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Chat endpoint: %.1fms total, path=%s, confidence=%.1f/%s",
        elapsed, result.get("reasoning_path", []),
        result.get("confidence_score", 0), result.get("confidence_level", "LOW"),
    )

    citations_raw = result.get("citations", [])
    citations = [
        CitationItem(
            document_id=c.get("document_id", ""),
            chunk_id=c.get("chunk_id", ""),
            page=c.get("page"),
            text=c.get("text"),
        )
        for c in citations_raw
    ]

    execution_path = result.get("reasoning_path", [])
    graph_exec = result.get("graph_execution", [])
    session_timeline = trace_service.build_session_timeline(execution_path, graph_exec)

    retrieval_details = result.get("retrieval_details", [])
    improved = result.get("confidence_improved", False)
    prev_conf = initial_state["confidence_score"]
    current_conf = result.get("confidence_score", 0.0)
    confidence_after_rewrite = current_conf if result.get("rewritten_question") else None

    reason_for_retry = None
    if result.get("retry_count", 0) > 0:
        if not improved:
            reason_for_retry = f"Confidence did not improve ({prev_conf:.1f} -> {current_conf:.1f})"
        elif result.get("confidence_level") != "HIGH":
            reason_for_retry = f"Confidence still not HIGH ({current_conf:.1f})"

    try:
        await trace_service.save_trace(
            db=db,
            trace_id=trace_id,
            original_query=body.question.strip(),
            rewritten_query=result.get("rewritten_question"),
            confidence_before_rewrite=prev_conf,
            confidence_after_rewrite=confidence_after_rewrite,
            retrieval_attempts=result.get("retry_count", 0) + 1,
            reason_for_retry=reason_for_retry,
            contradiction_detected=result.get("contradiction_detected", False),
            contradiction_reason=result.get("contradiction_reason"),
            clarification_needed=result.get("clarification_needed", False),
            clarification_question=result.get("clarification_question"),
            final_confidence=result.get("confidence_score", 0.0),
            final_confidence_level=result.get("confidence_level", "LOW"),
            execution_path=execution_path,
            graph_execution=graph_exec,
            retrieval_details=retrieval_details,
            confidence_breakdown=result.get("confidence_breakdown"),
            llm_observability=result.get("llm_observability"),
            session_timeline=session_timeline,
            answer=result.get("answer"),
            citations=[c.model_dump() for c in citations],
            latencies=result.get("latencies", {}),
        )
    except Exception as e:
        logger.error("Failed to save trace %s: %s", trace_id, e)

    return ChatResponse(
        answer=result.get("answer", "") or (
            "I don't have enough evidence to answer this question reliably."
        ),
        confidence=result.get("confidence_score", 0.0),
        confidence_level=result.get("confidence_level", "LOW"),
        reasoning_path=execution_path,
        citations=citations,
        clarification_question=result.get("clarification_question"),
        latencies=result.get("latencies"),
        trace_id=trace_id,
    )
