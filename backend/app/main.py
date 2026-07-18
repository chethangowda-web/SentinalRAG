import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.database import init_db
from app.core.exceptions import AppException, app_exception_handler, global_exception_handler
from app.core.logging import setup_logging
from app.core.metrics import get_metrics_collector
from app.core.middleware import setup_middleware
from app.core.resource_tracker import get_resource_tracker

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting SentinelRAG backend...")
    tracker = get_resource_tracker()
    tracker.start()
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        get_metrics_collector().record_error("database_init_failure")
    logger.info("Resource tracking started")
    yield
    tracker.stop()
    collector = get_metrics_collector()
    summary = tracker.summarize()
    logger.info(
        "Shutdown summary: %.1fs uptime, %d resource samples, CPU avg=%.1f%%, mem avg=%.1fMB, %d errors recorded",
        summary.duration_seconds, summary.samples, summary.cpu_avg, summary.memory_avg_mb,
        collector.get_errors().get("total", 0),
    )
    logger.info("Shutting down SentinelRAG backend...")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    setup_cors(application)
    setup_middleware(application)

    application.include_router(api_v1_router)

    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(Exception, global_exception_handler)

    @application.middleware("http")
    async def record_metrics_middleware(request, call_next):
        collector = get_metrics_collector()
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        endpoint = f"{request.method} {request.url.path}"
        collector.record_latency(endpoint, elapsed)
        collector.increment("requests.total")
        if response.status_code >= 400:
            collector.record_error(f"http_{response.status_code}")
        return response

    return application


app = create_app()


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
