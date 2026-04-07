from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import tomllib


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_config_path() -> Path:
    return repo_root() / "config" / "app.toml"


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


@dataclass(frozen=True)
class AppSettings:
    name: str
    env: str
    api_host: str
    api_port: int
    web_origin: str
    execution_mode: str


@dataclass(frozen=True)
class DatabaseSettings:
    url: str
    echo: bool


@dataclass(frozen=True)
class RedisSettings:
    url: str


@dataclass(frozen=True)
class StorageSettings:
    root_dir: str
    uploads_dir: str
    outputs_dir: str
    temp_dir: str
    public_base_url: str


@dataclass(frozen=True)
class ModelSettings:
    provider: str
    model_name: str
    fallback_model_name: str | None
    vision_model_name: str | None
    vision_fallback_model_name: str | None
    endpoint: str
    video_endpoint: str
    video_task_endpoint: str
    video_model_name: str
    video_prompt_extend: bool
    video_poll_interval_seconds: int
    video_poll_timeout_seconds: int
    video_generation_endpoint: str
    video_generation_default_model: str
    video_generation_poll_interval_seconds: int
    video_generation_max_wait_seconds: int
    api_key: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    vision_frame_count: int


@dataclass(frozen=True)
class PipelineSettings:
    default_aspect_ratio: str
    max_output_count: int
    max_source_minutes: int
    default_intro_template: str
    default_outro_template: str


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    config_path: Path
    app: AppSettings
    database: DatabaseSettings
    redis: RedisSettings
    storage: StorageSettings
    model: ModelSettings
    pipeline: PipelineSettings

    @property
    def storage_root(self) -> Path:
        return _resolve_path(self.repo_root, self.storage.root_dir)

    @property
    def uploads_root(self) -> Path:
        return _resolve_path(self.repo_root, self.storage.uploads_dir)

    @property
    def outputs_root(self) -> Path:
        return _resolve_path(self.repo_root, self.storage.outputs_dir)

    @property
    def temp_root(self) -> Path:
        return _resolve_path(self.repo_root, self.storage.temp_dir)

    @property
    def using_inline_execution(self) -> bool:
        return self.app.execution_mode.lower() == "inline"


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path) if config_path is not None else default_config_path()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    app = raw.get("app", {})
    database = raw.get("database", {})
    redis = raw.get("redis", {})
    storage = raw.get("storage", {})
    model = raw.get("model", {})
    pipeline = raw.get("pipeline", {})

    repo = repo_root()

    return Settings(
        repo_root=repo,
        config_path=path,
        app=AppSettings(
            name=_env("AI_CUT_APP_NAME", app.get("name", "AI Cut")) or "AI Cut",
            env=_env("AI_CUT_ENV", app.get("env", "local")) or "local",
            api_host=_env("AI_CUT_API_HOST", app.get("api_host", "0.0.0.0")) or "0.0.0.0",
            api_port=int(_env("AI_CUT_API_PORT", str(app.get("api_port", 8000))) or 8000),
            web_origin=_env("AI_CUT_WEB_ORIGIN", app.get("web_origin", "http://localhost:5173")) or "http://localhost:5173",
            execution_mode=_env("AI_CUT_EXECUTION_MODE", app.get("execution_mode", "inline")) or "inline",
        ),
        database=DatabaseSettings(
            url=_env("AI_CUT_DATABASE_URL", database.get("url", "sqlite:///storage/temp/ai_cut.db"))
            or "sqlite:///storage/temp/ai_cut.db",
            echo=_coerce_bool(_env("AI_CUT_DATABASE_ECHO", str(database.get("echo", False))), False),
        ),
        redis=RedisSettings(
            url=_env("AI_CUT_REDIS_URL", redis.get("url", "redis://127.0.0.1:6379/0"))
            or "redis://127.0.0.1:6379/0",
        ),
        storage=StorageSettings(
            root_dir=_env("AI_CUT_STORAGE_ROOT", storage.get("root_dir", "storage")) or "storage",
            uploads_dir=_env("AI_CUT_UPLOADS_DIR", storage.get("uploads_dir", "storage/uploads")) or "storage/uploads",
            outputs_dir=_env("AI_CUT_OUTPUTS_DIR", storage.get("outputs_dir", "storage/outputs")) or "storage/outputs",
            temp_dir=_env("AI_CUT_TEMP_DIR", storage.get("temp_dir", "storage/temp")) or "storage/temp",
            public_base_url=_env("AI_CUT_PUBLIC_BASE_URL", storage.get("public_base_url", "http://127.0.0.1:8000/storage"))
            or "http://127.0.0.1:8000/storage",
        ),
        model=ModelSettings(
            provider=_env("AI_CUT_MODEL_PROVIDER", model.get("provider", "qwen")) or "qwen",
            model_name=_env("AI_CUT_MODEL_NAME", model.get("model_name", "qwen-max-latest")) or "qwen-max-latest",
            fallback_model_name=_env("AI_CUT_MODEL_FALLBACK_NAME", model.get("fallback_model_name", "qwen-plus"))
            or "qwen-plus",
            vision_model_name=_env("AI_CUT_VISION_MODEL_NAME", model.get("vision_model_name", "qwen-vl-plus-latest"))
            or "qwen-vl-plus-latest",
            vision_fallback_model_name=_env(
                "AI_CUT_VISION_MODEL_FALLBACK_NAME",
                model.get("vision_fallback_model_name", "qwen3-vl-flash"),
            )
            or "qwen3-vl-flash",
            endpoint=_env("AI_CUT_MODEL_ENDPOINT", model.get("endpoint", "")) or "",
            video_endpoint=_env(
                "AI_CUT_VIDEO_ENDPOINT",
                model.get("video_endpoint")
                or model.get("video_generation_endpoint")
                or "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            )
            or "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            video_task_endpoint=_env(
                "AI_CUT_VIDEO_TASK_ENDPOINT",
                model.get("video_task_endpoint", "https://dashscope.aliyuncs.com/api/v1/tasks"),
            )
            or "https://dashscope.aliyuncs.com/api/v1/tasks",
            video_model_name=_env(
                "AI_CUT_VIDEO_MODEL_NAME",
                model.get("video_model_name")
                or model.get("video_generation_default_model")
                or "wan2.6-i2v",
            )
            or "wan2.6-i2v",
            video_prompt_extend=_coerce_bool(
                _env("AI_CUT_VIDEO_PROMPT_EXTEND", str(model.get("video_prompt_extend", True))),
                True,
            ),
            video_poll_interval_seconds=int(
                _env(
                    "AI_CUT_VIDEO_POLL_INTERVAL",
                    str(
                        model.get("video_poll_interval_seconds")
                        or model.get("video_generation_poll_interval_seconds")
                        or 10
                    ),
                )
                or 10
            ),
            video_poll_timeout_seconds=int(
                _env(
                    "AI_CUT_VIDEO_POLL_TIMEOUT",
                    str(
                        model.get("video_poll_timeout_seconds")
                        or model.get("video_generation_max_wait_seconds")
                        or 900
                    ),
                )
                or 900
            ),
            video_generation_endpoint=_env(
                "AI_CUT_VIDEO_GENERATION_ENDPOINT",
                model.get("video_generation_endpoint", "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"),
            )
            or "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            video_generation_default_model=_env(
                "AI_CUT_VIDEO_GENERATION_DEFAULT_MODEL",
                model.get("video_generation_default_model", "wan2.6-i2v"),
            )
            or "wan2.6-i2v",
            video_generation_poll_interval_seconds=int(
                _env(
                    "AI_CUT_VIDEO_GENERATION_POLL_INTERVAL",
                    str(model.get("video_generation_poll_interval_seconds", 10)),
                )
                or 10
            ),
            video_generation_max_wait_seconds=int(
                _env(
                    "AI_CUT_VIDEO_GENERATION_MAX_WAIT",
                    str(model.get("video_generation_max_wait_seconds", 900)),
                )
                or 900
            ),
            api_key=_env("AI_CUT_MODEL_API_KEY", model.get("api_key", "")) or "",
            timeout_seconds=int(_env("AI_CUT_MODEL_TIMEOUT", str(model.get("timeout_seconds", 45))) or 45),
            temperature=float(_env("AI_CUT_MODEL_TEMPERATURE", str(model.get("temperature", 0.15))) or 0.15),
            max_tokens=int(_env("AI_CUT_MODEL_MAX_TOKENS", str(model.get("max_tokens", 2000))) or 2000),
            vision_frame_count=int(_env("AI_CUT_VISION_FRAME_COUNT", str(model.get("vision_frame_count", 6))) or 6),
        ),
        pipeline=PipelineSettings(
            default_aspect_ratio=_env("AI_CUT_DEFAULT_ASPECT_RATIO", pipeline.get("default_aspect_ratio", "9:16"))
            or "9:16",
            max_output_count=int(_env("AI_CUT_MAX_OUTPUT_COUNT", str(pipeline.get("max_output_count", 10))) or 10),
            max_source_minutes=int(_env("AI_CUT_MAX_SOURCE_MINUTES", str(pipeline.get("max_source_minutes", 120))) or 120),
            default_intro_template=_env("AI_CUT_DEFAULT_INTRO_TEMPLATE", pipeline.get("default_intro_template", "hook"))
            or "hook",
            default_outro_template=_env("AI_CUT_DEFAULT_OUTRO_TEMPLATE", pipeline.get("default_outro_template", "brand"))
            or "brand",
        ),
    )
