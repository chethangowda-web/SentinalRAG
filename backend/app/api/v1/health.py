import logging

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    logger.info("Health check requested")
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
    )
