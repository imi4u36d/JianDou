"""
FastAPI application factory.
"""
from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import PROJECT_ROOT, settings, validate_runtime_settings
from backend.container import AppContainer
from backend.exceptions import InsufficientPermissionsError, InvalidCredentialsError, TokenExpiredError
from backend.logging_config import configure_logging
from backend.middleware import (
    AccessLogMiddleware,
    OriginGuardMiddleware,
    SecurityHeadersMiddleware,
    SpaFallbackMiddleware,
)

logger = logging.getLogger("jiandou.error")


def create_app(start_worker: bool = True) -> FastAPI:
    """Create and configure the FastAPI application.

    ``configure_logging`` is called here (rather than only in ``__main__.py``)
    so that even when the app is started directly with ``uvicorn backend.main:app``
    or imported programmatically (tests, OpenAPI export), log output is never
    silently dropped.

    The function is idempotent — it clears and re-adds handlers each call,
    so calling it from both ``__main__.py`` and here is safe.
    """
    configure_logging(level=logging.INFO, json_format=settings.log_json_format)

    validate_runtime_settings(settings)

    # Create data directories
    Path(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    for d in [settings.uploads_dir, settings.generation_runs_dir, "thumbs"]:
        Path(settings.storage_root, d).mkdir(parents=True, exist_ok=True)

    # Initialize DI container (lazy service creation)
    container = AppContainer(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if start_worker:
            await container.worker_runner.start()
            await container.auto_pilot_runner.start()
        try:
            yield
        finally:
            if start_worker:
                await container.worker_runner.stop()
                await container.auto_pilot_runner.stop()
            await container.task_repository.close()

    app = FastAPI(
        title="JianDou API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env == "dev" else None,
        lifespan=lifespan,
    )


    # -- Auth exception handlers --------------------------------------------
    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(TokenExpiredError)
    async def token_expired_handler(request: Request, exc: TokenExpiredError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(InsufficientPermissionsError)
    async def insufficient_permissions_handler(request: Request, exc: InsufficientPermissionsError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    # -- Global exception handler -------------------------------------------
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch unhandled exceptions, log the traceback, and return a structured 500."""
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"},
        )

    # -- App state (wire container services onto app.state) -----------------
    container.bind_app_state(app)

    # -- Middleware ---------------------------------------------------------
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(OriginGuardMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # -- Routers ------------------------------------------------------------
    from backend.routers import (
        admin,
        auth,
        credits,
        generation,
        health,
        material_assets,
        material_center,
        runtime_config,
        tasks,
        uploads,
        workflows,
    )
    app.include_router(health.router)
    app.include_router(runtime_config.router)
    app.include_router(auth.router)
    app.include_router(credits.router)
    app.include_router(tasks.router)
    app.include_router(generation.router)
    app.include_router(uploads.router)
    app.include_router(workflows.router)
    app.include_router(material_assets.router)
    app.include_router(material_center.router)
    app.include_router(admin.router)

    # -- Static files -------------------------------------------------------
    web_static = Path("static/web")
    if web_static.is_dir():
        app.mount("/", StaticFiles(directory=str(web_static), html=True), name="web")

    # -- SPA fallback -------------------------------------------------------
    spa_index = Path("static/web/index.html")
    if spa_index.is_file():
        app.add_middleware(SpaFallbackMiddleware)

    return app


app = create_app()
