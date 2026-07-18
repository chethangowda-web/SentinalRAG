import logging

from langgraph.graph import END, StateGraph

from app.graph.nodes.clarification_node import clarification_node
from app.graph.nodes.confidence_node import (
    confidence_node,
    route_after_confidence,
)
from app.graph.nodes.contradiction_node import (
    contradiction_node,
    route_after_contradiction,
)
from app.graph.nodes.fallback_node import fallback_node
from app.graph.nodes.generation_node import generation_node
from app.graph.nodes.retrieve_node import retrieve_node
from app.graph.nodes.retry_node import retry_node, route_after_retry
from app.graph.nodes.rewrite_node import rewrite_node
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    workflow = StateGraph(GraphState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("confidence_evaluate", confidence_node)
    workflow.add_node("rewrite_query", rewrite_node)
    workflow.add_node("retry_retrieve", retry_node)
    workflow.add_node("contradiction_detect", contradiction_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("generate_answer", generation_node)
    workflow.add_node("fallback", fallback_node)

    workflow.set_entry_point("retrieve")

    workflow.add_edge("retrieve", "confidence_evaluate")

    workflow.add_conditional_edges(
        "confidence_evaluate",
        route_after_confidence,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
        },
    )

    workflow.add_edge("rewrite_query", "retry_retrieve")

    workflow.add_conditional_edges(
        "retry_retrieve",
        route_after_retry,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "contradiction_detect": "contradiction_detect",
        },
    )

    workflow.add_conditional_edges(
        "contradiction_detect",
        route_after_contradiction,
        {
            "clarification": "clarification",
            "generate_answer": "generate_answer",
        },
    )

    workflow.add_edge("clarification", END)
    workflow.add_edge("generate_answer", END)
    workflow.add_edge("fallback", END)

    compiled = workflow.compile()
    logger.info("LangGraph compiled with 8 nodes")
    return compiled
