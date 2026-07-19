import logging
import time

from app.graph.state import GraphState
from app.services.query_rewriter import rewrite_query, get_rewrite_usage_tokens

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

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "rewrite_query",
        "execution_time_ms": elapsed,
        "input": question[:100],
        "output": rewritten[:120],
        "decision": "rewrite_complete -> retry_retrieve",
        "next_node": "retry_retrieve",
        "retry_count": state.get("retry_count", 0) + 1,
    })

    llm_obs = dict(state.get("llm_observability", {}) or {})
    rewrite_usage = get_rewrite_usage_tokens(question, rewritten)
    llm_obs["rewrite_prompt_tokens"] = llm_obs.get("rewrite_prompt_tokens", 0) + rewrite_usage["rewrite_prompt_tokens"]
    llm_obs["rewrite_completion_tokens"] = llm_obs.get("rewrite_completion_tokens", 0) + rewrite_usage["rewrite_completion_tokens"]
    llm_obs["rewrite_total_tokens"] = llm_obs.get("rewrite_total_tokens", 0) + rewrite_usage["rewrite_total_tokens"]
    llm_obs["rewrite_latency_ms"] = llm_obs.get("rewrite_latency_ms", 0) + elapsed

    logger.info(
        "Rewrite node: '%.60s' -> '%.80s' (%.1fms)",
        question, rewritten, elapsed,
    )

    return {
        "rewritten_question": rewritten,
        "retry_count": state.get("retry_count", 0) + 1,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
        "llm_observability": llm_obs,
    }
