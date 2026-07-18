import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.graph_builder import build_graph
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


class SentinelRAG:
    def __init__(self) -> None:
        self._graph = None
        logger.info("SentinelRAG initialized")

    def _get_graph(self):
        if self._graph is None:
            self._graph = build_graph()
        return self._graph

    async def answer(
        self,
        question: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        graph = self._get_graph()

        initial_state: GraphState = {
            "question": question,
            "rewritten_question": None,
            "retrieved_chunks": [],
            "confidence_score": 0.0,
            "confidence_level": "LOW",
            "confidence_reason": None,
            "retry_count": 0,
            "max_retries": 2,
            "contradiction_detected": False,
            "contradiction_reason": None,
            "clarification_needed": False,
            "clarification_question": None,
            "answer": None,
            "citations": [],
            "reasoning_path": [],
            "latencies": {},
        }

        try:
            result = await graph.ainvoke(initial_state, {"configurable": {"db": db}})
        except Exception as e:
            logger.exception("SentinelRAG graph execution failed: %s", e)
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return {
                "question": question,
                "answer": "An error occurred while processing the question.",
                "confidence_score": 0.0,
                "confidence_level": "LOW",
                "retrieved_chunks": [],
                "citations": [],
                "latencies": {"total": elapsed, "error": str(e)},
                "reasoning_path": ["error"],
                "contradiction_detected": False,
                "contradiction_reason": None,
                "clarification_needed": False,
                "clarification_question": None,
                "retry_count": 0,
                "error": str(e),
            }

        elapsed = round((time.perf_counter() - start) * 1000, 1)
        latencies = dict(result.get("latencies", {}))
        latencies["total"] = elapsed

        return {
            "question": question,
            "answer": result.get("answer", ""),
            "confidence_score": result.get("confidence_score", 0.0),
            "confidence_level": result.get("confidence_level", "LOW"),
            "retrieved_chunks": result.get("retrieved_chunks", []),
            "citations": result.get("citations", []),
            "latencies": latencies,
            "reasoning_path": result.get("reasoning_path", []),
            "contradiction_detected": result.get("contradiction_detected", False),
            "contradiction_reason": result.get("contradiction_reason"),
            "clarification_needed": result.get("clarification_needed", False),
            "clarification_question": result.get("clarification_question"),
            "retry_count": result.get("retry_count", 0),
        }
