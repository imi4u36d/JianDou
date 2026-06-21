"""SPA fallback middleware: serves index.html for client-side routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SpaFallbackMiddleware(BaseHTTPMiddleware):
    """Serves the SPA index.html for non-API paths that would otherwise 404.

    Must be registered *after* all API routers so that API 404s are not
    accidentally caught by this middleware.
    """

    def __init__(self, app, *, web_static_dir: str = "static/web") -> None:
        super().__init__(app)
        self._index_path = Path(web_static_dir) / "index.html"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code != 404:
            return response

        path = request.url.path
        if path.startswith("/api/") or path.startswith("/docs") or path.startswith("/openapi"):
            return response

        if not self._index_path.is_file():
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        return FileResponse(str(self._index_path))
