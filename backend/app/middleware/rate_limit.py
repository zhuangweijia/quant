import time
from collections import defaultdict

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger()

_EXEMPT_PATHS = {"/health", "/api/docs", "/api/redoc", "/api/openapi.json", "/docs", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_limit: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"token:{auth_header[7:20]}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _check_rate(self, client_id: str) -> tuple[bool, int, int, int]:
        now = time.time()
        limit = self.default_limit
        key = f"{client_id}:{limit}"
        window = self._windows[key]

        window[:] = [t for t in window if now - t < 60]
        remaining = max(0, limit - len(window))
        reset_time = int(now + 60)

        if len(window) >= limit:
            return False, limit, 0, reset_time

        window.append(now)
        return True, limit, remaining - 1, reset_time

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in _EXEMPT_PATHS:
            return await call_next(request)

        client_id = self._get_client_id(request)
        allowed, limit, remaining, reset_time = self._check_rate(client_id)

        if not allowed:
            logger.warning("rate_limit.exceeded", client_id=client_id, path=path)
            response = JSONResponse(
                status_code=429,
                content={"code": 429, "message": "请求过于频繁，请稍后重试"},
            )
        else:
            response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        return response
