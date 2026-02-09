"""Rate limiting middleware for HardForge API."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    In production, use Redis for distributed rate limiting.
    """

    # Prune stale client keys every 5 minutes
    _CLEANUP_INTERVAL = 300

    def __init__(self, app, requests_per_minute: int = 60, ai_requests_per_minute: int = 10, auth_requests_per_minute: int = 5):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.ai_requests_per_minute = ai_requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _get_client_id(self, request: Request) -> str:
        """Get a client identifier from the request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_ai_route(self, path: str) -> bool:
        """Check if this route triggers AI API calls."""
        ai_routes = ["/api/parse-intent", "/api/analyze-feasibility"]
        return any(path.startswith(route) for route in ai_routes)

    def _is_auth_route(self, path: str) -> bool:
        """Check if this is an authentication route (strict rate limit to prevent brute force)."""
        auth_routes = ["/api/auth/signup", "/api/auth/login"]
        return any(path.startswith(route) for route in auth_routes)

    def _cleanup_stale_keys(self) -> None:
        """Remove client keys with no recent requests to prevent memory leak (S-7)."""
        now = time.time()
        if now - self._last_cleanup < self._CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        window_start = now - 60
        stale_keys = [
            key for key, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] < window_start
        ]
        for key in stale_keys:
            del self._requests[key]

    def _check_rate(self, client_id: str, limit: int) -> bool:
        """Check if client is within rate limit."""
        now = time.time()
        window_start = now - 60  # 1-minute window

        # Clean old entries for this client
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]

        if len(self._requests[client_id]) >= limit:
            return False

        self._requests[client_id].append(now)
        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/api/health":
            return await call_next(request)

        # Periodically clean up stale keys
        self._cleanup_stale_keys()

        client_id = self._get_client_id(request)

        # Apply strictest limits to auth routes (prevent brute force)
        if self._is_auth_route(request.url.path):
            if not self._check_rate(f"{client_id}:auth", self.auth_requests_per_minute):
                raise HTTPException(
                    status_code=429,
                    detail="Too many authentication attempts. Please wait before trying again."
                )

        # Apply stricter limits to AI routes
        if self._is_ai_route(request.url.path):
            if not self._check_rate(f"{client_id}:ai", self.ai_requests_per_minute):
                raise HTTPException(
                    status_code=429,
                    detail="AI request rate limit exceeded. Please wait before trying again."
                )

        # General rate limit
        if not self._check_rate(client_id, self.requests_per_minute):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait before trying again."
            )

        return await call_next(request)
