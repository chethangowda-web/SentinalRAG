import logging

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.exceptions import AppException, app_exception_handler, global_exception_handler
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    setup_cors(application)

    application.include_router(api_v1_router)

    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(Exception, global_exception_handler)

    return application


app = create_app()


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
