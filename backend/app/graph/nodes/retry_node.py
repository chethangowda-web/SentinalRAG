import logging
import time

from langgraph.types import RunnableConfig

from app.graph.state import GraphState
from app.services.confidence_service import calculate_confidence_with_breakdown
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)

FINAL_TOP_K = 5


async def retry_node(state: GraphState, config: RunnableConfig) -> dict:
    start = time.perf_counter()
    rewritten = state.get("rewritten_question") or state["question"]
    db = config["configurable"]["db"]

    logger.info("Retry node: retry #%d, query='%s'", state.get("retry_count", 0), rewritten[:80])
    search_response = await retrieve(rewritten, db)

    chunks = []
    retrieval_details = []
    for i, r in enumerate(search_response.results):
        chunk = {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "text": r.text,
            "page_number": r.page_number,
            "section": r.section,
            "filename": r.filename,
            "vector_score": r.vector_score,
            "bm25_score": r.bm25_score,
            "fusion_score": r.fusion_score,
            "rerank_score": r.rerank_score,
        }
        chunks.append(chunk)
        retrieval_details.append({
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "text": r.text[:200],
            "vector_score": r.vector_score,
            "bm25_score": r.bm25_score,
            "fusion_score": r.fusion_score,
            "rerank_score": r.rerank_score,
            "final_rank": i + 1,
            "selected": i < FINAL_TOP_K,
            "reason": f"Retry reranked #{i+1}",
        })

    prev_score = state.get("confidence_score", 0.0)
    improved = search_response.confidence > prev_score

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["retry_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append(f"retry_retrieve(#{state.get('retry_count', 0)})")

    vector_scores_r = [c.get("vector_score", 0) for c in chunks if c.get("vector_score")]
    rerank_scores_r = [c.get("rerank_score", 0) for c in chunks if c.get("rerank_score")]
    _, retry_breakdown = calculate_confidence_with_breakdown(
        vector_scores=vector_scores_r,
        rerank_scores=rerank_scores_r,
        total_results=len(chunks),
        citation_count=len(chunks),
        contradiction_detected=state.get("contradiction_detected", False),
        retry_success=improved,
    )

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    if not improved:
        decision = "not_improved -> contradiction_detect"
        next_node = "contradiction_detect"
    elif search_response.confidence_level == "HIGH":
        decision = "improved_to_HIGH -> generate_answer"
        next_node = "generate_answer"
    elif retry_count < max_retries:
        decision = f"improved_not_HIGH retry{retry_count}/{max_retries} -> rewrite_query"
        next_node = "rewrite_query"
    else:
        decision = "max_retries_reached -> contradiction_detect"
        next_node = "contradiction_detect"

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "retry_retrieve",
        "execution_time_ms": elapsed,
        "input": rewritten[:100],
        "output": f"{len(chunks)} chunks, confidence={search_response.confidence:.1f}/{search_response.confidence_level} (was {prev_score:.1f}, improved={improved})",
        "decision": decision,
        "next_node": next_node,
        "retry_count": retry_count,
    })

    logger.info(
        "Retry node: %d chunks, confidence %.1f -> %.1f (improved=%s) %.1fms",
        len(chunks), prev_score, search_response.confidence, improved, elapsed,
    )

    return {
        "retrieved_chunks": chunks,
        "confidence_score": search_response.confidence,
        "confidence_level": search_response.confidence_level,
        "confidence_improved": improved,
        "confidence_breakdown": retry_breakdown,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
        "retrieval_details": retrieval_details,
    }


def route_after_retry(state: GraphState) -> str:
    if not state.get("confidence_improved", False):
        logger.info("Confidence not improved -> routing to contradiction")
        return "contradiction_detect"

    if state.get("confidence_level") == "HIGH":
        logger.info("Confidence improved to HIGH -> routing to generate")
        return "generate_answer"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count < max_retries:
        logger.info("Confidence not HIGH, retry %d/%d -> rewriting again", retry_count, max_retries)
        return "rewrite_query"

    logger.info("Max retries reached (%d) -> routing to contradiction", max_retries)
    return "contradiction_detect"
