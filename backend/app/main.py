import asyncio
import gc
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.frontend import mount_frontend
from app.core.exceptions import AppException, app_exception_handler, global_exception_handler, http_exception_handler
from fastapi.exceptions import HTTPException
from app.core.logging import setup_logging
from app.core.metrics import get_metrics_collector
from app.core.middleware import setup_middleware
from app.core.resource_tracker import get_resource_tracker
from app.services.health_check import wait_for_dependencies
from app.utils.memory import log_memory_usage

setup_logging()
logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()

if settings.SENTRY_DSN:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.SENTRY_DSN, send_default_pii=False, traces_sample_rate=0.0)
        logger.info("Sentry error tracking enabled")
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; error tracking is off")


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting SentinelRAG backend...")
    tracker = get_resource_tracker()
    tracker.start()
    try:
        await wait_for_dependencies()
    except Exception as e:
        logger.error("Service dependencies unavailable: %s", e)
        get_metrics_collector().record_error("dependency_startup_failure")
        raise

    from app.core.database import get_engine, init_db
    _ = get_engine()

    try:
        await init_db()
        logger.info("Database schema up to date")
    except Exception as e:
        logger.error("Database migration failed: %s", e)
        get_metrics_collector().record_error("database_migration_failure")
        if settings.is_sqlite:
            logger.warning("SQLite migration failed — continuing anyway")
        else:
            raise

    try:
        from app.core.database import get_session_maker
        from app.services.indexing_service import recover_interrupted_indexing

        async with get_session_maker()() as session:
            recovered = await recover_interrupted_indexing(session)
        if recovered:
            logger.warning("Marked %d interrupted indexing job(s) as failed so they can be retried", recovered)
        from app.api.v1.evaluation import recover_interrupted_runs

        async with get_session_maker()() as session:
            if await recover_interrupted_runs(session):
                logger.warning("Marked interrupted evaluation run(s) as failed")
    except Exception as e:
        logger.warning("Could not check for interrupted indexing jobs: %s", e)

    try:
        import qdrant_client
        logger.info("Qdrant client version: %s", qdrant_client.__version__)
    except Exception:
        pass

    if settings.PRELOAD_MODELS:
        try:
            from app.services import embedding_service, reranker_service
            await asyncio.to_thread(embedding_service._load_model)
            await asyncio.to_thread(reranker_service._load_reranker)
            logger.info("Embedding and reranker models preloaded")
        except Exception as e:
            logger.warning("Model preload failed, will load on first use: %s", e)
    else:
        # Not the models (memory), only the library imports, done once and early instead of by the first requests
        from app.services.model_loading import preimport_ml_libraries

        warmup = asyncio.create_task(asyncio.to_thread(preimport_ml_libraries))
        _background_tasks.add(warmup)
        warmup.add_done_callback(_background_tasks.discard)

    logger.info("Resource tracking started")
    yield
    tracker.stop()
    collector = get_metrics_collector()
    summary = tracker.summarize()
    gc.collect()
    log_memory_usage("shutdown")
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
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(Exception, global_exception_handler)

    @application.middleware("http")
    async def record_metrics_middleware(request, call_next):
        collector = get_metrics_collector()
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        endpoint = f"{request.method} {request.url.path}"
        logger.info("Incoming request: method=%s path=%s request_id=%s", request.method, request.url.path, request_id)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Request failed: method=%s path=%s request_id=%s", request.method, request.url.path, request_id)
            raise
        elapsed = (time.perf_counter() - start) * 1000
        collector.record_latency(endpoint, elapsed)
        collector.increment("requests.total")
        if response.status_code >= 400:
            collector.record_error(f"http_{response.status_code}")
        logger.info("Request completed: method=%s path=%s status=%d elapsed=%.1fms request_id=%s",
                     request.method, request.url.path, response.status_code, elapsed, request_id)
        return response

    # The exported frontend owns "/" when present; otherwise "/" is a small JSON banner.
    # Mounting must come after every API route so "/api/v1/*" and "/docs" win.
    if not mount_frontend(application):
        @application.get("/")
        async def root():
            return {
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
            }

    return application


app = create_app()
