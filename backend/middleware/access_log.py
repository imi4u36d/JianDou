"""Request access-log middleware for the JianDou API.

Emits one log line per request so that every HTTP call is traceable:

    [INFO] jiandou.middleware.access: GET /api/v3/tasks 200 12ms
"""
from __future__ import annotations

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("jiandou.middleware.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status code and latency."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "%s %s 500 %dms", request.method, request.url.path, elapsed_ms
            )
            raise

        elapsed_ms = int((time.monotonic() - start) * 1000)
        status = response.status_code

        if 200 <= status < 400:
            log_fn = logger.info
        elif 400 <= status < 500:
            log_fn = logger.warning
        else:
            log_fn = logger.error

        log_fn("%s %s %d %dms", request.method, request.url.path, status, elapsed_ms)
        return response
