import asyncio
import logging
import time

from app.graph.state import GraphState
from app.services.clarification_service import detect_ambiguity

logger = logging.getLogger(__name__)


async def clarification_node(state: GraphState) -> dict:
    start = time.perf_counter()
    question = state.get("rewritten_question") or state["question"]
    chunks = state.get("retrieved_chunks", [])

    clarification = await asyncio.to_thread(detect_ambiguity, question, chunks)

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["clarification_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("clarification")

    needed = clarification is not None

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "clarification",
        "execution_time_ms": elapsed,
        "input": f"question={question[:80]}, {len(chunks)} chunks",
        "output": f"needed={needed}" + (f": {clarification[:80]}" if clarification else ""),
        "decision": "clarification needed -> END" if needed else "nothing to clarify -> generate_answer",
        "next_node": "END" if needed else "generate_answer",
        "retry_count": state.get("retry_count", 0),
    })

    logger.info(
        "Clarification node: needed=%s (%.1fms)",
        needed, elapsed,
    )

    return {
        "clarification_needed": needed,
        "clarification_question": clarification,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
    }


def route_after_clarification(state: GraphState) -> str:
    """Stop with a clarifying question only if there is one; otherwise still answer the question."""
    if state.get("clarification_needed"):
        logger.info("Clarification needed -> ending with a question")
        return "end"
    logger.info("Nothing to clarify -> routing to generate_answer")
    return "generate_answer"
