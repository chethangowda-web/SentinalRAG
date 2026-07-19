import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.graph.state import GraphState
from app.graph.nodes.retrieve_node import retrieve_node
from app.graph.nodes.retry_node import retry_node
from app.graph.nodes.confidence_node import confidence_node
from app.graph.nodes.contradiction_node import contradiction_node
from app.graph.nodes.generation_node import generation_node


class TestGraphTraceIntegration:
    @pytest.mark.asyncio
    async def test_retrieve_node_records_graph_execution(self):
        mock_config = {"configurable": {"db": MagicMock()}}
        mock_response = MagicMock()
        mock_response.confidence = 92.0
        mock_response.confidence_level = "HIGH"
        mock_response.results = [
            MagicMock(
                chunk_id="c1", document_id="d1", text="chunk1",
                page_number=1, section="S1", filename="d1.pdf",
                vector_score=0.95, bm25_score=0.90, fusion_score=0.85, rerank_score=0.94,
            )
        ]
        mock_response.latencies = {"retrieve_node": 100.0}

        state: GraphState = _make_trace_state()

        with patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock) as m:
            m.return_value = mock_response
            result = await retrieve_node(state, mock_config)

            assert "graph_execution" in result
            assert len(result["graph_execution"]) == 1
            assert result["graph_execution"][0]["node_name"] == "retrieve"
            assert result["graph_execution"][0]["execution_time_ms"] > 0

            assert "retrieval_details" in result
            assert len(result["retrieval_details"]) == 1
            assert result["retrieval_details"][0]["chunk_id"] == "c1"

    def test_confidence_node_records_breakdown(self):
        state: GraphState = _make_trace_state()
        state["retrieved_chunks"] = [
            {"chunk_id": "c1", "vector_score": 0.95, "rerank_score": 0.92},
            {"chunk_id": "c2", "vector_score": 0.90, "rerank_score": 0.88},
        ]

        result = confidence_node(state)

        assert "confidence_breakdown" in result
        assert result["confidence_breakdown"] is not None
        assert result["confidence_breakdown"]["vector_similarity"] > 0
        assert "contradiction_status" in result["confidence_breakdown"]
        assert "retry_success" in result["confidence_breakdown"]

        assert "graph_execution" in result
        assert result["graph_execution"][0]["node_name"] == "confidence_evaluate"

    @pytest.mark.asyncio
    async def test_retry_node_records_breakdown_with_retry_status(self):
        mock_config = {"configurable": {"db": MagicMock()}}
        mock_response = MagicMock()
        mock_response.confidence = 92.0
        mock_response.confidence_level = "HIGH"
        mock_response.results = [
            MagicMock(
                chunk_id="c1", document_id="d1", text="chunk1",
                page_number=1, section="S1", filename="d1.pdf",
                vector_score=0.95, bm25_score=0.90, fusion_score=0.85, rerank_score=0.94,
            )
        ]
        mock_response.latencies = {}

        state: GraphState = _make_trace_state(score=30.0, level="LOW")
        state["retry_count"] = 1

        with patch("app.graph.nodes.retry_node.retrieve", new_callable=AsyncMock) as m:
            m.return_value = mock_response
            result = await retry_node(state, mock_config)

            assert "confidence_breakdown" in result
            assert result["confidence_breakdown"]["retry_success"] is True

            assert "graph_execution" in result
            assert result["graph_execution"][0]["node_name"] == "retry_retrieve"

    def test_contradiction_node_records_breakdown(self):
        state: GraphState = _make_trace_state()
        state["retrieved_chunks"] = [
            {"text": "Refund period is 30 days.", "vector_score": 0.95, "rerank_score": 0.92},
            {"text": "Refund period is 90 days.", "vector_score": 0.90, "rerank_score": 0.88},
        ]

        result = contradiction_node(state)

        assert "confidence_breakdown" in result
        assert result["confidence_breakdown"]["contradiction_status"] == "detected"

        assert "graph_execution" in result
        assert result["graph_execution"][0]["node_name"] == "contradiction_detect"

    @pytest.mark.asyncio
    async def test_generation_node_computes_definitive_breakdown(self):
        state: GraphState = _make_trace_state(level="HIGH", score=90.0)
        state["retrieved_chunks"] = [
            {"chunk_id": "c1", "document_id": "d1", "text": "chunk text", "page_number": 1,
             "vector_score": 0.95, "bm25_score": 0.90, "fusion_score": 0.85, "rerank_score": 0.94},
        ]
        state["contradiction_detected"] = True
        state["retry_count"] = 1
        state["confidence_improved"] = True

        with patch("app.graph.nodes.generation_node.generate_answer") as m:
            m.return_value = "The policy is 30 days."
            result = await generation_node(state)

            assert "confidence_breakdown" in result
            assert result["confidence_breakdown"] is not None
            assert result["confidence_breakdown"]["contradiction_status"] == "detected"
            assert result["confidence_breakdown"]["retry_success"] is True
            assert result["confidence_breakdown"]["vector_similarity"] > 0

    def test_graph_execution_list_accumulates(self):
        state: GraphState = _make_trace_state(level="HIGH", score=95.0)
        state["retrieved_chunks"] = [
            {"chunk_id": "c1", "vector_score": 0.95, "rerank_score": 0.94},
        ]
        state["graph_execution"] = [
            {"node_name": "retrieve", "execution_time_ms": 50.0},
        ]

        result = confidence_node(state)
        assert len(result["graph_execution"]) == 2
        assert result["graph_execution"][0]["node_name"] == "retrieve"
        assert result["graph_execution"][1]["node_name"] == "confidence_evaluate"


def _make_trace_state(
    question: str = "test question",
    chunks: list | None = None,
    level: str = "LOW",
    score: float = 0.0,
    rewritten: str | None = None,
) -> GraphState:
    return {
        "question": question,
        "rewritten_question": rewritten,
        "retrieved_chunks": chunks or [],
        "confidence_score": score,
        "confidence_level": level,
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
        "trace_id": "test-trace-id",
        "graph_execution": [],
        "retrieval_details": [],
        "confidence_breakdown": None,
        "llm_observability": None,
    }
