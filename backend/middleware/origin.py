"""Origin-guard middleware: rejects untrusted origins for state-changing requests."""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

UNSAFE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _normalize_origin(origin: str) -> str:
    raw = (origin or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    return f"{scheme}://{hostname}{port}"


class OriginGuardMiddleware(BaseHTTPMiddleware):
    """Rejects state-changing requests from untrusted origins.

    Configured via :func:`_trusted_origins` which reads settings
    at request time so configuration changes take effect without a restart.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method.upper() in UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if origin and _normalize_origin(origin) not in _trusted_origins(request):
                return JSONResponse(status_code=403, content={"detail": "untrusted_origin"})
        return await call_next(request)


def _trusted_origins(request: Request) -> set[str]:
    from backend.config import settings

    trusted: set[str] = set()
    # web_origin may be a single URL or comma-separated list
    for raw in settings.web_origin.split(","):
        trusted.add(_normalize_origin(raw))
    trusted.add(_normalize_origin(str(request.base_url)))
    for origin in settings.trusted_origins.split(","):
        trusted.add(_normalize_origin(origin))
    # For localhost / 127.0.0.1, also trust the port-less variant
    # so that any dev-server port is accepted.
    extra: set[str] = set()
    for o in trusted:
        parsed = urlsplit(o)
        if parsed.hostname in ("localhost", "127.0.0.1") and parsed.port:
            extra.add(f"{parsed.scheme}://{parsed.hostname}")
    trusted.update(extra)
    return {origin for origin in trusted if origin}
