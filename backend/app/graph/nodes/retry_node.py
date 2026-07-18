import logging
import time

from langgraph.types import RunnableConfig

from app.graph.state import GraphState
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)


async def retry_node(state: GraphState, config: RunnableConfig) -> dict:
    start = time.perf_counter()
    rewritten = state.get("rewritten_question") or state["question"]
    db = config["configurable"]["db"]

    logger.info("Retry node: retry #%d, query='%s'", state.get("retry_count", 0), rewritten[:80])
    search_response = await retrieve(rewritten, db)

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

    prev_score = state.get("confidence_score", 0.0)
    improved = search_response.confidence > prev_score

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["retry_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append(f"retry_retrieve(#{state.get('retry_count', 0)})")

    logger.info(
        "Retry node: %d chunks, confidence %.1f -> %.1f (improved=%s) %.1fms",
        len(chunks), prev_score, search_response.confidence, improved, elapsed,
    )

    return {
        "retrieved_chunks": chunks,
        "confidence_score": search_response.confidence,
        "confidence_level": search_response.confidence_level,
        "confidence_improved": improved,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
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
