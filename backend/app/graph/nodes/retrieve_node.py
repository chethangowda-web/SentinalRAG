import logging
import time

from langgraph.types import RunnableConfig

from app.graph.state import GraphState
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)


async def retrieve_node(state: GraphState, config: RunnableConfig) -> dict:
    start = time.perf_counter()
    question = state.get("rewritten_question") or state["question"]
    db = config["configurable"]["db"]

    logger.info("Retrieve node: query='%s'", question[:80])
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

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Retrieve node complete: %d chunks, confidence=%.1f/%s (%.1fms)",
        len(chunks), search_response.confidence, search_response.confidence_level, elapsed,
    )

    latencies = dict(search_response.latencies or {})
    latencies["retrieve_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("retrieve")

    return {
        "retrieved_chunks": chunks,
        "confidence_score": search_response.confidence,
        "confidence_level": search_response.confidence_level,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }
