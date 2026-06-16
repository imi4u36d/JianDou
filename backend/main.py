"""
FastAPI application factory.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="JianDou API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env == "dev" else None,
    )

    # Create data directories
    Path("./data").mkdir(parents=True, exist_ok=True)
    for d in [settings.uploads_dir, settings.generation_runs_dir, "thumbs"]:
        Path(settings.storage_root, d).mkdir(parents=True, exist_ok=True)

    # Register routers
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

    # Redirect /admin to /admin/
    @app.get("/admin")
    async def admin_redirect():
        return RedirectResponse(url="/admin/", status_code=301)

    # Mount static files
    admin_static = Path("static/admin")
    if admin_static.is_dir():
        app.mount("/admin", StaticFiles(directory=str(admin_static), html=True), name="admin")
    web_static = Path("static/web")
    if web_static.is_dir():
        app.mount("/", StaticFiles(directory=str(web_static), html=True), name="web")

    # SPA fallback: serve index.html for any non-API, non-static path
    _web_index = Path("static/web/index.html")
    if _web_index.is_file():
        from fastapi.responses import FileResponse

        @app.exception_handler(404)
        async def spa_fallback(request: Request, exc):
            path = request.url.path
            if path.startswith("/api/") or path.startswith("/admin/") or path.startswith("/docs") or path.startswith("/openapi"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(str(_web_index))

    return app


app = create_app()
