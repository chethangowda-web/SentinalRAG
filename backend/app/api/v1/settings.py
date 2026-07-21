import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

_SETTINGS_FILE = Path("user_settings.json")


class SettingsResponse(BaseModel):
    embedding_model: str
    embedding_dimension: int
    chunk_size: int
    chunk_overlap: int
    qdrant_collection: str
    llm_model: str
    llm_temperature: float
    max_retries: int
    rate_limit_max_requests: int
    rate_limit_window_seconds: int
    ocr_language: str
    deepseek_api_key_set: bool
    hybrid_search_enabled: bool = True


class SettingsUpdate(BaseModel):
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    llm_temperature: float | None = None
    max_retries: int | None = None
    ocr_language: str | None = None


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    return SettingsResponse(
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dimension=settings.EMBEDDING_DIMENSION,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        qdrant_collection=settings.QDRANT_COLLECTION,
        llm_model=settings.LLM_MODEL,
        llm_temperature=settings.LLM_TEMPERATURE,
        max_retries=settings.MAX_RETRIES,
        rate_limit_max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
        rate_limit_window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        ocr_language=settings.OCR_LANGUAGE,
        deepseek_api_key_set=bool(settings.effective_llm_api_key),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate):
    overrides = {}
    if _SETTINGS_FILE.exists():
        with open(_SETTINGS_FILE) as f:
            overrides = json.load(f)
    updates = body.model_dump(exclude_none=True)
    overrides.update(updates)
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(overrides, f, indent=2)
    logger.info("Settings updated: %s", updates)
    return await get_settings()


@router.post("/settings/reset")
async def reset_settings():
    if _SETTINGS_FILE.exists():
        _SETTINGS_FILE.unlink()
        logger.info("Settings reset to defaults")
    return {"status": "reset"}


@router.get("/settings/health")
async def settings_health_check():
    results = {
        "backend": {"status": "healthy", "version": settings.APP_VERSION},
        "qdrant": {"status": "unknown"},
        "database": {"status": "unknown"},
        "llm": {"status": "unknown"},
    }

    # Check Qdrant
    try:
        from app.core.qdrant import get_qdrant_client
        client = get_qdrant_client()
        client.get_collections()
        results["qdrant"] = {"status": "healthy"}
    except Exception as e:
        results["qdrant"] = {"status": "unhealthy", "error": str(e)}

    # Check LLM
    if settings.effective_llm_api_key:
        results["llm"] = {"status": "configured", "model": settings.effective_llm_model}
    else:
        results["llm"] = {"status": "not_configured"}

    return results
