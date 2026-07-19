import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import trace_service


class TestTraceAPI:
    @pytest.mark.asyncio
    async def test_list_traces_empty(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.list_traces", new_callable=AsyncMock)
        patcher_count = patch("app.api.v1.traces.trace_service.count_traces", new_callable=AsyncMock)

        with patcher as mock_list:
            mock_list.return_value = []
            with patcher_count as mock_count:
                mock_count.return_value = 0

                response = await async_client.get("/api/v1/traces")
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 0
                assert data["traces"] == []

    @pytest.mark.asyncio
    async def test_list_traces_with_data(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.list_traces", new_callable=AsyncMock)
        patcher_count = patch("app.api.v1.traces.trace_service.count_traces", new_callable=AsyncMock)

        mock_trace = MagicMock()
        mock_trace.id = "trace-1"
        mock_trace.timestamp = None
        mock_trace.original_query = "test query"
        mock_trace.rewritten_query = None
        mock_trace.confidence_before_rewrite = 0.0
        mock_trace.confidence_after_rewrite = None
        mock_trace.retrieval_attempts = 1
        mock_trace.reason_for_retry = None
        mock_trace.contradiction_detected = False
        mock_trace.contradiction_reason = None
        mock_trace.clarification_needed = False
        mock_trace.clarification_question = None
        mock_trace.final_confidence = 95.0
        mock_trace.final_confidence_level = "HIGH"
        mock_trace.execution_path = json.dumps(["retrieve", "generate_answer"])
        mock_trace.graph_execution = json.dumps([])
        mock_trace.retrieval_details = json.dumps([])
        mock_trace.confidence_breakdown = None
        mock_trace.llm_observability = None
        mock_trace.session_timeline = None
        mock_trace.answer = "answer"
        mock_trace.citations = json.dumps([])
        mock_trace.latencies = json.dumps({})

        with patcher as mock_list:
            mock_list.return_value = [mock_trace]
            with patcher_count as mock_count:
                mock_count.return_value = 1

                response = await async_client.get("/api/v1/traces")
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 1
                assert len(data["traces"]) == 1
                assert data["traces"][0]["id"] == "trace-1"

    @pytest.mark.asyncio
    async def test_get_trace_found(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.get_trace", new_callable=AsyncMock)

        mock_trace = MagicMock()
        mock_trace.id = "trace-1"
        mock_trace.timestamp = None
        mock_trace.original_query = "test"
        mock_trace.rewritten_query = None
        mock_trace.confidence_before_rewrite = 0.0
        mock_trace.confidence_after_rewrite = None
        mock_trace.retrieval_attempts = 1
        mock_trace.reason_for_retry = None
        mock_trace.contradiction_detected = False
        mock_trace.contradiction_reason = None
        mock_trace.clarification_needed = False
        mock_trace.clarification_question = None
        mock_trace.final_confidence = 95.0
        mock_trace.final_confidence_level = "HIGH"
        mock_trace.execution_path = json.dumps(["retrieve"])
        mock_trace.graph_execution = json.dumps([])
        mock_trace.retrieval_details = json.dumps([])
        mock_trace.confidence_breakdown = None
        mock_trace.llm_observability = None
        mock_trace.session_timeline = None
        mock_trace.answer = "answer"
        mock_trace.citations = json.dumps([])
        mock_trace.latencies = json.dumps({})

        with patcher as mock_get:
            mock_get.return_value = mock_trace

            response = await async_client.get("/api/v1/traces/trace-1")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "trace-1"
            assert data["final_confidence"] == 95.0

    @pytest.mark.asyncio
    async def test_get_trace_not_found(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.get_trace", new_callable=AsyncMock)

        with patcher as mock_get:
            mock_get.return_value = None

            response = await async_client.get("/api/v1/traces/nonexistent")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_json(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.list_traces", new_callable=AsyncMock)

        with patcher as mock_list:
            mock_list.return_value = []

            response = await async_client.get("/api/v1/traces/export/json")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            assert "sentinelrag_traces.json" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_export_csv(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.list_traces", new_callable=AsyncMock)

        with patcher as mock_list:
            mock_list.return_value = []

            response = await async_client.get("/api/v1/traces/export/csv")
            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]
            assert "sentinelrag_traces.csv" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_export_markdown(self, async_client):
        patcher = patch("app.api.v1.traces.trace_service.list_traces", new_callable=AsyncMock)

        with patcher as mock_list:
            mock_list.return_value = []

            response = await async_client.get("/api/v1/traces/export/markdown")
            assert response.status_code == 200
            assert "text/markdown" in response.headers["content-type"]
            assert "sentinelrag_decision_report.md" in response.headers.get("content-disposition", "")
