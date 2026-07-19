import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.graph.state import GraphState
from app.graph.nodes.confidence_node import confidence_node, route_after_confidence
from app.graph.nodes.contradiction_node import contradiction_node, route_after_contradiction
from app.graph.nodes.fallback_node import fallback_node
from app.graph.nodes.retry_node import retry_node, route_after_retry
from app.services.contradiction_service import detect_contradictions
from app.services.clarification_service import detect_ambiguity
from app.services.query_rewriter import rewrite_query


class TestGraphState:
    def test_state_defaults(self):
        state: GraphState = {
            "question": "What is the refund policy?",
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
        assert state["question"] == "What is the refund policy?"
        assert state["max_retries"] == 2
        assert state["retry_count"] == 0


class TestConfidenceNode:
    def test_confidence_node_high(self):
        state: GraphState = _make_state(
            chunks=[{"vector_score": 0.95, "rerank_score": 0.92}] * 5,
        )
        result = confidence_node(state)
        assert result["confidence_score"] >= 80
        assert result["confidence_level"] == "HIGH"

    def test_confidence_node_low(self):
        state: GraphState = _make_state(chunks=[])
        result = confidence_node(state)
        assert result["confidence_score"] == 0.0
        assert result["confidence_level"] == "LOW"

    def test_route_high_to_generate(self):
        state: GraphState = _make_state(level="HIGH")
        assert route_after_confidence(state) == "generate_answer"

    def test_route_low_to_rewrite(self):
        state: GraphState = _make_state(level="LOW")
        assert route_after_confidence(state) == "rewrite_query"

    def test_route_medium_to_rewrite(self):
        state: GraphState = _make_state(level="MEDIUM")
        assert route_after_confidence(state) == "rewrite_query"


class TestContradictionNode:
    def test_no_contradiction_single_chunk(self):
        state: GraphState = _make_state(chunks=[{"text": "The refund policy is 30 days."}])
        result = contradiction_node(state)
        assert result["contradiction_detected"] is False

    def test_no_contradiction_consistent(self):
        state: GraphState = _make_state(chunks=[
            {"text": "The refund policy allows returns within 30 days."},
            {"text": "All customers are eligible for the warranty program."},
        ])
        result = contradiction_node(state)
        assert result["contradiction_detected"] is False

    def test_detects_number_conflict(self):
        state: GraphState = _make_state(chunks=[
            {"text": "The refund period is 30 days from purchase."},
            {"text": "The refund period is 90 days from purchase."},
        ])
        result = contradiction_node(state)
        assert result["contradiction_detected"] is True
        assert result["contradiction_reason"] is not None

    def test_detects_same_number_different_context(self):
        state: GraphState = _make_state(chunks=[
            {"text": "The maximum refund period is 30 days per our policy."},
            {"text": "Refunds are processed within 30 business days per company rules."},
        ])
        result = contradiction_node(state)
        assert result["contradiction_detected"] is True

    def test_route_contradiction_to_clarification(self):
        state: GraphState = _make_state()
        state["contradiction_detected"] = True
        assert route_after_contradiction(state) == "clarification"

    def test_route_no_contradiction_to_generate(self):
        state: GraphState = _make_state()
        state["contradiction_detected"] = False
        assert route_after_contradiction(state) == "generate_answer"


class TestRetryNode:
    @pytest.mark.asyncio
    async def test_retry_returns_chunks(self):
        mock_config = {"configurable": {"db": MagicMock()}}
        state: GraphState = _make_state(
            question="test query",
            rewritten_question="improved query",
        )
        with patch("app.graph.nodes.retry_node.retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_response = MagicMock()
            mock_response.confidence = 85.0
            mock_response.confidence_level = "HIGH"
            mock_response.results = []
            mock_response.latencies = {}
            mock_retrieve.return_value = mock_response

            result = await retry_node(state, mock_config)
            assert result["confidence_score"] == 85.0

    def test_route_improved_to_generate(self):
        state: GraphState = _make_state(level="HIGH", score=80.0)
        state["confidence_score"] = 0.5
        state["confidence_improved"] = True
        assert route_after_retry(state) == "generate_answer"

    def test_route_not_improved_to_contradiction(self):
        state: GraphState = _make_state(level="LOW", score=0.0)
        assert route_after_retry(state) == "contradiction_detect"

    def test_route_retry_below_max(self):
        state: GraphState = _make_state(level="MEDIUM", score=50.0)
        state["retry_count"] = 1
        state["max_retries"] = 2
        state["confidence_score"] = 50.0
        state["confidence_improved"] = True
        assert route_after_retry(state) == "rewrite_query"


class TestFallbackNode:
    def test_fallback_returns_low_confidence(self):
        state: GraphState = _make_state()
        result = fallback_node(state)
        assert "don't have enough evidence" in result["answer"]
        assert result["citations"] == []


class TestContradictionService:
    def test_detect_number_conflicts_across_chunks(self):
        chunks = [
            {"text": "The fee is 30 dollars per month."},
            {"text": "The fee is 30 dollars annually."},
        ]
        detected, reason = detect_contradictions(chunks)
        assert detected is True
        assert "30" in reason

    def test_no_contradiction_same_numbers(self):
        chunks = [
            {"text": "There are 31 days in December."},
            {"text": "The company policy requires 90 days notice."},
        ]
        detected, reason = detect_contradictions(chunks)
        assert detected is False

    def test_single_chunk_no_contradiction(self):
        detected, reason = detect_contradictions([{"text": "Some text."}])
        assert detected is False

    def test_empty_chunks(self):
        detected, reason = detect_contradictions([])
        assert detected is False

    def test_policy_conflict_detection(self):
        chunks = [
            {"text": "Refunds are allowed within 30 days."},
            {"text": "No refunds are permitted under any circumstances."},
        ]
        detected, reason = detect_contradictions(chunks)
        assert detected is True


class TestClarificationService:
    def test_vague_question_detected(self):
        chunks = [{"section": "Refund Policy", "text": "text here"}]
        result = detect_ambiguity("What about it?", chunks)
        assert result is not None
        assert "specific" in result.lower()

    def test_vague_question_no_chunks(self):
        result = detect_ambiguity("Tell me about something", [])
        assert result is not None

    def test_specific_question_no_llm(self):
        with patch("app.services.clarification_service.settings.DEEPSEEK_API_KEY", ""):
            result = detect_ambiguity("What is the refund period in days?", [])
            assert result is None


class TestQueryRewriter:
    def test_no_llm_returns_original(self):
        with patch("app.services.query_rewriter.settings.DEEPSEEK_API_KEY", ""):
            result = rewrite_query("What about refunds?")
            assert result == "What about refunds?"


class TestGraphExecution:
    @pytest.mark.asyncio
    async def test_high_confidence_path(self, db_session):
        from app.graph.graph_builder import build_graph

        graph = build_graph()
        mock_results = [
            MagicMock(
                chunk_id=f"c{i}", document_id=f"d{i}",
                text=f"Refund policy chunk {i}.",
                page_number=i, section=f"Section {i}", filename=f"doc{i}.pdf",
                vector_score=0.95, bm25_score=0.9, rerank_score=0.94,
            )
            for i in range(4)
        ]
        mock_response = MagicMock()
        mock_response.confidence = 92.0
        mock_response.confidence_level = "HIGH"
        mock_response.results = mock_results
        mock_response.latencies = {"total": 100.0}

        patcher_retrieve = patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock)
        patcher_retry = patch("app.graph.nodes.retry_node.retrieve", new_callable=AsyncMock)
        patcher_gen = patch("app.graph.nodes.generation_node.generate_answer")

        with patcher_retrieve as mock_retrieve:
            mock_retrieve.return_value = mock_response
            with patcher_retry as mock_retry:
                mock_retry.return_value = mock_response
                with patcher_gen as mock_gen:
                    mock_gen.return_value = "The refund policy is 30 days."

                    result = await graph.ainvoke(
                        {
                            "question": "What is the refund policy?",
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
                            "trace_id": "test-trace-id",
                            "graph_execution": [],
                            "retrieval_details": [],
                            "confidence_breakdown": None,
                            "llm_observability": None,
                        },
                        {"configurable": {"db": db_session}},
                    )
                    assert result["confidence_level"] == "HIGH"
                    assert len(result["reasoning_path"]) >= 2

    @pytest.mark.asyncio
    async def test_low_confidence_fallback_path(self, db_session):
        from app.graph.graph_builder import build_graph

        graph = build_graph()

        with patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_response = MagicMock()
            mock_response.confidence = 20.0
            mock_response.confidence_level = "LOW"
            mock_response.results = []
            mock_response.latencies = {"total": 50.0}
            mock_retrieve.return_value = mock_response

            with patch("app.graph.nodes.retry_node.retrieve", new_callable=AsyncMock) as mock_retry:
                mock_retry.return_value = mock_response
                with patch("app.graph.nodes.rewrite_node.rewrite_query") as mock_rewrite:
                    mock_rewrite.return_value = "improved query"
                    with patch("app.graph.nodes.generation_node.generate_answer") as mock_gen:
                        mock_gen.return_value = "I don't have enough evidence to answer this question reliably."

                        result = await graph.ainvoke(
                            {
                                "question": "obscure question",
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
                                "trace_id": "test-trace-id",
                                "graph_execution": [],
                                "retrieval_details": [],
                                "confidence_breakdown": None,
                                "llm_observability": None,
                            },
                            {"configurable": {"db": db_session}},
                        )
                        assert "don't have enough evidence" in result["answer"]
                        assert any("generate_answer" in s for s in result["reasoning_path"])


def _make_high_conf_response():
    mock_response = MagicMock()
    mock_response.confidence = 95.0
    mock_response.confidence_level = "HIGH"
    mock_response.results = [
        MagicMock(
            chunk_id=f"c{i}", document_id=f"d{i}", text=f"chunk text {i}",
            page_number=i, section=f"Section {i}", filename=f"doc{i}.pdf",
            vector_score=0.95, bm25_score=0.9, rerank_score=0.93,
        )
        for i in range(1, 5)
    ]
    mock_response.latencies = {"total": 60.0}
    return mock_response


class TestChatAPI:
    @pytest.mark.asyncio
    async def test_chat_endpoint_empty_question(self, async_client, db_session):
        response = await async_client.post(
            "/api/v1/chat",
            json={"question": ""},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["confidence_level"] == "LOW"

    @pytest.mark.asyncio
    async def test_chat_endpoint_returns_response(self, async_client, db_session):
        mock_resp = _make_high_conf_response()
        patcher_retrieve = patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock)
        patcher_gen = patch("app.graph.nodes.generation_node.generate_answer")

        with patcher_retrieve as mock_retrieve:
            mock_retrieve.return_value = mock_resp
            with patcher_gen as mock_gen:
                mock_gen.return_value = "The policy is 30 days."

                response = await async_client.post(
                    "/api/v1/chat",
                    json={"question": "What is the policy?"},
                )
                assert response.status_code == 200
                data = response.json()
                assert "answer" in data
                assert data["confidence"] > 0

    @pytest.mark.asyncio
    async def test_chat_endpoint_returns_citations(self, async_client, db_session):
        mock_resp = _make_high_conf_response()
        patcher_retrieve = patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock)
        patcher_gen = patch("app.graph.nodes.generation_node.generate_answer")

        with patcher_retrieve as mock_retrieve:
            mock_retrieve.return_value = mock_resp
            with patcher_gen as mock_gen:
                mock_gen.return_value = "Answer with citation."

                response = await async_client.post(
                    "/api/v1/chat",
                    json={"question": "test"},
                )
                data = response.json()
                assert "citations" in data
                assert len(data["citations"]) > 0

    @pytest.mark.asyncio
    async def test_chat_endpoint_reasoning_path(self, async_client, db_session):
        mock_resp = _make_high_conf_response()
        patcher_retrieve = patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock)
        patcher_gen = patch("app.graph.nodes.generation_node.generate_answer")

        with patcher_retrieve as mock_retrieve:
            mock_retrieve.return_value = mock_resp
            with patcher_gen as mock_gen:
                mock_gen.return_value = "Answer."

                response = await async_client.post(
                    "/api/v1/chat",
                    json={"question": "test"},
                )
                data = response.json()
                assert "reasoning_path" in data
                assert len(data["reasoning_path"]) > 0

    @pytest.mark.asyncio
    async def test_chat_endpoint_latencies(self, async_client, db_session):
        mock_resp = _make_high_conf_response()
        patcher_retrieve = patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock)
        patcher_gen = patch("app.graph.nodes.generation_node.generate_answer")

        with patcher_retrieve as mock_retrieve:
            mock_retrieve.return_value = mock_resp
            with patcher_gen as mock_gen:
                mock_gen.return_value = "Answer."

                response = await async_client.post(
                    "/api/v1/chat",
                    json={"question": "test"},
                )
                data = response.json()
                assert data["latencies"] is not None


def _make_state(
    question: str = "test question",
    chunks: list | None = None,
    level: str = "LOW",
    score: float = 0.0,
    rewritten_question: str | None = None,
) -> GraphState:
    return {
        "question": question,
        "rewritten_question": rewritten_question,
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
