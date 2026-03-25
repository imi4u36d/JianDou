from __future__ import annotations

from pathlib import Path
import sys


def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    packages_root = repo_root / "packages"
    for candidate in (repo_root, packages_root):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_path()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend_core.runtime import build_runtime
from .routers.health import router as health_router
from .routers.tasks import router as tasks_router
from .routers.uploads import router as uploads_router


runtime = build_runtime()

app = FastAPI(title=runtime.settings.app.name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[runtime.settings.app.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/storage", StaticFiles(directory=str(runtime.settings.storage_root)), name="storage")
app.state.runtime = runtime


@app.on_event("startup")
def _startup() -> None:
    app.state.runtime = runtime


app.include_router(health_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
