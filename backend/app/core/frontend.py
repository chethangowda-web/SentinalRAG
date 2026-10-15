"""Serve the statically exported frontend from the API process.

In the single-container deployment the Dockerfile copies the Next.js export to `static/`
next to the `app/` package. When that directory is absent (local development, tests, the
split docker-compose setup) nothing is mounted and the API behaves exactly as before.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

logger = logging.getLogger(__name__)


def frontend_dist_dir() -> Path | None:
    configured = Path(settings.FRONTEND_DIST) if settings.FRONTEND_DIST else Path(__file__).resolve().parents[2] / "static"
    return configured if (configured / "index.html").is_file() else None


def mount_frontend(app: FastAPI, directory: Path | None = None) -> bool:
    """Mount the exported site at "/". Call after every API route is registered.

    Returns whether anything was mounted.
    """
    directory = directory or frontend_dist_dir()
    if directory is None:
        return False
    # html=True serves /login/ from login/index.html and 404.html for unknown pages.
    app.mount("/", StaticFiles(directory=str(directory), html=True), name="frontend")
    logger.info("Serving frontend from %s", directory)
    return True
