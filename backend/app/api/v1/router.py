from fastapi import APIRouter, Depends

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.embed import router as embed_router
from app.api.v1.search import router as search_router
from app.api.v1.chat import router as chat_router
from app.api.v1.chat_history import router as chat_history_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.traces import router as traces_router
from app.api.v1.documents import router as documents_router
from app.api.v1.settings import router as settings_router
from app.api.v1.dashboard import router as dashboard_router
from app.core.auth import get_current_user

api_v1_router = APIRouter(prefix="/api/v1")

# Auth routes (public)
api_v1_router.include_router(auth_router, tags=["auth"])

# Protected routes
api_v1_router.include_router(health_router, tags=["health"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(ingest_router, tags=["ingest"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(embed_router, tags=["embed"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(search_router, tags=["search"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(chat_router, tags=["chat"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(chat_history_router, tags=["chat_history"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(evaluation_router, tags=["evaluation"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(metrics_router, tags=["metrics"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(traces_router, tags=["traces"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(documents_router, tags=["documents"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(settings_router, tags=["settings"], dependencies=[Depends(get_current_user)])
api_v1_router.include_router(dashboard_router, tags=["dashboard"], dependencies=[Depends(get_current_user)])
