import asyncio
import gzip
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, StreamingResponse
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.frontend import mount_frontend
from app.core.middleware import RateLimitMiddleware, UIGZipMiddleware
from app.services import embedding_service, retrieval_service, vector_search_service


# ---- retrieval admission and non-blocking rerank ---------------------------------------------

@pytest.fixture(autouse=True)
def fresh_gate(monkeypatch):
    monkeypatch.setattr(retrieval_service, "_gate", None)
    monkeypatch.setattr(settings, "RETRIEVAL_CONCURRENCY", 2)
    monkeypatch.setattr(settings, "RETRIEVAL_QUEUE_TIMEOUT_SECONDS", 0.3)


def _hit():
    hit = MagicMock(chunk_id="c1", document_id="d1", text="Refunds within 30 days.", page_number=1, section=None,
                    filename="p.pdf", vector_score=0.8, bm25_score=1.0, rrf_score=0.5)
    return hit


async def _fake_searches(monkeypatch, work_seconds=0.15):
    running = {"now": 0, "peak": 0}

    async def slow_vector(*args, **kwargs):
        running["now"] += 1
        running["peak"] = max(running["peak"], running["now"])
        await asyncio.sleep(work_seconds)
        running["now"] -= 1
        return [MagicMock()]

    monkeypatch.setattr(vector_search_service, "search_vector_async", slow_vector)
    monkeypatch.setattr(retrieval_service.bm25_service, "search_bm25", AsyncMock(return_value=[]))
    monkeypatch.setattr(retrieval_service.hybrid_search_service, "fuse_results", lambda *a, **k: [_hit()])
    monkeypatch.setattr(retrieval_service.reranker_service, "rerank", lambda q, t, k: [(0, 2.0)])
    return running


@pytest.mark.asyncio
async def test_no_more_searches_run_at_once_than_the_server_can_handle(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_QUEUE_TIMEOUT_SECONDS", 5.0)
    running = await _fake_searches(monkeypatch)
    await asyncio.gather(*[retrieval_service.retrieve("refund window", None, user_id="u") for _ in range(6)])
    assert running["peak"] == 2


@pytest.mark.asyncio
async def test_a_search_that_waits_too_long_gets_a_busy_reply_not_a_hang(monkeypatch):
    await _fake_searches(monkeypatch, work_seconds=1.0)
    monkeypatch.setattr(settings, "RETRIEVAL_CONCURRENCY", 1)
    monkeypatch.setattr(retrieval_service, "_gate", None)
    first = asyncio.create_task(retrieval_service.retrieve("refund window", None, user_id="u"))
    await asyncio.sleep(0.05)
    with pytest.raises(AppException) as busy:
        await retrieval_service.retrieve("uptime", None, user_id="u")
    assert busy.value.status_code == 503 and "busy" in busy.value.detail
    await first  # the one being served is not affected
    # and the slot is released afterwards
    await retrieval_service.retrieve("again", None, user_id="u")


@pytest.mark.asyncio
async def test_reranking_does_not_freeze_the_event_loop(monkeypatch):
    await _fake_searches(monkeypatch, work_seconds=0)
    monkeypatch.setattr(retrieval_service.reranker_service, "rerank", lambda q, t, k: (time.sleep(0.4), [(0, 2.0)])[1])

    ticks = []

    async def heartbeat():
        for _ in range(8):
            ticks.append(time.perf_counter())
            await asyncio.sleep(0.05)

    await asyncio.gather(retrieval_service.retrieve("refund window", None, user_id="u"), heartbeat())
    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    assert max(gaps) < 0.25  # a blocking rerank would leave a ~0.4 s hole in the heartbeat


# ---- query embedding cache ------------------------------------------------------------------------

def test_a_repeated_query_is_embedded_once(monkeypatch):
    embedding_service._query_cache.clear()
    calls = []
    monkeypatch.setattr(embedding_service, "generate_embeddings", lambda texts: calls.append(texts) or [[0.1, 0.2]])
    assert embedding_service.embed_query("What is the refund window?") == [0.1, 0.2]
    assert embedding_service.embed_query("  what is the refund window? ") == [0.1, 0.2]
    assert len(calls) == 1
    embedding_service._query_cache.clear()


# ---- compression only for the UI, never for streamed API responses -------------------------------------

def _app():
    app = FastAPI()

    @app.get("/api/v1/stream")
    async def stream():
        async def gen():
            for i in range(3):
                yield f"data: {'x' * 400}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/v1/big")
    async def big():
        return PlainTextResponse("y" * 5000)

    @app.get("/page")
    async def page():
        return PlainTextResponse("z" * 5000)

    app.add_middleware(UIGZipMiddleware)
    return app


async def _get(app, path, **kw):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.get(path, headers={"Accept-Encoding": "gzip"}, **kw)


@pytest.mark.asyncio
async def test_ui_files_are_compressed_but_api_responses_are_not():
    app = _app()
    page = await _get(app, "/page")
    assert page.headers.get("content-encoding") == "gzip" and page.text == "z" * 5000
    assert len(gzip.compress(b"z" * 5000)) < 5000

    for path in ("/api/v1/stream", "/api/v1/big"):
        r = await _get(app, path)
        assert "content-encoding" not in r.headers  # streamed events must reach the browser as they are written


@pytest.mark.asyncio
async def test_hashed_assets_cache_for_a_year_and_pages_always_revalidate(tmp_path):
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "login").mkdir()
    (tmp_path / "login" / "index.html").write_text("<h1>login</h1>")
    (tmp_path / "_next" / "static" / "chunks").mkdir(parents=True)
    (tmp_path / "_next" / "static" / "chunks" / "app-abc123.js").write_text("console.log(1)")
    (tmp_path / "logo.svg").write_text("<svg/>")
    app = FastAPI()
    mount_frontend(app, tmp_path)

    assert (await _get(app, "/_next/static/chunks/app-abc123.js")).headers["cache-control"] == "public, max-age=31536000, immutable"
    assert (await _get(app, "/")).headers["cache-control"] == "no-cache"
    assert (await _get(app, "/login/")).headers["cache-control"] == "no-cache"
    assert (await _get(app, "/logo.svg")).headers["cache-control"] == "public, max-age=86400"


# ---- rate limits follow the person, not the address ----------------------------------------------------

def _limited_app(max_requests=3, anonymous=2):
    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_seconds=60, anonymous_max_requests=anonymous)
    return app


async def _hits(app, n, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return [(await c.get("/api/v1/ping", headers=headers)).status_code for _ in range(n)]


@pytest.mark.asyncio
async def test_two_users_on_one_address_do_not_share_an_allowance():
    from app.core.auth import create_access_token

    app = _limited_app(max_requests=3)
    alice, bob = create_access_token("alice"), create_access_token("bob")
    assert await _hits(app, 4, alice) == [200, 200, 200, 429]
    assert await _hits(app, 3, bob) == [200, 200, 200]  # same IP, fresh allowance


@pytest.mark.asyncio
async def test_callers_without_a_valid_token_share_the_stricter_address_limit():
    app = _limited_app(anonymous=2)
    assert await _hits(app, 3) == [200, 200, 429]
    assert await _hits(_limited_app(anonymous=2), 3, "not-a-token") == [200, 200, 429]
