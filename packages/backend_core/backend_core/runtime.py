from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

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
        endpoint = self.settings.model.endpoint.strip()
        endpoint_host = ""
        if endpoint:
            try:
                endpoint_host = urlparse(endpoint).netloc or endpoint
            except Exception:
                endpoint_host = endpoint

        model_ready = bool(
            self.settings.model.provider
            and self.settings.model.model_name
            and endpoint
            and self.settings.model.api_key
        )

        config_errors: list[str] = []
        if not self.settings.model.provider:
            config_errors.append("missing provider")
        if not self.settings.model.model_name:
            config_errors.append("missing model_name")
        if not endpoint:
            config_errors.append("missing endpoint")
        if not self.settings.model.api_key:
            config_errors.append("missing api_key")

        return {
            "name": self.settings.app.name,
            "env": self.settings.app.env,
            "execution_mode": self.settings.app.execution_mode,
            "database_url": self.database_url,
            "model_provider": self.settings.model.provider,
            "storage_root": str(self.settings.storage_root),
            "model": {
                "provider": self.settings.model.provider,
                "primary_model": self.settings.model.model_name,
                "fallback_model": self.settings.model.fallback_model_name,
                "vision_model": self.settings.model.vision_model_name,
                "vision_fallback_model": self.settings.model.vision_fallback_model_name,
                "endpoint_host": endpoint_host,
                "api_key_present": bool(self.settings.model.api_key),
                "ready": model_ready,
                "temperature": self.settings.model.temperature,
                "max_tokens": self.settings.model.max_tokens,
                "config_errors": config_errors,
            },
            "planning_capabilities": {
                "editing_mode_split": True,
                "drama_planning": True,
                "mixcut_storyboard_planning": True,
                "timed_transcript_supported": True,
                "transcript_semantic_planning": True,
                "visual_content_analysis": bool(self.settings.model.vision_model_name),
                "visual_event_reasoning": bool(self.settings.model.vision_model_name),
                "subtitle_visual_fusion": True,
                "audio_peak_signal": True,
                "scene_boundary_signal": True,
                "fusion_timeline_planning": bool(self.settings.model.model_name),
                "fallback_heuristic_enabled": True,
            },
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
