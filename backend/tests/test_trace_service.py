import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import trace_service
from app.models.trace import Trace


class TestTraceService:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_trace(self):
        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        trace_id = str(uuid.uuid4())
        trace_data = {
            "trace_id": trace_id,
            "original_query": "What is the policy?",
            "rewritten_query": None,
            "confidence_before_rewrite": 30.0,
            "confidence_after_rewrite": None,
            "retrieval_attempts": 1,
            "reason_for_retry": None,
            "contradiction_detected": False,
            "contradiction_reason": None,
            "clarification_needed": False,
            "clarification_question": None,
            "final_confidence": 95.0,
            "final_confidence_level": "HIGH",
            "execution_path": ["retrieve", "confidence_evaluate", "generate_answer"],
            "graph_execution": [],
            "retrieval_details": [],
            "confidence_breakdown": None,
            "llm_observability": None,
            "session_timeline": None,
            "answer": "The policy is 30 days.",
            "citations": [],
            "latencies": {"total": 100.0},
        }

        mock_trace = MagicMock(spec=Trace)
        mock_trace.id = trace_id
        mock_trace.timestamp = None
        mock_trace.original_query = trace_data["original_query"]
        mock_trace.rewritten_query = trace_data["rewritten_query"]
        mock_trace.confidence_before_rewrite = trace_data["confidence_before_rewrite"]
        mock_trace.confidence_after_rewrite = trace_data["confidence_after_rewrite"]
        mock_trace.retrieval_attempts = trace_data["retrieval_attempts"]
        mock_trace.reason_for_retry = trace_data["reason_for_retry"]
        mock_trace.contradiction_detected = trace_data["contradiction_detected"]
        mock_trace.contradiction_reason = trace_data["contradiction_reason"]
        mock_trace.clarification_needed = trace_data["clarification_needed"]
        mock_trace.clarification_question = trace_data["clarification_question"]
        mock_trace.final_confidence = trace_data["final_confidence"]
        mock_trace.final_confidence_level = trace_data["final_confidence_level"]
        mock_trace.execution_path = json.dumps(trace_data["execution_path"])
        mock_trace.graph_execution = None
        mock_trace.retrieval_details = None
        mock_trace.confidence_breakdown = None
        mock_trace.llm_observability = None
        mock_trace.session_timeline = None
        mock_trace.answer = trace_data["answer"]
        mock_trace.citations = json.dumps(trace_data["citations"])
        mock_trace.latencies = json.dumps(trace_data["latencies"])

        with patch("app.services.trace_service.Trace", return_value=mock_trace):
            result = await trace_service.save_trace(
                db=mock_db,
                **trace_data,
            )
            assert result.id == trace_id
            assert result.original_query == "What is the policy?"

    @pytest.mark.asyncio
    async def test_get_trace_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await trace_service.get_trace(mock_db, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_traces_empty(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        traces = await trace_service.list_traces(mock_db)
        assert traces == []

    def test_export_csv(self):
        traces_data = [
            {
                "id": "abc-123",
                "timestamp": "2026-07-19T12:00:00",
                "original_query": "test query",
                "rewritten_query": "improved query",
                "confidence_before_rewrite": 30.0,
                "confidence_after_rewrite": 85.0,
                "retrieval_attempts": 2,
                "reason_for_retry": "not high enough",
                "contradiction_detected": False,
                "clarification_needed": False,
                "final_confidence": 85.0,
                "final_confidence_level": "HIGH",
                "execution_path": ["retrieve", "confidence_evaluate", "rewrite_query", "retry_retrieve", "generate_answer"],
                "answer": "The policy is 30 days.",
            }
        ]
        csv_output = trace_service.export_traces_csv(traces_data)
        assert "Trace ID" in csv_output
        assert "abc-123" in csv_output
        assert "test query" in csv_output
        assert "HIGH" in csv_output

    def test_export_markdown(self):
        traces_data = [
            {
                "id": "abc-123",
                "timestamp": "2026-07-19T12:00:00",
                "original_query": "test query",
                "rewritten_query": None,
                "confidence_before_rewrite": 0.0,
                "confidence_after_rewrite": None,
                "retrieval_attempts": 1,
                "reason_for_retry": None,
                "contradiction_detected": False,
                "contradiction_reason": None,
                "clarification_needed": False,
                "clarification_question": None,
                "final_confidence": 0.0,
                "final_confidence_level": "LOW",
                "execution_path": ["retrieve", "fallback"],
                "answer": "I don't know.",
                "graph_execution": [],
                "retrieval_details": [],
                "confidence_breakdown": None,
            }
        ]
        md = trace_service.export_traces_markdown(traces_data)
        assert "Decision Trace Report" in md
        assert "abc-123" in md
        assert "test query" in md

    def test_build_session_timeline(self):
        path = ["retrieve", "confidence_evaluate", "generate_answer"]
        graph_exec = [
            {"node_name": "retrieve", "execution_time_ms": 50.0},
            {"node_name": "confidence_evaluate", "execution_time_ms": 5.0},
            {"node_name": "generate_answer", "execution_time_ms": 2000.0},
        ]
        timeline = trace_service.build_session_timeline(path, graph_exec)
        assert "Vector Search" in timeline
        assert "Confidence" in timeline
        assert "Answer" in timeline
        assert "2000" in timeline

    def test_trace_to_dict(self):
        trace = MagicMock(spec=Trace)
        trace.id = "abc"
        trace.timestamp = None
        trace.original_query = "q"
        trace.rewritten_query = None
        trace.confidence_before_rewrite = 0.0
        trace.confidence_after_rewrite = None
        trace.retrieval_attempts = 1
        trace.reason_for_retry = None
        trace.contradiction_detected = False
        trace.contradiction_reason = None
        trace.clarification_needed = False
        trace.clarification_question = None
        trace.final_confidence = 0.0
        trace.final_confidence_level = "LOW"
        trace.execution_path = json.dumps(["retrieve"])
        trace.graph_execution = None
        trace.retrieval_details = None
        trace.confidence_breakdown = None
        trace.llm_observability = None
        trace.session_timeline = None
        trace.answer = None
        trace.citations = None
        trace.latencies = None

        d = trace_service.trace_to_dict(trace)
        assert d["id"] == "abc"
        assert d["original_query"] == "q"
        assert d["execution_path"] == ["retrieve"]
        assert d["latencies"] == {}
