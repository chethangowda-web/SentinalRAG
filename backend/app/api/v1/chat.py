import logging
import time
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.graph.graph_builder import build_graph
from app.graph.state import GraphState
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationItem,
    ConfidenceBreakdown,
    GraphExecutionStep,
    LLMObservability,
    RetrievalDetailItem,
)
from app.services import chat_history_service, trace_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _dict_to_graph_execution_step(d: dict) -> GraphExecutionStep:
    return GraphExecutionStep(
        node_name=d.get("node_name", "unknown"),
        execution_time_ms=d.get("execution_time_ms", 0),
        input=d.get("input"),
        output=d.get("output"),
        decision=d.get("decision"),
        next_node=d.get("next_node"),
        retry_count=d.get("retry_count", 0),
    )


def _dict_to_retrieval_detail(d: dict) -> RetrievalDetailItem:
    return RetrievalDetailItem(
        chunk_id=d.get("chunk_id", ""),
        document_id=d.get("document_id", ""),
        text=d.get("text", ""),
        vector_score=d.get("vector_score", 0),
        bm25_score=d.get("bm25_score", 0),
        fusion_score=d.get("fusion_score", 0),
        rerank_score=d.get("rerank_score", 0),
        final_rank=d.get("final_rank", 0),
        selected=d.get("selected", False),
        reason=d.get("reason", ""),
    )


def _dict_to_breakdown(d: dict | None) -> ConfidenceBreakdown | None:
    if not d:
        return None
    return ConfidenceBreakdown(
        vector_similarity=d.get("vector_similarity", 0),
        vector_contribution=d.get("vector_contribution", 0),
        coverage=d.get("coverage", 0),
        coverage_contribution=d.get("coverage_contribution", 0),
        cross_encoder_score=d.get("cross_encoder_score", 0),
        cross_encoder_contribution=d.get("cross_encoder_contribution", 0),
        citation_count=d.get("citation_count", 0),
        citation_contribution=d.get("citation_contribution", 0),
        contradiction_status=d.get("contradiction_status", "none"),
        retry_success=d.get("retry_success", False),
        raw_score=d.get("raw_score", 0),
        final_score=d.get("final_score", 0),
    )


def _dict_to_llm_obs(d: dict | None) -> LLMObservability | None:
    if not d:
        return None
    return LLMObservability(
        rewrite_prompt_tokens=d.get("rewrite_prompt_tokens", 0),
        rewrite_completion_tokens=d.get("rewrite_completion_tokens", 0),
        rewrite_total_tokens=d.get("rewrite_total_tokens", 0),
        rewrite_latency_ms=d.get("rewrite_latency_ms", 0),
        generation_prompt_tokens=d.get("generation_prompt_tokens", 0),
        generation_completion_tokens=d.get("generation_completion_tokens", 0),
        generation_total_tokens=d.get("generation_total_tokens", 0),
        generation_latency_ms=d.get("generation_latency_ms", 0),
        model_name=d.get("model_name", settings.effective_llm_model),
        temperature=d.get("temperature", settings.LLM_TEMPERATURE),
    )


def _normalize_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return round(value, 1)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    start = time.perf_counter()
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    session_id = body.session_id
    if not session_id:
        session_id = str(uuid.uuid4())

    if not body.question or not body.question.strip():
        return ChatResponse(
            answer="Please provide a valid question.",
            confidence=0.0,
            confidence_level="LOW",
            reasoning_path=["validation"],
            citations=[],
            trace_id=trace_id,
            model_used=settings.effective_llm_model or "unknown",
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
        logger.exception("Graph execution failed for trace_id=%s: %s", trace_id, e)
        return ChatResponse(
            answer="An error occurred while processing your question. Please try again.",
            confidence=0.0,
            confidence_level="LOW",
            reasoning_path=["error"],
            citations=[],
            trace_id=trace_id,
            model_used=settings.effective_llm_model or "unknown",
        )

    answer_text = result.get("answer", "")
    retrieved_chunks = result.get("retrieved_chunks", [])

    if not answer_text and not retrieved_chunks:
        answer_text = "No relevant information was found in the uploaded documents."
        logger.info("No relevant chunks found for question: '%s' trace_id=%s", body.question.strip(), trace_id)
    elif not answer_text and retrieved_chunks:
        answer_text = "No relevant information was found in the uploaded documents."

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Chat endpoint: %.1fms total, path=%s, confidence=%.1f/%s",
        elapsed, result.get("reasoning_path", []),
        result.get("confidence_score", 0), result.get("confidence_level", "LOW"),
    )

    raw_conf = result.get("confidence_score", 0.0)
    confidence = _normalize_confidence(raw_conf)
    confidence_level = result.get("confidence_level", "LOW")
    if confidence >= 80:
        confidence_level = "HIGH"
    elif confidence >= 50:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

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

    retrieval_details = result.get("retrieval_details", [])
    improved = result.get("confidence_improved", False)
    prev_conf = initial_state["confidence_score"]
    current_conf = confidence
    confidence_after_rewrite = current_conf if result.get("rewritten_question") else None

    reason_for_retry = None
    if result.get("retry_count", 0) > 0:
        if not improved:
            reason_for_retry = f"Confidence did not improve ({prev_conf:.1f} -> {current_conf:.1f})"
        elif confidence_level != "HIGH":
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
            final_confidence=confidence,
            final_confidence_level=confidence_level,
            execution_path=execution_path,
            graph_execution=graph_exec,
            retrieval_details=retrieval_details,
            confidence_breakdown=result.get("confidence_breakdown"),
            llm_observability=result.get("llm_observability"),
            session_timeline=trace_service.build_session_timeline(execution_path, graph_exec),
            answer=result.get("answer"),
            citations=[c.model_dump() for c in citations],
            latencies=result.get("latencies", {}),
        )
    except Exception as e:
        logger.error("Failed to save trace %s: %s", trace_id, e)

    response = ChatResponse(
        answer=result.get("answer", "") or (
            "I don't have enough evidence to answer this question reliably."
        ),
        confidence=confidence,
        confidence_level=confidence_level,
        reasoning_path=execution_path,
        citations=citations,
        clarification_question=result.get("clarification_question"),
        clarification_needed=result.get("clarification_needed", False),
        latencies=result.get("latencies"),
        trace_id=trace_id,
        session_id=session_id,
        graph_execution=[_dict_to_graph_execution_step(g) for g in (graph_exec or [])],
        retrieval_details=[_dict_to_retrieval_detail(r) for r in (retrieval_details or [])],
        confidence_breakdown=_dict_to_breakdown(result.get("confidence_breakdown")),
        llm_observability=_dict_to_llm_obs(result.get("llm_observability")),
        rewritten_question=result.get("rewritten_question"),
        retry_count=result.get("retry_count", 0),
        contradiction_detected=result.get("contradiction_detected", False),
        contradiction_reason=result.get("contradiction_reason"),
        model_used=settings.effective_llm_model or "unknown",
    )

    try:
        existing = await chat_history_service.get_session(db, session_id)
        if not existing:
            existing = await chat_history_service.create_session(
                db, title=body.question.strip()[:100], session_id=session_id
            )
        if existing:
            await chat_history_service.add_message(
                db, session_id, "user", body.question.strip()
            )
            resp_dict = response.model_dump()
            resp_dict.pop("session_id", None)
            await chat_history_service.add_message(
                db, session_id, "assistant",
                response.answer,
                response_json=resp_dict,
            )
    except Exception as e:
        logger.error("Failed to save chat history: %s", e)

    return response
