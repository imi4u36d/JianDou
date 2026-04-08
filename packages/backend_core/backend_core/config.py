from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
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
    """应用名称、环境和服务监听相关配置。"""

    name: str
    env: str
    api_host: str
    api_port: int
    web_origin: str
    execution_mode: str


@dataclass(frozen=True)
class DatabaseSettings:
    """主关系型数据库连接配置。"""

    url: str
    echo: bool


@dataclass(frozen=True)
class RedisSettings:
    """后端服务使用的 Redis 连接配置。"""

    url: str


@dataclass(frozen=True)
class StorageSettings:
    """存储资源对应的本地路径和公开访问地址配置。"""

    root_dir: str
    uploads_dir: str
    outputs_dir: str
    temp_dir: str
    public_base_url: str


@dataclass(frozen=True)
class ModelSettings:
    """模型访问所需的提供方、地址、凭证和超时配置。"""

    provider: str
    model_name: str
    image_model_name: str
    fallback_model_name: str | None
    text_analysis_provider: str
    text_analysis_model_name: str
    text_analysis_fallback_model_name: str | None
    text_analysis_endpoint: str
    text_analysis_api_key: str
    text_analysis_models: str
    vision_model_name: str | None
    vision_fallback_model_name: str | None
    endpoint: str
    video_endpoint: str
    video_task_endpoint: str
    video_model_name: str
    video_models: str
    video_prompt_extend: bool
    video_poll_interval_seconds: int
    video_poll_timeout_seconds: int
    video_generation_endpoint: str
    video_generation_default_model: str
    video_generation_poll_interval_seconds: int
    video_generation_max_wait_seconds: int
    seeddance_video_endpoint: str
    seeddance_video_task_endpoint: str
    seeddance_api_key: str
    seeddance_poll_interval_seconds: int
    seeddance_poll_timeout_seconds: int
    aliyun_billing_access_key_id: str
    aliyun_billing_access_key_secret: str
    volcengine_billing_access_key_id: str
    volcengine_billing_access_key_secret: str
    video_model_usage_quota: str
    api_key: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    vision_frame_count: int


@dataclass(frozen=True)
class RemoteModelTarget:
    """应用提供方与模型回退逻辑后得到的最终远端模型目标。"""

    provider: str
    family: str
    mode: str
    model_name: str
    fallback_model_name: str | None
    endpoint: str
    api_key: str


@dataclass(frozen=True)
class PipelineSettings:
    """输出规格和模板选择相关的产品默认配置。"""

    default_aspect_ratio: str
    max_output_count: int
    max_source_minutes: int
    default_intro_template: str
    default_outro_template: str


@dataclass(frozen=True)
class Settings:
    """由 TOML 和环境变量共同解析后的完整应用配置。"""

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


def _normalize_model_name(value: str | None) -> str:
    return (value or "").strip()


def _normalize_provider_name(value: str | None) -> str:
    return _normalize_model_name(value).lower()


def _looks_like_chatgpt_provider(value: str | None) -> bool:
    normalized = _normalize_provider_name(value)
    return normalized in {"chatgpt", "openai", "gpt"}


def _looks_like_chatgpt_model(value: str | None) -> bool:
    normalized = _normalize_model_name(value).lower()
    if not normalized:
        return False
    return normalized.startswith(("gpt", "chatgpt", "o1", "o3", "o4"))


def _looks_like_qwen_model(value: str | None) -> bool:
    normalized = _normalize_model_name(value).lower()
    if not normalized:
        return False
    return normalized.startswith(("qwen", "qwq"))


def default_text_analysis_model_name(model: ModelSettings) -> str:
    explicit = _normalize_model_name(model.text_analysis_model_name)
    if explicit:
        return explicit
    fallback = _normalize_model_name(model.model_name)
    if fallback:
        return fallback
    return "gpt-5.4"


def resolve_text_analysis_target(model: ModelSettings, requested_model: str | None = None) -> RemoteModelTarget:
    selected_model = _normalize_model_name(requested_model) or default_text_analysis_model_name(model)
    configured_provider = _normalize_provider_name(model.text_analysis_provider)
    provider_hint = configured_provider
    if requested_model and _looks_like_qwen_model(selected_model):
        provider_hint = "qwen"
    elif requested_model and _looks_like_chatgpt_model(selected_model):
        provider_hint = "chatgpt"

    use_chatgpt_slot = _looks_like_chatgpt_provider(provider_hint) or (
        not provider_hint and _looks_like_chatgpt_model(selected_model)
    )
    if use_chatgpt_slot:
        endpoint = _normalize_model_name(model.text_analysis_endpoint) or "https://api.openai.com/v1/chat/completions"
        api_key = _normalize_model_name(model.text_analysis_api_key)
        if not api_key and _looks_like_chatgpt_provider(model.provider):
            api_key = _normalize_model_name(model.api_key)
        if endpoint and api_key:
            return RemoteModelTarget(
                provider=_normalize_model_name(model.text_analysis_provider) or "chatgpt",
                family="chatgpt",
                mode="chatgpt_key",
                model_name=selected_model,
                fallback_model_name=_normalize_model_name(model.text_analysis_fallback_model_name) or None,
                endpoint=endpoint,
                api_key=api_key,
            )
        if requested_model and _looks_like_chatgpt_model(selected_model):
            return RemoteModelTarget(
                provider=_normalize_model_name(model.text_analysis_provider) or "chatgpt",
                family="chatgpt",
                mode="chatgpt_key",
                model_name=selected_model,
                fallback_model_name=_normalize_model_name(model.text_analysis_fallback_model_name) or None,
                endpoint=endpoint,
                api_key=api_key,
            )
        fallback_model = (
            _normalize_model_name(model.text_analysis_fallback_model_name)
            or _normalize_model_name(model.model_name)
            or "qwen3.6-plus"
        )
        provider = _normalize_model_name(model.provider) or "qwen"
        family = "qwen" if _looks_like_qwen_model(fallback_model) or provider.lower().startswith("qwen") else "compatible"
        return RemoteModelTarget(
            provider=provider,
            family=family,
            mode="compatible_key",
            model_name=fallback_model,
            fallback_model_name=_normalize_model_name(model.fallback_model_name) or None,
            endpoint=_normalize_model_name(model.endpoint),
            api_key=_normalize_model_name(model.api_key),
        )
    provider = _normalize_model_name(model.provider) or "qwen"
    family = "qwen" if _looks_like_qwen_model(selected_model) or provider.lower().startswith("qwen") else "compatible"
    return RemoteModelTarget(
        provider=provider,
        family=family,
        mode="compatible_key",
        model_name=selected_model,
        fallback_model_name=_normalize_model_name(model.fallback_model_name) or None,
        endpoint=_normalize_model_name(model.endpoint) or _normalize_model_name(model.text_analysis_endpoint),
        api_key=_normalize_model_name(model.api_key) or _normalize_model_name(model.text_analysis_api_key),
    )


def text_analysis_model_options(model: ModelSettings) -> list[dict[str, object]]:
    default_model = default_text_analysis_model_name(model)
    options: list[dict[str, object]] = []
    seen: set[str] = set()

    predefined = [
        (
            _normalize_model_name(model.text_analysis_model_name) or "gpt-5.4",
            "GPT-5.4",
            _normalize_model_name(model.text_analysis_provider) or "chatgpt",
            "gpt",
            "ChatGPT / OpenAI key 模式，适合人物、对白、语境和剧情理解。",
        ),
        (
            _normalize_model_name(model.model_name) or "qwen3.6-plus",
            "Qwen 3.6 Plus",
            _normalize_model_name(model.provider) or "qwen",
            "qwen",
            "兼容当前阿里百炼 Key 模式的文本分析模型。",
        ),
    ]

    for value, label, provider, family, description in predefined:
        normalized = _normalize_model_name(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        options.append(
            {
                "value": normalized,
                "label": label,
                "description": description,
                "provider": provider,
                "family": family,
                "isDefault": normalized == default_model,
            }
        )

    raw_catalog = _normalize_model_name(model.text_analysis_models)
    if raw_catalog:
        try:
            parsed = json.loads(raw_catalog)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    normalized = _normalize_model_name(
                        str(item.get("value") or item.get("model") or item.get("name") or item.get("label") or "")
                    )
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    options.append(
                        {
                            "value": normalized,
                            "label": _normalize_model_name(str(item.get("label") or item.get("name") or normalized))
                            or normalized,
                            "description": _normalize_model_name(str(item.get("description") or "")) or None,
                            "provider": _normalize_model_name(str(item.get("provider") or model.text_analysis_provider)) or None,
                            "family": _normalize_model_name(str(item.get("family") or "")) or None,
                            "isDefault": normalized == default_model,
                        }
                    )
                elif isinstance(item, str):
                    normalized = _normalize_model_name(item)
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    target = resolve_text_analysis_target(model, normalized)
                    options.append(
                        {
                            "value": normalized,
                            "label": normalized,
                            "description": "文本分析模型（自定义配置）。",
                            "provider": target.provider,
                            "family": target.family,
                            "isDefault": normalized == default_model,
                        }
                    )

    if default_model not in seen:
        target = resolve_text_analysis_target(model, default_model)
        options.insert(
            0,
            {
                "value": default_model,
                "label": default_model,
                "description": "当前默认文本分析模型。",
                "provider": target.provider,
                "family": target.family,
                "isDefault": True,
            }
        )

    return options


def load_settings(config_path: str | Path | None = None) -> Settings:
    """加载 TOML 配置，并允许环境变量覆盖单个字段。"""

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
            model_name=_env("AI_CUT_MODEL_NAME", model.get("model_name", "qwen3.6-plus")) or "qwen3.6-plus",
            image_model_name=_env(
                "AI_CUT_IMAGE_MODEL_NAME",
                model.get("image_model_name", "Doubao-Seedream-5.0-lite"),
            )
            or "Doubao-Seedream-5.0-lite",
            fallback_model_name=_env("AI_CUT_MODEL_FALLBACK_NAME", model.get("fallback_model_name", "qwen-plus"))
            or "qwen-plus",
            text_analysis_provider=_env(
                "AI_CUT_TEXT_ANALYSIS_PROVIDER",
                model.get("text_analysis_provider", "chatgpt"),
            )
            or "chatgpt",
            text_analysis_model_name=_env(
                "AI_CUT_TEXT_ANALYSIS_MODEL_NAME",
                model.get("text_analysis_model_name", "gpt-5.4"),
            )
            or "gpt-5.4",
            text_analysis_fallback_model_name=_env(
                "AI_CUT_TEXT_ANALYSIS_FALLBACK_MODEL_NAME",
                model.get("text_analysis_fallback_model_name", model.get("model_name", "qwen3.6-plus")),
            )
            or model.get("model_name", "qwen3.6-plus"),
            text_analysis_endpoint=_env(
                "AI_CUT_TEXT_ANALYSIS_ENDPOINT",
                model.get("text_analysis_endpoint", "https://api.openai.com/v1/chat/completions"),
            )
            or "https://api.openai.com/v1/chat/completions",
            text_analysis_api_key=_env(
                "AI_CUT_TEXT_ANALYSIS_API_KEY",
                model.get("text_analysis_api_key", ""),
            )
            or "",
            text_analysis_models=_env(
                "AI_CUT_TEXT_ANALYSIS_MODELS",
                model.get("text_analysis_models", ""),
            )
            or "",
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
            video_models=_env(
                "AI_CUT_VIDEO_MODELS",
                model.get("video_models", ""),
            )
            or "",
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
            seeddance_video_endpoint=_env(
                "AI_CUT_SEEDDANCE_VIDEO_ENDPOINT",
                _env(
                    "AI_CUT_JIMENG_VIDEO_ENDPOINT",
                    model.get("seeddance_video_endpoint")
                    or model.get("jimeng_video_endpoint")
                    or "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
                ),
            )
            or "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
            seeddance_video_task_endpoint=_env(
                "AI_CUT_SEEDDANCE_VIDEO_TASK_ENDPOINT",
                _env(
                    "AI_CUT_JIMENG_VIDEO_TASK_ENDPOINT",
                    model.get("seeddance_video_task_endpoint")
                    or model.get("jimeng_video_task_endpoint")
                    or "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
                ),
            )
            or "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
            seeddance_api_key=_env(
                "AI_CUT_SEEDDANCE_API_KEY",
                _env(
                    "AI_CUT_JIMENG_API_KEY",
                    model.get("seeddance_api_key")
                    or model.get("jimeng_api_key")
                    or "",
                ),
            )
            or "",
            seeddance_poll_interval_seconds=int(
                _env(
                    "AI_CUT_SEEDDANCE_POLL_INTERVAL",
                    _env(
                        "AI_CUT_JIMENG_POLL_INTERVAL",
                        str(
                            model.get("seeddance_poll_interval_seconds")
                            or model.get("jimeng_poll_interval_seconds")
                            or 8
                        ),
                    ),
                )
                or 8
            ),
            seeddance_poll_timeout_seconds=int(
                _env(
                    "AI_CUT_SEEDDANCE_POLL_TIMEOUT",
                    _env(
                        "AI_CUT_JIMENG_POLL_TIMEOUT",
                        str(
                            model.get("seeddance_poll_timeout_seconds")
                            or model.get("jimeng_poll_timeout_seconds")
                            or 600
                        ),
                    ),
                )
                or 600
            ),
            aliyun_billing_access_key_id=_env(
                "AI_CUT_ALIYUN_BILLING_ACCESS_KEY_ID",
                model.get("aliyun_billing_access_key_id", ""),
            )
            or "",
            aliyun_billing_access_key_secret=_env(
                "AI_CUT_ALIYUN_BILLING_ACCESS_KEY_SECRET",
                model.get("aliyun_billing_access_key_secret", ""),
            )
            or "",
            volcengine_billing_access_key_id=_env(
                "AI_CUT_VOLCENGINE_BILLING_ACCESS_KEY_ID",
                model.get("volcengine_billing_access_key_id", ""),
            )
            or "",
            volcengine_billing_access_key_secret=_env(
                "AI_CUT_VOLCENGINE_BILLING_ACCESS_KEY_SECRET",
                model.get("volcengine_billing_access_key_secret", ""),
            )
            or "",
            video_model_usage_quota=_env(
                "AI_CUT_VIDEO_MODEL_USAGE_QUOTA",
                model.get("video_model_usage_quota", ""),
            )
            or "",
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
