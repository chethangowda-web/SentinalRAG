import logging
import os
import time

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse, ReadinessResponse, MetricsResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_start_time = time.time()


async def _check_database() -> dict:
    try:
        from app.core.database import get_engine
        from sqlalchemy import text as sa_text
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


def _check_qdrant() -> dict:
    try:
        from app.core.qdrant import get_qdrant_client
        client = get_qdrant_client()
        client.get_collections()
        return {"status": "healthy"}
    except Exception as e:
        logger.warning("Qdrant health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


def _check_ocr() -> dict:
    try:
        from app.services.ocr_service import TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            return {"status": "healthy"}
        return {"status": "unavailable", "error": "pytesseract not installed"}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


def _check_embedding() -> dict:
    try:
        from app.services.embedding_service import is_model_loaded
        if is_model_loaded():
            return {"status": "healthy", "model": settings.EMBEDDING_MODEL}
        return {"status": "unhealthy", "error": "Model not loaded"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_llm() -> dict:
    if settings.DEEPSEEK_API_KEY:
        return {"status": "configured", "model": settings.LLM_MODEL}
    return {"status": "unconfigured", "error": "DEEPSEEK_API_KEY not set"}


def _get_disk_usage() -> dict:
    try:
        upload = settings.UPLOAD_DIR
        processed = settings.PROCESSED_DIR
        upload_size = sum(f.stat().st_size for f in upload.rglob("*") if f.is_file()) if upload.exists() else 0
        processed_size = sum(f.stat().st_size for f in processed.rglob("*") if f.is_file()) if processed.exists() else 0
        return {
            "upload_dir_mb": round(upload_size / (1024 * 1024), 2),
            "processed_dir_mb": round(processed_size / (1024 * 1024), 2),
            "total_mb": round((upload_size + processed_size) / (1024 * 1024), 2),
        }
    except Exception as e:
        return {"error": str(e)}


def _get_memory_usage() -> dict:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_mb": round(mem.total / (1024 * 1024), 1),
            "available_mb": round(mem.available / (1024 * 1024), 1),
            "used_mb": round(mem.used / (1024 * 1024), 1),
            "percent": mem.percent,
        }
    except ImportError:
        return {"note": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        uptime_seconds=int(time.time() - _start_time),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    db = await _check_database()
    qdrant = _check_qdrant()
    ocr = _check_ocr()
    embedding = _check_embedding()
    llm = _check_llm()

    all_healthy = all(
        s["status"] == "healthy"
        for s in [db, qdrant]
    )

    return ReadinessResponse(
        ready=all_healthy,
        database=db,
        qdrant=qdrant,
        ocr=ocr,
        embedding=embedding,
        llm=llm,
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics():
    return MetricsResponse(
        version=settings.APP_VERSION,
        uptime_seconds=int(time.time() - _start_time),
        database=await _check_database(),
        qdrant=_check_qdrant(),
        ocr=_check_ocr(),
        embedding=_check_embedding(),
        llm=_check_llm(),
        disk=_get_disk_usage(),
        memory=_get_memory_usage(),
    )


