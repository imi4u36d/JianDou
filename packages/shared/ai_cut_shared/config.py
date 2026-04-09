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


def default_prompt_config_path() -> Path:
    return repo_root() / "config" / "prompts"


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _required_text(value: Any, *, field: str) -> str:
    normalized = _strip_or_none(value)
    if normalized is None:
        raise ValueError(f"missing required config field: {field}")
    return normalized


def _optional_text(value: Any) -> str | None:
    return _strip_or_none(value)


def _required_int(value: Any, *, field: str) -> int:
    normalized = _required_text(value, field=field)
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid integer for config field: {field}") from exc


def _required_float(value: Any, *, field: str) -> float:
    normalized = _required_text(value, field=field)
    try:
        return float(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid float for config field: {field}") from exc


def _required_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = _required_text(value, field=field).lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean for config field: {field}")


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
class PromptSettings:
    """系统提示词配置，启动时从独立文件加载。"""

    connectivity_probe: str
    text_analysis_rewriter: str
    short_drama_script: str
    generation_json_only: str
    qwen_vl_prompt_rewriter: str
    planner_shot_analysis_json_only: str
    planner_fusion_json_only: str
    creative_prompt_generator_json_only: str


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
    prompts: PromptSettings

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
    if not explicit:
        raise ValueError("missing required config field: model.text_analysis_model_name")
    return explicit


def resolve_text_analysis_target(model: ModelSettings, requested_model: str | None = None) -> RemoteModelTarget:
    selected_model = _normalize_model_name(requested_model) or default_text_analysis_model_name(model)
    analysis_provider = _required_text(model.text_analysis_provider, field="model.text_analysis_provider")
    analysis_endpoint = _required_text(model.text_analysis_endpoint, field="model.text_analysis_endpoint")
    analysis_api_key = _required_text(model.text_analysis_api_key, field="model.text_analysis_api_key")
    compatible_provider = _required_text(model.provider, field="model.provider")
    compatible_endpoint = _required_text(model.endpoint, field="model.endpoint")
    compatible_api_key = _required_text(model.api_key, field="model.api_key")

    selected_lower = selected_model.lower()
    analysis_provider_lower = analysis_provider.lower()

    # Adapter routing: selected model family decides which credential set to use.
    # - ChatGPT family models use dedicated text_analysis_* config.
    # - Qwen/compatible models use main compatible provider config.
    if _looks_like_qwen_model(selected_lower):
        family = "qwen"
        mode = "compatible_key"
        provider = compatible_provider
        endpoint = compatible_endpoint
        api_key = compatible_api_key
    elif _looks_like_chatgpt_model(selected_lower):
        family = "chatgpt"
        mode = "chatgpt_key"
        provider = analysis_provider
        endpoint = analysis_endpoint
        api_key = analysis_api_key
    elif _looks_like_chatgpt_provider(analysis_provider_lower):
        family = "chatgpt"
        mode = "chatgpt_key"
        provider = analysis_provider
        endpoint = analysis_endpoint
        api_key = analysis_api_key
    elif analysis_provider_lower.startswith("qwen"):
        family = "qwen"
        mode = "compatible_key"
        provider = compatible_provider
        endpoint = compatible_endpoint
        api_key = compatible_api_key
    else:
        family = "compatible"
        mode = "compatible_key"
        provider = compatible_provider
        endpoint = compatible_endpoint
        api_key = compatible_api_key
    return RemoteModelTarget(
        provider=provider,
        family=family,
        mode=mode,
        model_name=selected_model,
        fallback_model_name=_normalize_model_name(model.fallback_model_name) or None,
        endpoint=endpoint,
        api_key=api_key,
    )


def text_analysis_model_options(model: ModelSettings) -> list[dict[str, object]]:
    default_model = default_text_analysis_model_name(model)
    options: list[dict[str, object]] = []
    seen: set[str] = set()

    default_target = resolve_text_analysis_target(model, default_model)
    predefined = [
        (
            default_model,
            default_model,
            default_target.provider,
            default_target.family,
            "文本分析默认模型（严格配置）。",
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
        except Exception as exc:
            raise ValueError("invalid JSON in model.text_analysis_models") from exc
        if not isinstance(parsed, list):
            raise ValueError("model.text_analysis_models must be a JSON list")
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


def _load_prompt_settings(prompt_config_path: Path) -> PromptSettings:
    sources: list[Path]
    if prompt_config_path.is_dir():
        sources = sorted([item for item in prompt_config_path.glob("*.toml") if item.is_file()])
        if not sources:
            raise ValueError(f"prompt config directory has no .toml files: {prompt_config_path}")
    else:
        sources = [prompt_config_path]

    prompt_section: dict[str, Any] = {}
    for source in sources:
        with source.open("rb") as handle:
            raw_prompt = tomllib.load(handle)
        source_section = raw_prompt.get("system_prompts", {})
        if not isinstance(source_section, dict):
            raise ValueError(f"invalid prompt config in {source}: [system_prompts] must be a table")
        for key, value in source_section.items():
            if key in prompt_section:
                raise ValueError(f"duplicate prompt key found: system_prompts.{key} ({source})")
            prompt_section[key] = value

    def _prompt_required(key: str) -> str:
        return _required_text(prompt_section.get(key), field=f"system_prompts.{key}")

    return PromptSettings(
        connectivity_probe=_prompt_required("connectivity_probe"),
        text_analysis_rewriter=_prompt_required("text_analysis_rewriter"),
        short_drama_script=_prompt_required("short_drama_script"),
        generation_json_only=_prompt_required("generation_json_only"),
        qwen_vl_prompt_rewriter=_prompt_required("qwen_vl_prompt_rewriter"),
        planner_shot_analysis_json_only=_prompt_required("planner_shot_analysis_json_only"),
        planner_fusion_json_only=_prompt_required("planner_fusion_json_only"),
        creative_prompt_generator_json_only=_prompt_required("creative_prompt_generator_json_only"),
    )


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
    prompt = raw.get("prompt", {})

    repo = repo_root()

    def _pick(section: dict[str, Any], key: str, env_name: str) -> Any:
        env_value = os.getenv(env_name)
        if env_value is not None and env_value != "":
            return env_value
        return section.get(key)

    def _pick_alias(section: dict[str, Any], keys: tuple[str, ...], env_names: tuple[str, ...]) -> Any:
        for env_name in env_names:
            env_value = os.getenv(env_name)
            if env_value is not None and env_value != "":
                return env_value
        for key in keys:
            value = section.get(key)
            if value is not None and value != "":
                return value
        return None

    prompt_path_value = _pick(prompt, "file", "AI_CUT_PROMPTS_PATH")
    prompt_config_path = (
        _resolve_path(repo, _required_text(prompt_path_value, field="prompt.file"))
        if prompt_path_value is not None and str(prompt_path_value).strip()
        else default_prompt_config_path()
    )
    prompts = _load_prompt_settings(prompt_config_path)

    return Settings(
        repo_root=repo,
        config_path=path,
        app=AppSettings(
            name=_required_text(_pick(app, "name", "AI_CUT_APP_NAME"), field="app.name"),
            env=_required_text(_pick(app, "env", "AI_CUT_ENV"), field="app.env"),
            api_host=_required_text(_pick(app, "api_host", "AI_CUT_API_HOST"), field="app.api_host"),
            api_port=_required_int(_pick(app, "api_port", "AI_CUT_API_PORT"), field="app.api_port"),
            web_origin=_required_text(_pick(app, "web_origin", "AI_CUT_WEB_ORIGIN"), field="app.web_origin"),
            execution_mode=_required_text(
                _pick(app, "execution_mode", "AI_CUT_EXECUTION_MODE"),
                field="app.execution_mode",
            ),
        ),
        database=DatabaseSettings(
            url=_required_text(_pick(database, "url", "AI_CUT_DATABASE_URL"), field="database.url"),
            echo=_required_bool(_pick(database, "echo", "AI_CUT_DATABASE_ECHO"), field="database.echo"),
        ),
        redis=RedisSettings(
            url=_required_text(_pick(redis, "url", "AI_CUT_REDIS_URL"), field="redis.url"),
        ),
        storage=StorageSettings(
            root_dir=_required_text(_pick(storage, "root_dir", "AI_CUT_STORAGE_ROOT"), field="storage.root_dir"),
            uploads_dir=_required_text(_pick(storage, "uploads_dir", "AI_CUT_UPLOADS_DIR"), field="storage.uploads_dir"),
            outputs_dir=_required_text(_pick(storage, "outputs_dir", "AI_CUT_OUTPUTS_DIR"), field="storage.outputs_dir"),
            temp_dir=_required_text(_pick(storage, "temp_dir", "AI_CUT_TEMP_DIR"), field="storage.temp_dir"),
            public_base_url=_required_text(
                _pick(storage, "public_base_url", "AI_CUT_PUBLIC_BASE_URL"),
                field="storage.public_base_url",
            ),
        ),
        model=ModelSettings(
            provider=_required_text(_pick(model, "provider", "AI_CUT_MODEL_PROVIDER"), field="model.provider"),
            model_name=_required_text(_pick(model, "model_name", "AI_CUT_MODEL_NAME"), field="model.model_name"),
            image_model_name=_required_text(
                _pick(model, "image_model_name", "AI_CUT_IMAGE_MODEL_NAME"),
                field="model.image_model_name",
            ),
            fallback_model_name=_optional_text(_pick(model, "fallback_model_name", "AI_CUT_MODEL_FALLBACK_NAME")),
            text_analysis_provider=_required_text(
                _pick(model, "text_analysis_provider", "AI_CUT_TEXT_ANALYSIS_PROVIDER"),
                field="model.text_analysis_provider",
            ),
            text_analysis_model_name=_required_text(
                _pick(model, "text_analysis_model_name", "AI_CUT_TEXT_ANALYSIS_MODEL_NAME"),
                field="model.text_analysis_model_name",
            ),
            text_analysis_fallback_model_name=_optional_text(
                _pick(model, "text_analysis_fallback_model_name", "AI_CUT_TEXT_ANALYSIS_FALLBACK_MODEL_NAME")
            ),
            text_analysis_endpoint=_required_text(
                _pick(model, "text_analysis_endpoint", "AI_CUT_TEXT_ANALYSIS_ENDPOINT"),
                field="model.text_analysis_endpoint",
            ),
            text_analysis_api_key=_required_text(
                _pick(model, "text_analysis_api_key", "AI_CUT_TEXT_ANALYSIS_API_KEY"),
                field="model.text_analysis_api_key",
            ),
            text_analysis_models=_required_text(
                _pick(model, "text_analysis_models", "AI_CUT_TEXT_ANALYSIS_MODELS"),
                field="model.text_analysis_models",
            ),
            vision_model_name=_optional_text(_pick(model, "vision_model_name", "AI_CUT_VISION_MODEL_NAME")),
            vision_fallback_model_name=_optional_text(
                _pick(model, "vision_fallback_model_name", "AI_CUT_VISION_MODEL_FALLBACK_NAME")
            ),
            endpoint=_required_text(_pick(model, "endpoint", "AI_CUT_MODEL_ENDPOINT"), field="model.endpoint"),
            video_endpoint=_required_text(
                _pick(model, "video_endpoint", "AI_CUT_VIDEO_ENDPOINT"),
                field="model.video_endpoint",
            ),
            video_task_endpoint=_required_text(
                _pick(model, "video_task_endpoint", "AI_CUT_VIDEO_TASK_ENDPOINT"),
                field="model.video_task_endpoint",
            ),
            video_model_name=_required_text(
                _pick(model, "video_model_name", "AI_CUT_VIDEO_MODEL_NAME"),
                field="model.video_model_name",
            ),
            video_models=_required_text(_pick(model, "video_models", "AI_CUT_VIDEO_MODELS"), field="model.video_models"),
            video_prompt_extend=_required_bool(
                _pick(model, "video_prompt_extend", "AI_CUT_VIDEO_PROMPT_EXTEND"),
                field="model.video_prompt_extend",
            ),
            video_poll_interval_seconds=_required_int(
                _pick(model, "video_poll_interval_seconds", "AI_CUT_VIDEO_POLL_INTERVAL"),
                field="model.video_poll_interval_seconds",
            ),
            video_poll_timeout_seconds=_required_int(
                _pick(model, "video_poll_timeout_seconds", "AI_CUT_VIDEO_POLL_TIMEOUT"),
                field="model.video_poll_timeout_seconds",
            ),
            video_generation_endpoint=_required_text(
                _pick(model, "video_generation_endpoint", "AI_CUT_VIDEO_GENERATION_ENDPOINT"),
                field="model.video_generation_endpoint",
            ),
            video_generation_default_model=_required_text(
                _pick(model, "video_generation_default_model", "AI_CUT_VIDEO_GENERATION_DEFAULT_MODEL"),
                field="model.video_generation_default_model",
            ),
            video_generation_poll_interval_seconds=_required_int(
                _pick(model, "video_generation_poll_interval_seconds", "AI_CUT_VIDEO_GENERATION_POLL_INTERVAL"),
                field="model.video_generation_poll_interval_seconds",
            ),
            video_generation_max_wait_seconds=_required_int(
                _pick(model, "video_generation_max_wait_seconds", "AI_CUT_VIDEO_GENERATION_MAX_WAIT"),
                field="model.video_generation_max_wait_seconds",
            ),
            seeddance_video_endpoint=_required_text(
                _pick_alias(
                    model,
                    ("seeddance_video_endpoint", "jimeng_video_endpoint"),
                    ("AI_CUT_SEEDDANCE_VIDEO_ENDPOINT", "AI_CUT_JIMENG_VIDEO_ENDPOINT"),
                ),
                field="model.seeddance_video_endpoint",
            ),
            seeddance_video_task_endpoint=_required_text(
                _pick_alias(
                    model,
                    ("seeddance_video_task_endpoint", "jimeng_video_task_endpoint"),
                    ("AI_CUT_SEEDDANCE_VIDEO_TASK_ENDPOINT", "AI_CUT_JIMENG_VIDEO_TASK_ENDPOINT"),
                ),
                field="model.seeddance_video_task_endpoint",
            ),
            seeddance_api_key=_required_text(
                _pick_alias(
                    model,
                    ("seeddance_api_key", "jimeng_api_key"),
                    ("AI_CUT_SEEDDANCE_API_KEY", "AI_CUT_JIMENG_API_KEY"),
                ),
                field="model.seeddance_api_key",
            ),
            seeddance_poll_interval_seconds=_required_int(
                _pick_alias(
                    model,
                    ("seeddance_poll_interval_seconds", "jimeng_poll_interval_seconds"),
                    ("AI_CUT_SEEDDANCE_POLL_INTERVAL", "AI_CUT_JIMENG_POLL_INTERVAL"),
                ),
                field="model.seeddance_poll_interval_seconds",
            ),
            seeddance_poll_timeout_seconds=_required_int(
                _pick_alias(
                    model,
                    ("seeddance_poll_timeout_seconds", "jimeng_poll_timeout_seconds"),
                    ("AI_CUT_SEEDDANCE_POLL_TIMEOUT", "AI_CUT_JIMENG_POLL_TIMEOUT"),
                ),
                field="model.seeddance_poll_timeout_seconds",
            ),
            aliyun_billing_access_key_id=_optional_text(
                _pick(model, "aliyun_billing_access_key_id", "AI_CUT_ALIYUN_BILLING_ACCESS_KEY_ID")
            )
            or "",
            aliyun_billing_access_key_secret=_optional_text(
                _pick(model, "aliyun_billing_access_key_secret", "AI_CUT_ALIYUN_BILLING_ACCESS_KEY_SECRET")
            )
            or "",
            volcengine_billing_access_key_id=_optional_text(
                _pick(model, "volcengine_billing_access_key_id", "AI_CUT_VOLCENGINE_BILLING_ACCESS_KEY_ID")
            )
            or "",
            volcengine_billing_access_key_secret=_optional_text(
                _pick(model, "volcengine_billing_access_key_secret", "AI_CUT_VOLCENGINE_BILLING_ACCESS_KEY_SECRET")
            )
            or "",
            video_model_usage_quota=_optional_text(
                _pick(model, "video_model_usage_quota", "AI_CUT_VIDEO_MODEL_USAGE_QUOTA")
            )
            or "",
            api_key=_required_text(_pick(model, "api_key", "AI_CUT_MODEL_API_KEY"), field="model.api_key"),
            timeout_seconds=_required_int(_pick(model, "timeout_seconds", "AI_CUT_MODEL_TIMEOUT"), field="model.timeout_seconds"),
            temperature=_required_float(_pick(model, "temperature", "AI_CUT_MODEL_TEMPERATURE"), field="model.temperature"),
            max_tokens=_required_int(_pick(model, "max_tokens", "AI_CUT_MODEL_MAX_TOKENS"), field="model.max_tokens"),
            vision_frame_count=_required_int(
                _pick(model, "vision_frame_count", "AI_CUT_VISION_FRAME_COUNT"),
                field="model.vision_frame_count",
            ),
        ),
        pipeline=PipelineSettings(
            default_aspect_ratio=_required_text(
                _pick(pipeline, "default_aspect_ratio", "AI_CUT_DEFAULT_ASPECT_RATIO"),
                field="pipeline.default_aspect_ratio",
            ),
            max_output_count=_required_int(
                _pick(pipeline, "max_output_count", "AI_CUT_MAX_OUTPUT_COUNT"),
                field="pipeline.max_output_count",
            ),
            max_source_minutes=_required_int(
                _pick(pipeline, "max_source_minutes", "AI_CUT_MAX_SOURCE_MINUTES"),
                field="pipeline.max_source_minutes",
            ),
            default_intro_template=_required_text(
                _pick(pipeline, "default_intro_template", "AI_CUT_DEFAULT_INTRO_TEMPLATE"),
                field="pipeline.default_intro_template",
            ),
            default_outro_template=_required_text(
                _pick(pipeline, "default_outro_template", "AI_CUT_DEFAULT_OUTRO_TEMPLATE"),
                field="pipeline.default_outro_template",
            ),
        ),
        prompts=prompts,
    )
