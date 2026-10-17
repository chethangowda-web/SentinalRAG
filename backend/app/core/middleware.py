import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # The outer metrics middleware (main.py) assigns the id first so its own log lines carry it.
        request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        logger = logging.getLogger("sentinelrag.middleware")
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": elapsed_ms,
            },
        )

        return response


# The exported UI uses inline scripts/styles, so 'unsafe-inline' is needed for both; everything else is locked to
# this origin. Swagger UI (/docs) loads assets from a CDN, so it is exempt.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
_CSP_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if not request.url.path.startswith(_CSP_EXEMPT_PREFIXES):
            response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


def _rate_limit_key(request: Request) -> tuple[str, bool]:
    """Who a request counts against: the signed-in user, else the client IP. Returns (key, is_user).

    People behind one address (a school, an office) must not use up each other's allowance.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        from app.core.auth import decode_access_token

        user_id = decode_access_token(auth[7:].strip())
        if user_id:
            return f"user:{user_id}", True
    return f"ip:{request.client.host if request.client else 'unknown'}", False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 240, window_seconds: int = 60, anonymous_max_requests: int = 120):
        super().__init__(app)
        self.max_requests = max_requests
        self.anonymous_max_requests = anonymous_max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}
        self._requests_seen = 0

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            client_ip, is_user = _rate_limit_key(request)
            limit = self.max_requests if is_user else self.anonymous_max_requests
            now = time.time()
            window_start = now - self.window_seconds

            if client_ip in self.requests:
                self.requests[client_ip] = [
                    t for t in self.requests[client_ip] if t > window_start
                ]

            # Drop IPs with no requests left in the window so the dict can't grow without bound.
            self._requests_seen += 1
            if self._requests_seen % 1000 == 0:
                self.requests = {
                    ip: ts for ip, ts in self.requests.items() if ts and ts[-1] > window_start
                }

            if len(self.requests.get(client_ip, [])) >= limit:
                logging.getLogger("sentinelrag.security").warning(
                    "Rate limit exceeded for %s", client_ip,
                    extra={"request_id": getattr(request.state, "request_id", "rate-limited")},
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )

            self.requests.setdefault(client_ip, []).append(now)

        return await call_next(request)


class UIGZipMiddleware:
    """gzip for the web UI's files only.

    Starlette's GZipMiddleware would also compress the /api/ responses, including the chat's server-sent
    events, which it buffers until they finish: answers would stop streaming.
    """

    def __init__(self, app, minimum_size: int = 800):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not scope["path"].startswith("/api/"):
            await self.gzip(scope, receive, send)
        else:
            await self.app(scope, receive, send)


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(UIGZipMiddleware)
    app.add_middleware(SecureHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        anonymous_max_requests=settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS,
    )
