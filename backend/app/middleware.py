"""Middleware for rate limiting and request tracking."""

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limit: max requests per window per client IP
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_SEARCH = 10  # max search requests per minute
RATE_LIMIT_MAX_SUMMARIZE = 5  # max summarize requests per minute


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter using sliding window per IP."""

    def __init__(self, app):
        super().__init__(app)
        # {ip: [(timestamp, path), ...]}
        self._requests: dict[str, list[tuple[float, str]]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit write endpoints
        path = request.url.path
        if request.method != "POST" or path not in (
            "/api/v1/search",
            "/api/v1/summarize",
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        self._requests[client_ip] = [
            (ts, p)
            for ts, p in self._requests[client_ip]
            if now - ts < RATE_LIMIT_WINDOW
        ]

        # Count requests to this endpoint
        limit = (
            RATE_LIMIT_MAX_SEARCH
            if "search" in path
            else RATE_LIMIT_MAX_SUMMARIZE
        )
        endpoint_count = sum(
            1 for _, p in self._requests[client_ip] if p == path
        )

        if endpoint_count >= limit:
            logger.warning(
                "Rate limit exceeded for %s on %s (%d/%d)",
                client_ip, path, endpoint_count, limit,
            )
            return Response(
                content='{"error":"Too many requests. Please try again later."}',
                status_code=429,
                media_type="application/json",
            )

        self._requests[client_ip].append((now, path))
        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Logs request timing for observability."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        if request.url.path not in ("/health",):
            logger.info(
                "%s %s %d %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
        return response
