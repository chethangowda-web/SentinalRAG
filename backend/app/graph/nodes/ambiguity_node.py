import asyncio
import logging
import time

from app.graph.state import GraphState
from app.services.clarification_service import detect_ambiguity

logger = logging.getLogger(__name__)

# Vague questions ("Tell me about the network", "How long does it take?") are short. Longer
# questions are assumed specific and skip the check, so they cost no extra LLM call.
MAX_WORDS_TO_CHECK = 6


async def ambiguity_node(state: GraphState) -> dict:
    start = time.perf_counter()
    question = state["question"]
    words = len(question.split())

    clarification = None
    if words <= MAX_WORDS_TO_CHECK:
        # Judge the question alone. Showing the retrieved passages made the model ask "which plan?"
        # about specific questions simply because several plans appear in the documents.
        clarification = await asyncio.to_thread(detect_ambiguity, question, [], False)

    needed = clarification is not None
    elapsed = round((time.perf_counter() - start) * 1000, 1)

    latencies = dict(state.get("latencies", {}))
    latencies["ambiguity_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("ambiguity_check")

    if words > MAX_WORDS_TO_CHECK:
        output, decision, next_node = f"skipped ({words} words, specific enough)", "specific -> confidence_evaluate", "confidence_evaluate"
    elif needed:
        output, decision, next_node = f"needed: {clarification[:80]}", "ambiguous -> END", "END"
    else:
        output, decision, next_node = "clear", "clear -> confidence_evaluate", "confidence_evaluate"

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "ambiguity_check",
        "execution_time_ms": elapsed,
        "input": f"question={question[:80]}",
        "output": output,
        "decision": decision,
        "next_node": next_node,
        "retry_count": state.get("retry_count", 0),
    })

    logger.info("Ambiguity node: words=%d needed=%s (%.1fms)", words, needed, elapsed)

    update = {
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
    }
    if needed:
        update["clarification_needed"] = True
        update["clarification_question"] = clarification
    return update


def route_after_ambiguity(state: GraphState) -> str:
    if state.get("clarification_needed"):
        logger.info("Question is ambiguous -> ending with a clarifying question")
        return "end"
    return "confidence_evaluate"
