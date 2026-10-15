from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.retrieval_service import SearchResponse


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/metrics/performance", "/api/v1/metrics/system", "/api/v1/metrics/errors", "/api/v1/metrics"])
async def test_global_metrics_require_admin(async_client, path):
    response = await async_client.get(path)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_global_metrics_allowed_for_admin(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "Test@Example.com")
    response = await async_client.get("/api/v1/metrics/errors")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_settings_update_requires_admin(async_client):
    response = await async_client.put("/api/v1/settings", json={"chunk_size": 100})
    assert response.status_code == 403

    response = await async_client.post("/api/v1/settings/reset")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_is_scoped_to_current_user(async_client):
    empty = SearchResponse(query="q", confidence=0.0, confidence_level="LOW", results=[], latencies={})
    with patch("app.services.retrieval_service.retrieve", new_callable=AsyncMock, return_value=empty) as mock_retrieve:
        response = await async_client.post("/api/v1/search", json={"query": "refund policy"})

    assert response.status_code == 200
    assert mock_retrieve.call_args.kwargs["user_id"] == "test-user-id"


@pytest.mark.asyncio
async def test_me_reports_whether_the_user_is_an_admin(async_client, monkeypatch):
    assert (await async_client.get("/api/v1/auth/me")).json()["is_admin"] is False
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "TEST@example.com")
    assert (await async_client.get("/api/v1/auth/me")).json()["is_admin"] is True
