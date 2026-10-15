import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.frontend import frontend_dist_dir, mount_frontend


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "login").mkdir()
    (tmp_path / "login" / "index.html").write_text("<h1>login</h1>")
    (tmp_path / "404.html").write_text("<h1>not found page</h1>")
    return tmp_path


def _app_with_api() -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/health")
    async def health():
        return {"status": "healthy"}

    return app


async def _get(app: FastAPI, path: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, follow_redirects=True)


@pytest.mark.asyncio
async def test_site_is_served_and_api_routes_still_win(site):
    app = _app_with_api()
    assert mount_frontend(app, site) is True

    assert "home" in (await _get(app, "/")).text
    assert "login" in (await _get(app, "/login/")).text
    assert "login" in (await _get(app, "/login")).text  # redirected to /login/
    assert (await _get(app, "/api/v1/health")).json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_unknown_pages_get_the_exported_404_page(site):
    app = _app_with_api()
    mount_frontend(app, site)
    response = await _get(app, "/nope/")
    assert response.status_code == 404
    assert "not found page" in response.text


def test_nothing_is_mounted_without_a_site(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_DIST", str(tmp_path))  # exists but has no index.html
    app = _app_with_api()
    assert mount_frontend(app) is False
    assert not [r for r in app.routes if getattr(r, "name", "") == "frontend"]


def test_dist_dir_requires_an_index_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_DIST", str(tmp_path))
    assert frontend_dist_dir() is None
    (tmp_path / "index.html").write_text("x")
    assert frontend_dist_dir() == tmp_path
