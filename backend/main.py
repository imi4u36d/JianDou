"""
FastAPI application factory.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_diagnosis_service import TaskQueueCoordinator
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_query_service import TaskQueryService
from backend.services.task_command_service import TaskCommandService
from backend.services.task_application_service import TaskApplicationServiceImpl
from backend.services.model_config_service import (
    AdminModelConfigService,
    ModelRuntimePropertiesResolver,
    SqlAlchemyUserModelCredentialRepository,
    UserModelConfigService,
)
from backend.services.structured_application_logger import StructuredApplicationLogger
from backend.services.generation_service import DefaultGenerationApplicationService
from backend.services.task_worker_runner import TaskWorkerOpsConfig, TaskWorkerRunner
from backend.services.task_worker_service import TaskWorkerPipelineHandler


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

    # Initialize application services
    task_repo = TaskRepository()
    exec_coord = TaskExecutionCoordinator()
    query_service = TaskQueryService(task_repo, exec_coord)
    command_service = TaskCommandService(task_repo, exec_coord)
    task_app_service = TaskApplicationServiceImpl(query_service, command_service)
    credential_repo = SqlAlchemyUserModelCredentialRepository(settings.database_url)
    model_resolver = ModelRuntimePropertiesResolver(
        config_dir="./config",
        credential_provider=credential_repo,
    )
    admin_config_service = AdminModelConfigService(model_resolver)
    user_model_config_service = UserModelConfigService(model_resolver, credential_repo)

    app.state.task_application_service = task_app_service
    app.state.admin_model_config_service = admin_config_service
    app.state.user_model_config_service = user_model_config_service
    app.state.model_resolver = model_resolver
    app.state.structured_logger = StructuredApplicationLogger
    app.state.generation_application_service = DefaultGenerationApplicationService(
        config_resolver=model_resolver,
    )
    task_queue = TaskQueueCoordinator(task_repo)
    pipeline_handler = TaskWorkerPipelineHandler(
        task_repository=task_repo,
        task_queue_port=task_queue,
        execution_coordinator=exec_coord,
        generation_application_service=app.state.generation_application_service,
    )
    worker_runner = TaskWorkerRunner(
        task_queue_port=task_queue,
        execution_coordinator=exec_coord,
        pipeline_handler=pipeline_handler,
        execution_mode=settings.execution_mode,
        ops_config=TaskWorkerOpsConfig(
            worker_concurrency=settings.worker_concurrency,
            worker_poll_initial_delay_ms=500,
            worker_poll_interval_ms=settings.worker_poll_interval_ms,
            worker_maintenance_initial_delay_ms=1_000,
            worker_maintenance_interval_ms=10_000,
            worker_stale_timeout_seconds=settings.worker_stale_timeout_seconds,
        ),
    )
    app.state.task_worker_runner = worker_runner
    app.state.task_repository = task_repo

    @app.on_event("startup")
    async def start_task_worker() -> None:
        await worker_runner.start()

    @app.on_event("shutdown")
    async def stop_task_worker() -> None:
        await worker_runner.stop()
        await task_repo.close()

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
    # Mount static files
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
            if path.startswith("/api/") or path.startswith("/docs") or path.startswith("/openapi"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(str(_web_index))

    return app


app = create_app()
