import logging
import time

from app.graph.state import GraphState
from app.services.answer_generator import generate_answer

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

    logger.info(
        "Generation node: answer_len=%d, %d citations (%.1fms)",
        len(answer), len(citations), elapsed,
    )

    return {
        "answer": answer,
        "citations": citations,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }
