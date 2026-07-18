from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.embed import router as embed_router
from app.api.v1.search import router as search_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(ingest_router)
api_v1_router.include_router(embed_router)
api_v1_router.include_router(search_router)
