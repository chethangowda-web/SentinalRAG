import re
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.v1 import auth as auth_module
from app.api.v1.auth import _utcnow
from app.core.auth import create_access_token
from app.core.config import settings
from app.main import app
from app.models.password_reset import PasswordReset
from app.services.email_service import EmailError


@pytest_asyncio.fixture
async def auth_client(db_session):
    """A client with real authentication (the shared one pretends everybody is the test user)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    auth_module.reset_rate_limits()
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")
    yield
    auth_module.reset_rate_limits()


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    async def fake_send(to, subject, text):
        sent.append((to, subject, text))

    monkeypatch.setattr(auth_module, "send_email", fake_send)
    return sent


async def _register(client, email="reset@example.com", password="Old-Password-1"):
    r = await client.post("/api/v1/auth/register", json={"name": "Reset Me", "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _link_token(sent):
    return re.search(r"token=([\w-]+)", sent[-1][2]).group(1)


@pytest.mark.asyncio
async def test_a_reset_link_sets_a_new_password_once(auth_client, outbox):
    await _register(auth_client)
    r = await auth_client.post("/api/v1/auth/forgot-password", json={"email": "Reset@Example.com"})
    assert r.status_code == 202
    assert len(outbox) == 1 and outbox[0][0] == "reset@example.com"
    token = _link_token(outbox)

    done = await auth_client.post("/api/v1/auth/reset-password", json={"token": token, "password": "New-Password-2"})
    assert done.status_code == 204

    login = await auth_client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "New-Password-2"})
    assert login.status_code == 200
    old = await auth_client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "Old-Password-1"})
    assert old.status_code == 401

    again = await auth_client.post("/api/v1/auth/reset-password", json={"token": token, "password": "Third-Password-3"})
    assert again.status_code == 400  # a link works once


@pytest.mark.asyncio
async def test_the_answer_does_not_reveal_whether_an_account_exists(auth_client, outbox):
    await _register(auth_client)
    known = await auth_client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    unknown = await auth_client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert [m[0] for m in outbox] == ["reset@example.com"]


@pytest.mark.asyncio
async def test_a_failing_mail_provider_is_not_reported_to_the_caller(auth_client, monkeypatch):
    await _register(auth_client)

    async def broken(*args):
        raise EmailError("provider down")

    monkeypatch.setattr(auth_module, "send_email", broken)
    r = await auth_client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 202


@pytest.mark.asyncio
async def test_expired_and_unknown_links_are_refused(auth_client, db_session, outbox):
    await _register(auth_client)
    await auth_client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    token = _link_token(outbox)

    row = (await db_session.execute(select(PasswordReset))).scalar_one()
    row.expires_at = _utcnow() - timedelta(minutes=1)
    await db_session.commit()

    expired = await auth_client.post("/api/v1/auth/reset-password", json={"token": token, "password": "New-Password-2"})
    unknown = await auth_client.post("/api/v1/auth/reset-password", json={"token": "made-up", "password": "New-Password-2"})
    assert expired.status_code == unknown.status_code == 400


@pytest.mark.asyncio
async def test_only_the_hash_of_the_secret_is_stored(auth_client, db_session, outbox):
    await _register(auth_client)
    await auth_client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    token = _link_token(outbox)
    stored = (await db_session.execute(select(PasswordReset))).scalar_one()
    assert token not in stored.token_hash and len(stored.token_hash) == 64


@pytest.mark.asyncio
async def test_resetting_signs_the_account_out_everywhere(auth_client, outbox):
    old_token = await _register(auth_client)
    me = await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me.status_code == 200

    await auth_client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    await auth_client.post("/api/v1/auth/reset-password", json={"token": _link_token(outbox), "password": "New-Password-2"})

    stale = await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert stale.status_code == 401 and "password was changed" in stale.json()["detail"]


@pytest.mark.asyncio
async def test_reset_requests_are_rate_limited_per_account(auth_client, outbox):
    await _register(auth_client)
    codes = [(await auth_client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]


@pytest.mark.asyncio
async def test_the_feature_is_off_without_an_email_provider(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    assert (await auth_client.get("/api/v1/auth/config")).json()["password_reset_available"] is False
    r = await auth_client.post("/api/v1/auth/forgot-password", json={"email": "x@example.com"})
    assert r.status_code == 503 and "not set up" in r.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_keeps_this_device_and_ends_the_others(auth_client):
    token = await _register(auth_client)
    headers = {"Authorization": f"Bearer {token}"}

    wrong = await auth_client.post("/api/v1/auth/change-password", headers=headers,
                                    json={"current_password": "nope-nope-1", "new_password": "New-Password-2"})
    assert wrong.status_code == 403

    changed = await auth_client.post("/api/v1/auth/change-password", headers=headers,
                                      json={"current_password": "Old-Password-1", "new_password": "New-Password-2"})
    assert changed.status_code == 200
    fresh = {"Authorization": f"Bearer {changed.json()['access_token']}"}

    assert (await auth_client.get("/api/v1/auth/me", headers=fresh)).status_code == 200
    assert (await auth_client.get("/api/v1/auth/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_logout_everywhere_ends_every_session(auth_client):
    token = await _register(auth_client)
    headers = {"Authorization": f"Bearer {token}"}
    assert (await auth_client.post("/api/v1/auth/logout-everywhere", headers=headers)).status_code == 204
    assert (await auth_client.get("/api/v1/auth/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_tokens_issued_before_versioning_still_work(auth_client):
    token = await _register(auth_client)
    me = (await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).json()
    legacy = create_access_token(me["id"])  # version 0, as every token was before this feature
    assert (await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy}"})).status_code == 200
