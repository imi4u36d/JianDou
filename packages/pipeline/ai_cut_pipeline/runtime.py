from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from ai_cut_ai.providers import ModelRouter
from ai_cut_shared.config import Settings, load_settings
from ai_cut_db.db import create_sqlalchemy_engine, init_database, build_session_factory
from ai_cut_ai.planner import build_planner
from ai_cut_storage.storage import MediaStorage
from ai_cut_pipeline.service import TaskService
from ai_cut_pipeline.worker import TaskWorker


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
        router = ModelRouter(self.settings)
        text_model = router.resolve(capability="text_analysis", kind="text")
        endpoint = text_model.base_url.strip()
        endpoint_host = ""
        if endpoint:
            try:
                endpoint_host = urlparse(endpoint).netloc or endpoint
            except Exception:
                endpoint_host = endpoint

        model_ready = bool(
            text_model.provider_name
            and text_model.model_name
            and endpoint
            and text_model.api_key
        )

        config_errors: list[str] = []
        if not text_model.provider_name:
            config_errors.append("missing provider")
        if not text_model.model_name:
            config_errors.append("missing model_name")
        if not endpoint:
            config_errors.append("missing endpoint")
        if not text_model.api_key:
            config_errors.append("missing api_key")

        return {
            "name": self.settings.app.name,
            "env": self.settings.app.env,
            "execution_mode": self.settings.app.execution_mode,
            "database_url": self.database_url,
            "model_provider": text_model.provider_name,
            "storage_root": str(self.settings.storage_root),
            "model": {
                "provider": text_model.provider_name,
                "primary_model": text_model.model_name,
                "fallback_model": text_model.fallback_model,
                "text_analysis_provider": text_model.provider_name,
                "text_analysis_model": text_model.model_name,
                "vision_model": self.settings.model.defaults.vision_analysis,
                "endpoint_host": endpoint_host,
                "api_key_present": bool(text_model.api_key),
                "ready": model_ready,
                "temperature": self.settings.model.temperature,
                "max_tokens": self.settings.model.max_tokens,
                "config_errors": config_errors,
            },
            "planning_capabilities": {
                "drama_planning": True,
                "timed_transcript_supported": True,
                "transcript_semantic_planning": True,
                "visual_content_analysis": bool(self.settings.model.defaults.vision_analysis),
                "visual_event_reasoning": bool(self.settings.model.defaults.vision_analysis),
                "subtitle_visual_fusion": True,
                "audio_peak_signal": True,
                "scene_boundary_signal": True,
                "fusion_timeline_planning": bool(text_model.model_name),
                "fallback_heuristic_enabled": False,
            },
        }


def _build_engine(settings: Settings):
    preferred_url = settings.database.url
    engine = create_sqlalchemy_engine(preferred_url, echo=settings.database.echo)
    with engine.connect():
        pass
    return engine, preferred_url


def _build_redis_queue(settings: Settings):
    from ai_cut_pipeline.worker import RedisJobQueue

    return RedisJobQueue(settings.redis.url)


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
