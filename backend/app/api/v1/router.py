from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.embed import router as embed_router
from app.api.v1.search import router as search_router
from app.api.v1.chat import router as chat_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.traces import router as traces_router
from app.api.v1.documents import router as documents_router
from app.api.v1.settings import router as settings_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(ingest_router, tags=["ingest"])
api_v1_router.include_router(embed_router, tags=["embed"])
api_v1_router.include_router(search_router, tags=["search"])
api_v1_router.include_router(chat_router, tags=["chat"])
api_v1_router.include_router(evaluation_router, tags=["evaluation"])
api_v1_router.include_router(metrics_router, tags=["metrics"])
api_v1_router.include_router(traces_router, tags=["traces"])
api_v1_router.include_router(documents_router, tags=["documents"])
api_v1_router.include_router(settings_router, tags=["settings"])
