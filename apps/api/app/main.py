from __future__ import annotations

from pathlib import Path
import sys


def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    packages_root = repo_root / "packages"
    package_projects: list[Path] = []
    if packages_root.exists():
        package_projects = sorted(
            [
                child
                for child in packages_root.iterdir()
                if child.is_dir() and (child / "pyproject.toml").exists()
            ]
        )

    for candidate in [repo_root, *package_projects, packages_root]:
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_path()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend_core.runtime import build_runtime
from .routers.admin import router as admin_router
from .routers.generation_v2 import router as generation_v2_router
from .routers.health import router as health_router
from .routers.tasks import router as tasks_router
from .routers.uploads import router as uploads_router


def _build_allowed_origins(web_origin: str) -> list[str]:
    origins: list[str] = []
    for raw_origin in web_origin.split(","):
        origin = raw_origin.strip()
        if origin and origin not in origins:
            origins.append(origin)

    aliases: list[str] = []
    for origin in origins:
        if "127.0.0.1" in origin:
            aliases.append(origin.replace("127.0.0.1", "localhost"))
        if "localhost" in origin:
            aliases.append(origin.replace("localhost", "127.0.0.1"))

    for alias in aliases:
        if alias not in origins:
            origins.append(alias)

    return origins


runtime = build_runtime()

app = FastAPI(title=runtime.settings.app.name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_allowed_origins(runtime.settings.app.web_origin),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/storage", StaticFiles(directory=str(runtime.settings.storage_root)), name="storage")
app.state.runtime = runtime


@app.on_event("startup")
def _startup() -> None:
    app.state.runtime = runtime


app.include_router(health_router, prefix="/api/v2")
app.include_router(admin_router, prefix="/api/v2")
app.include_router(generation_v2_router)
app.include_router(uploads_router, prefix="/api/v2")
app.include_router(tasks_router, prefix="/api/v2")
