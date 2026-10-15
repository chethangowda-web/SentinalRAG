from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.api.v1 import auth as auth_module
from app.core.auth import hash_password
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.ratelimit import SlidingWindowCounter
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.user import User

REGISTER = {"name": "New User", "email": "new@example.com", "password": "Passw0rd!x"}


def test_sliding_window_counts_and_resets(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("app.core.ratelimit.time.monotonic", lambda: clock[0])
    counter = SlidingWindowCounter(max_events=2, window_seconds=60)
    counter.record("k")
    counter.record("k")
    with pytest.raises(AppException) as exc:
        counter.enforce("k", "Slow down.")
    assert exc.value.status_code == 429 and "Try again" in exc.value.detail
    clock[0] += 61  # window passed
    counter.enforce("k", "Slow down.")
    counter.record("k")
    counter.reset("k")
    assert counter.count("k") == 0


@pytest.mark.asyncio
async def test_auth_config_reports_whether_an_invite_is_needed(async_client, monkeypatch):
    assert (await async_client.get("/api/v1/auth/config")).json() == {"registration_requires_code": False}
    monkeypatch.setattr(settings, "REGISTRATION_CODE", "letmein")
    assert (await async_client.get("/api/v1/auth/config")).json() == {"registration_requires_code": True}


@pytest.mark.asyncio
async def test_registration_needs_the_invite_code_when_configured(async_client, monkeypatch):
    monkeypatch.setattr(settings, "REGISTRATION_CODE", "letmein")
    assert (await async_client.post("/api/v1/auth/register", json=REGISTER)).status_code == 403
    wrong = await async_client.post("/api/v1/auth/register", json={**REGISTER, "invite_code": "nope"})
    assert wrong.status_code == 403
    ok = await async_client.post("/api/v1/auth/register", json={**REGISTER, "invite_code": "letmein"})
    assert ok.status_code == 201


@pytest.mark.asyncio
async def test_signups_are_rate_limited_per_address(async_client, monkeypatch):
    monkeypatch.setattr(auth_module._register_attempts, "max_events", 2)
    for i in range(2):
        r = await async_client.post("/api/v1/auth/register", json={**REGISTER, "email": f"u{i}@example.com"})
        assert r.status_code == 201
    third = await async_client.post("/api/v1/auth/register", json={**REGISTER, "email": "u3@example.com"})
    assert third.status_code == 429


@pytest.mark.asyncio
async def test_repeated_failed_logins_are_locked_out(async_client, monkeypatch):
    monkeypatch.setattr(auth_module._login_failures_by_email, "max_events", 3)
    await async_client.post("/api/v1/auth/register", json=REGISTER)
    bad = {"email": REGISTER["email"], "password": "wrong-password"}
    for _ in range(3):
        assert (await async_client.post("/api/v1/auth/login", json=bad)).status_code == 401
    assert (await async_client.post("/api/v1/auth/login", json=bad)).status_code == 429
    # Even the right password is refused while locked out
    good = {"email": REGISTER["email"], "password": REGISTER["password"]}
    assert (await async_client.post("/api/v1/auth/login", json=good)).status_code == 429


@pytest.mark.asyncio
async def test_a_successful_login_clears_earlier_failures(async_client, monkeypatch):
    monkeypatch.setattr(auth_module._login_failures_by_email, "max_events", 3)
    await async_client.post("/api/v1/auth/register", json=REGISTER)
    bad = {"email": REGISTER["email"], "password": "wrong-password"}
    for _ in range(2):
        await async_client.post("/api/v1/auth/login", json=bad)
    good = {"email": REGISTER["email"], "password": REGISTER["password"]}
    assert (await async_client.post("/api/v1/auth/login", json=good)).status_code == 200
    for _ in range(2):  # the two earlier failures no longer count
        assert (await async_client.post("/api/v1/auth/login", json=bad)).status_code == 401


@pytest.mark.asyncio
async def test_upload_is_refused_over_the_document_quota(async_client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_DOCUMENTS_PER_USER", 0)
    r = await async_client.post("/api/v1/ingest", files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert r.status_code == 429 and "Document limit" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_is_refused_over_the_storage_quota(async_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_STORAGE_MB_PER_USER", 1)
    db_session.add(Document(id="big", filename="big.pdf", file_type="pdf", file_size=1024 * 1024, user_id=test_user.id))
    await db_session.commit()
    r = await async_client.post("/api/v1/ingest", files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert r.status_code == 429 and "Storage limit" in r.json()["detail"]


@pytest.mark.asyncio
async def test_chat_is_refused_over_the_daily_quota(async_client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_CHATS_PER_USER_PER_DAY", 0)
    r = await async_client.post("/api/v1/chat", json={"question": "What is the policy?"})
    assert r.status_code == 429 and "Daily question limit" in r.json()["detail"]


@pytest.mark.asyncio
async def test_streaming_chat_reports_the_quota_as_an_error_event(async_client):
    # The stream opens its own DB session, so stub the check rather than seeding that session.
    async def over_quota(db, user_id):
        raise AppException(status_code=429, detail="Daily question limit reached (1 per 24 hours).")

    with patch("app.api.v1.chat.check_chat_quota", over_quota):
        r = await async_client.post("/api/v1/chat/stream", json={"question": "What is the policy?"})
    assert "event: error" in r.text and "Daily question limit" in r.text


@pytest.mark.asyncio
async def test_delete_account_requires_the_password_and_removes_everything(async_client, db_session, test_user):
    test_user.password_hash = hash_password("Correct-Horse-1")
    db_session.add(Document(id="d1", filename="a.pdf", file_type="pdf", user_id=test_user.id))
    db_session.add(ChatSession(id="s1", user_id=test_user.id, title="t"))
    await db_session.commit()

    wrong = await async_client.request("DELETE", "/api/v1/auth/me", json={"password": "nope"})
    assert wrong.status_code == 403

    with patch("app.api.v1.auth.delete_document_vectors") as vectors:
        ok = await async_client.request("DELETE", "/api/v1/auth/me", json={"password": "Correct-Horse-1"})
    assert ok.status_code == 204
    vectors.assert_called_once_with("d1")
    for model in (User, Document, ChatSession):
        assert (await db_session.execute(select(func.count()).select_from(model))).scalar() == 0


@pytest.mark.asyncio
async def test_security_headers_and_docs_exemption(async_client):
    api = await async_client.get("/api/v1/health", headers={"x-forwarded-proto": "https"})
    assert "default-src 'self'" in api.headers["content-security-policy"]
    assert "max-age=" in api.headers["strict-transport-security"]
    assert api.headers["x-frame-options"] == "DENY"
    docs = await async_client.get("/docs")
    assert "content-security-policy" not in docs.headers  # Swagger UI loads assets from a CDN


@pytest.mark.asyncio
async def test_responses_carry_a_request_id(async_client):
    r = await async_client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"
    assert (await async_client.get("/api/v1/health")).headers["x-request-id"]
