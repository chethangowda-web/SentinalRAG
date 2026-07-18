import logging
import time

from app.graph.state import GraphState
from app.services.query_rewriter import rewrite_query

logger = logging.getLogger(__name__)


async def rewrite_node(state: GraphState) -> dict:
    start = time.perf_counter()
    question = state["question"]

    rewritten = rewrite_query(question)

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["rewrite_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("rewrite_query")

    logger.info(
        "Rewrite node: '%.60s' -> '%.80s' (%.1fms)",
        question, rewritten, elapsed,
    )

    return {
        "rewritten_question": rewritten,
        "retry_count": state.get("retry_count", 0) + 1,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }
