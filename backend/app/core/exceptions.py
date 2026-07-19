import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_type: str | None = None) -> None:
        self.status_code = status_code
        self.detail = detail
        self.error_type = error_type or "app_error"


class LLMTimeoutError(AppException):
    def __init__(self, detail: str = "LLM did not respond in time"):
        super().__init__(status_code=504, detail=detail, error_type="llm_timeout")


class QdrantConnectionError(AppException):
    def __init__(self, detail: str = "Vector database is unavailable"):
        super().__init__(status_code=503, detail=detail, error_type="qdrant_down")


class DatabaseConnectionError(AppException):
    def __init__(self, detail: str = "Database is unavailable"):
        super().__init__(status_code=503, detail=detail, error_type="database_down")


class OCRError(AppException):
    def __init__(self, detail: str = "OCR processing failed"):
        super().__init__(status_code=500, detail=detail, error_type="ocr_failure")


class EmbeddingError(AppException):
    def __init__(self, detail: str = "Embedding generation failed"):
        super().__init__(status_code=500, detail=detail, error_type="embedding_failure")


class InvalidUploadError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail, error_type="invalid_upload")


class NetworkError(AppException):
    def __init__(self, detail: str = "External service unreachable"):
        super().__init__(status_code=502, detail=detail, error_type="network_failure")


def _standard_error_response(
    request: Request,
    status_code: int,
    message: str,
    error_type: str,
) -> dict:
    return {
        "error": True,
        "error_code": error_type,
        "message": message,
        "status_code": status_code,
        "request_id": getattr(request.state, "request_id", None),
        "trace_id": getattr(request.state, "trace_id", None),
    }


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(
        "AppException: %s — %s (type=%s)",
        exc.status_code, exc.detail, exc.error_type,
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_standard_error_response(
            request=request,
            status_code=exc.status_code,
            message=exc.detail,
            error_type=exc.error_type or "app_error",
        ),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception: %s",
        str(exc),
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=500,
        content=_standard_error_response(
            request=request,
            status_code=500,
            message="An unexpected internal error occurred. Our team has been notified.",
            error_type="internal_error",
        ),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi.exceptions import HTTPException

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_standard_error_response(
                request=request,
                status_code=exc.status_code,
                message=exc.detail,
                error_type=f"http_{exc.status_code}",
            ),
        )
    return await global_exception_handler(request, exc)
