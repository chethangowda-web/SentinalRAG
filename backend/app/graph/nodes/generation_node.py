import logging
import time

from app.graph.state import GraphState
from app.services.answer_generator import generate_answer, get_usage_tokens
from app.services.confidence_service import calculate_confidence_with_breakdown
from app.core.config import settings

logger = logging.getLogger(__name__)


async def generation_node(state: GraphState) -> dict:
    start = time.perf_counter()
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])

    answer = generate_answer(question, chunks)

    citations = []
    for c in chunks:
        citations.append({
            "document_id": c.get("document_id", ""),
            "chunk_id": c.get("chunk_id", ""),
            "page": c.get("page_number"),
            "text": c.get("text", "")[:200],
        })

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["generation_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("generate_answer")

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "generate_answer",
        "execution_time_ms": elapsed,
        "input": f"question={question[:80]}, {len(chunks)} chunks",
        "output": f"answer_len={len(answer)}, {len(citations)} citations",
        "decision": "complete -> END",
        "next_node": "END",
        "retry_count": state.get("retry_count", 0),
    })

    final_vector_scores = [c.get("vector_score", 0) for c in chunks if c.get("vector_score")]
    final_rerank_scores = [c.get("rerank_score", 0) for c in chunks if c.get("rerank_score")]
    contradiction_detected_final = state.get("contradiction_detected", False)
    retry_success_final = state.get("retry_count", 0) > 0 and state.get("confidence_improved", False)
    _, final_breakdown = calculate_confidence_with_breakdown(
        vector_scores=final_vector_scores,
        rerank_scores=final_rerank_scores,
        total_results=len(chunks),
        citation_count=len(citations),
        contradiction_detected=contradiction_detected_final,
        retry_success=retry_success_final,
    )

    llm_obs = dict(state.get("llm_observability", {}) or {})
    usage = get_usage_tokens(question, chunks, answer)
    llm_obs["generation_prompt_tokens"] = llm_obs.get("generation_prompt_tokens", 0) + usage["prompt_tokens"]
    llm_obs["generation_completion_tokens"] = llm_obs.get("generation_completion_tokens", 0) + usage["completion_tokens"]
    llm_obs["generation_total_tokens"] = llm_obs.get("generation_total_tokens", 0) + usage["total_tokens"]
    llm_obs["generation_latency_ms"] = llm_obs.get("generation_latency_ms", 0) + elapsed
    llm_obs["model_name"] = settings.effective_llm_model
    llm_obs["temperature"] = settings.LLM_TEMPERATURE

    logger.info(
        "Generation node: answer_len=%d, %d citations (%.1fms)",
        len(answer), len(citations), elapsed,
    )

    return {
        "answer": answer,
        "citations": citations,
        "confidence_breakdown": final_breakdown,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
        "llm_observability": llm_obs,
    }
