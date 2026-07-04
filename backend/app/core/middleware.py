"""Security headers and request middleware."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .rate_limit import rate_limiter

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        client = request.client.host if request.client else "unknown"

        if not request.url.path.startswith("/health") and not rate_limiter.allow(client):
            logger.warning("Rate limit exceeded client=%s path=%s", client, request.url.path)
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again shortly."})

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        logger.info("%s %s %s %.2fms", request.method, request.url.path, response.status_code, elapsed_ms)
        return response
