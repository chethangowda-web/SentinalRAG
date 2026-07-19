import logging
import time

from langgraph.types import RunnableConfig

from app.graph.state import GraphState
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)

FINAL_TOP_K = 5


async def retrieve_node(state: GraphState, config: RunnableConfig) -> dict:
    start = time.perf_counter()
    question = state.get("rewritten_question") or state["question"]
    db = config["configurable"]["db"]

    logger.info("Retrieve node: query='%s'", question[:80])
    search_response = await retrieve(question, db)

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
            "reason": "Reranked top result" if i == 0 else (f"Reranked position {i+1}" if i < FINAL_TOP_K else "Below rerank cutoff"),
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

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "retrieve",
        "execution_time_ms": elapsed,
        "input": question[:100],
        "output": f"{len(chunks)} chunks, confidence={search_response.confidence:.1f}/{search_response.confidence_level}",
        "decision": None,
        "next_node": None,
        "retry_count": state.get("retry_count", 0),
    })

    return {
        "retrieved_chunks": chunks,
        "confidence_score": search_response.confidence,
        "confidence_level": search_response.confidence_level,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
        "retrieval_details": retrieval_details,
    }
