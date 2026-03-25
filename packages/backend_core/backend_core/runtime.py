from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings, load_settings
from .db import build_sqlite_url, create_sqlalchemy_engine, init_database, build_session_factory
from .planner import build_planner
from .storage import MediaStorage
from .worker import TaskWorker
from .service import TaskService


@dataclass
class BackendRuntime:
    settings: Settings
    database_url: str
    engine: object
    session_factory: object
    storage: MediaStorage
    service: TaskService
    worker: TaskWorker

    def describe(self) -> dict[str, object]:
        return {
            "name": self.settings.app.name,
            "env": self.settings.app.env,
            "execution_mode": self.settings.app.execution_mode,
            "database_url": self.database_url,
            "model_provider": self.settings.model.provider,
            "storage_root": str(self.settings.storage_root),
        }


def _build_engine(settings: Settings):
    preferred_url = settings.database.url
    engine = create_sqlalchemy_engine(preferred_url, echo=settings.database.echo)
    try:
        with engine.connect():
            pass
        return engine, preferred_url
    except Exception:
        fallback_path = settings.temp_root / "ai_cut.db"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_url = build_sqlite_url(fallback_path)
        fallback_engine = create_sqlalchemy_engine(fallback_url, echo=settings.database.echo)
        with fallback_engine.connect():
            pass
        return fallback_engine, fallback_url


def _build_redis_queue(settings: Settings):
    try:
        from .worker import RedisJobQueue
    except Exception:
        return None
    try:
        return RedisJobQueue(settings.redis.url)
    except Exception:
        return None


def build_runtime(config_path: str | Path | None = None) -> BackendRuntime:
    settings = load_settings(config_path)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.uploads_root.mkdir(parents=True, exist_ok=True)
    settings.outputs_root.mkdir(parents=True, exist_ok=True)
    settings.temp_root.mkdir(parents=True, exist_ok=True)

    engine, database_url = _build_engine(settings)
    init_database(engine)
    session_factory = build_session_factory(engine)
    storage = MediaStorage(settings)
    planner = build_planner(settings)
    service = TaskService(
        settings=settings,
        session_factory=session_factory,
        storage=storage,
        planner=planner,
    )
    queue = _build_redis_queue(settings)
    worker = TaskWorker(service=service, job_queue=queue, poll_interval_seconds=2)
    service.set_worker(worker)
    return BackendRuntime(
        settings=settings,
        database_url=database_url,
        engine=engine,
        session_factory=session_factory,
        storage=storage,
        service=service,
        worker=worker,
    )
