"""Application assembly for the JianDou FastAPI service."""

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
    CamelCaseJsonMiddleware,
    OriginGuardMiddleware,
    SecurityHeadersMiddleware,
    SpaFallbackMiddleware,
)

logger = logging.getLogger("jiandou.error")


def _prepare_runtime_directories() -> None:
    Path(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    for directory in [settings.uploads_dir, settings.generation_runs_dir, "thumbs"]:
        Path(settings.storage_root, directory).mkdir(parents=True, exist_ok=True)


def _create_lifespan(container: AppContainer, *, start_worker: bool):
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if start_worker:
            await container.worker_runner.start()
            await container.auto_pilot_runner.start()
        try:
            yield
        finally:
            if start_worker:
                await container.auto_pilot_runner.stop()
                await container.worker_runner.stop()
            await container.task_repository.close()
            await container.json_cache.close()

    return lifespan


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(_request: Request, exc: InvalidCredentialsError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(TokenExpiredError)
    async def token_expired_handler(_request: Request, exc: TokenExpiredError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(InsufficientPermissionsError)
    async def insufficient_permissions_handler(_request: Request, exc: InsufficientPermissionsError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


def _register_middleware(app: FastAPI) -> None:
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(OriginGuardMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CamelCaseJsonMiddleware)


def _register_routers(app: FastAPI) -> None:
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

    for router in (
        health.router,
        runtime_config.router,
        auth.router,
        credits.router,
        tasks.router,
        generation.router,
        uploads.router,
        material_assets.router,
        material_center.router,
        workflows.router,
        admin.router,
    ):
        app.include_router(router)


def _register_static_content(app: FastAPI) -> None:
    storage_dir = Path(settings.storage_root)
    if storage_dir.is_dir():
        app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")

    web_static = Path("static/web")
    if web_static.is_dir():
        app.mount("/", StaticFiles(directory=str(web_static), html=True), name="web")

    if Path("static/web/index.html").is_file():
        app.add_middleware(SpaFallbackMiddleware)


def create_app(*, start_worker: bool = True) -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(level=logging.INFO, json_format=settings.log_json_format)
    validate_runtime_settings(settings)
    _prepare_runtime_directories()

    container = AppContainer(settings)
    app = FastAPI(
        title="JianDou API",
        version="0.2.0rc1",
        docs_url="/docs" if settings.app_env == "dev" else None,
        lifespan=_create_lifespan(container, start_worker=start_worker),
    )

    _register_exception_handlers(app)
    container.bind_app_state(app)
    _register_middleware(app)
    _register_routers(app)
    _register_static_content(app)
    return app
