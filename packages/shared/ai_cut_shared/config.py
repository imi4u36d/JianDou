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


def _ensure_dict(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid config field: {field} must be a table")
    return value


def _normalize_name(value: str | None) -> str:
    return (value or "").strip()


def _normalize_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
        return tuple(item for item in items if item)
    if isinstance(value, (list, tuple)):
        values: list[str] = []
        for item in value:
            normalized = _normalize_name(str(item))
            if normalized:
                values.append(normalized)
        return tuple(values)
    raise ValueError("list value must be string or array")


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
class ProviderSettings:
    name: str
    provider: str
    api_key: str
    base_url: str
    extras: dict[str, Any]


@dataclass(frozen=True)
class ModelDefinition:
    name: str
    provider: str
    kind: str
    label: str
    capabilities: tuple[str, ...]
    family: str | None = None
    description: str | None = None
    aliases: tuple[str, ...] = ()
    fallback_model: str | None = None


@dataclass(frozen=True)
class ModelDefaults:
    text_analysis: str
    planner_fusion: str
    creative_prompt: str
    vision_analysis: str
    prompt_rewrite: str
    image_generation: str
    video_generation: str


@dataclass(frozen=True)
class RemoteModelTarget:
    provider: str
    family: str
    mode: str
    model_name: str
    fallback_model_name: str | None
    endpoint: str
    api_key: str


@dataclass(frozen=True)
class ModelSettings:
    providers: dict[str, ProviderSettings]
    models: dict[str, ModelDefinition]
    defaults: ModelDefaults
    aliyun_billing_access_key_id: str
    aliyun_billing_access_key_secret: str
    volcengine_billing_access_key_id: str
    volcengine_billing_access_key_secret: str
    video_model_usage_quota: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    vision_frame_count: int

    def _provider(self, key: str) -> ProviderSettings | None:
        return self.providers.get(key)

    def _default_model(self, key: str) -> ModelDefinition | None:
        model_name = getattr(self.defaults, key, None)
        if not model_name:
            return None
        return self.models.get(model_name)

    @property
    def provider(self) -> str:
        provider = self._provider("aliyun_compatible")
        return provider.provider if provider is not None else ""

    @property
    def endpoint(self) -> str:
        provider = self._provider("aliyun_compatible")
        return provider.base_url if provider is not None else ""

    @property
    def api_key(self) -> str:
        provider = self._provider("aliyun_compatible")
        return provider.api_key if provider is not None else ""

    @property
    def model_name(self) -> str:
        return self.defaults.text_analysis

    @property
    def fallback_model_name(self) -> str | None:
        model = self._default_model("text_analysis")
        return model.fallback_model if model is not None else None

    @property
    def text_analysis_model_name(self) -> str:
        return self.defaults.text_analysis

    @property
    def text_analysis_fallback_model_name(self) -> str | None:
        return self.fallback_model_name

    @property
    def text_analysis_models(self) -> str:
        return ",".join(name for name, item in self.models.items() if "text_analysis" in item.capabilities)

    @property
    def vision_model_name(self) -> str | None:
        return self.defaults.vision_analysis

    @property
    def vision_fallback_model_name(self) -> str | None:
        model = self._default_model("vision_analysis")
        return model.fallback_model if model is not None else None

    @property
    def image_model_name(self) -> str:
        return self.defaults.image_generation

    @property
    def video_model_name(self) -> str:
        return self.defaults.video_generation

    @property
    def video_models(self) -> str:
        return ",".join(name for name, item in self.models.items() if "video_generation" in item.capabilities)

    @property
    def video_endpoint(self) -> str:
        provider = self._provider("aliyun_video")
        return provider.base_url if provider is not None else ""

    @property
    def video_task_endpoint(self) -> str:
        provider = self._provider("aliyun_video")
        if provider is None:
            return ""
        return str(provider.extras.get("task_base_url") or "").strip()

    @property
    def video_prompt_extend(self) -> bool:
        provider = self._provider("aliyun_video")
        if provider is None:
            return False
        return bool(provider.extras.get("prompt_extend"))

    @property
    def video_poll_interval_seconds(self) -> int:
        provider = self._provider("aliyun_video")
        if provider is None:
            return 8
        return int(provider.extras.get("poll_interval_seconds") or 8)

    @property
    def video_poll_timeout_seconds(self) -> int:
        provider = self._provider("aliyun_video")
        if provider is None:
            return 600
        return int(provider.extras.get("poll_timeout_seconds") or 600)

    @property
    def video_generation_endpoint(self) -> str:
        return self.video_endpoint

    @property
    def video_generation_default_model(self) -> str:
        return self.defaults.video_generation

    @property
    def video_generation_poll_interval_seconds(self) -> int:
        return self.video_poll_interval_seconds

    @property
    def video_generation_max_wait_seconds(self) -> int:
        return self.video_poll_timeout_seconds

    @property
    def seeddance_video_endpoint(self) -> str:
        provider = self._provider("volcengine_seed")
        return provider.base_url if provider is not None else ""

    @property
    def seeddance_video_task_endpoint(self) -> str:
        provider = self._provider("volcengine_seed")
        if provider is None:
            return ""
        return str(provider.extras.get("task_base_url") or "").strip()

    @property
    def seeddance_api_key(self) -> str:
        provider = self._provider("volcengine_seed")
        return provider.api_key if provider is not None else ""

    @property
    def seeddance_poll_interval_seconds(self) -> int:
        provider = self._provider("volcengine_seed")
        if provider is None:
            return 8
        return int(provider.extras.get("poll_interval_seconds") or 8)

    @property
    def seeddance_poll_timeout_seconds(self) -> int:
        provider = self._provider("volcengine_seed")
        if provider is None:
            return 600
        return int(provider.extras.get("poll_timeout_seconds") or 600)


@dataclass(frozen=True)
class PipelineSettings:
    default_aspect_ratio: str
    max_output_count: int
    max_source_minutes: int
    default_intro_template: str
    default_outro_template: str


@dataclass(frozen=True)
class PromptSettings:
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


def _parse_provider_settings(raw_model: dict[str, Any]) -> dict[str, ProviderSettings]:
    raw_providers = _ensure_dict(raw_model.get("providers", {}), field="model.providers")
    providers: dict[str, ProviderSettings] = {}
    for key, item in raw_providers.items():
        provider_section = _ensure_dict(item, field=f"model.providers.{key}")
        extras_raw = provider_section.get("extras", {})
        providers[key] = ProviderSettings(
            name=key,
            provider=_required_text(provider_section.get("provider") or key, field=f"model.providers.{key}.provider"),
            api_key=_required_text(provider_section.get("api_key"), field=f"model.providers.{key}.api_key"),
            base_url=_required_text(provider_section.get("base_url"), field=f"model.providers.{key}.base_url"),
            extras=dict(extras_raw) if isinstance(extras_raw, dict) else {},
        )
    if not providers:
        raise ValueError("missing required config field: model.providers")
    return providers


def _parse_model_definitions(raw_model: dict[str, Any], providers: dict[str, ProviderSettings]) -> dict[str, ModelDefinition]:
    raw_models = _ensure_dict(raw_model.get("models", {}), field="model.models")
    models: dict[str, ModelDefinition] = {}
    for key, item in raw_models.items():
        model_section = _ensure_dict(item, field=f"model.models.{key}")
        provider_key = _required_text(model_section.get("provider"), field=f"model.models.{key}.provider")
        if provider_key not in providers:
            raise ValueError(f"model '{key}' references unknown provider '{provider_key}'")
        capabilities = _normalize_list(model_section.get("capabilities"))
        if not capabilities:
            raise ValueError(f"missing required config field: model.models.{key}.capabilities")
        models[key] = ModelDefinition(
            name=key,
            provider=provider_key,
            kind=_required_text(model_section.get("kind"), field=f"model.models.{key}.kind"),
            label=_required_text(model_section.get("label") or key, field=f"model.models.{key}.label"),
            capabilities=capabilities,
            family=_optional_text(model_section.get("family")),
            description=_optional_text(model_section.get("description")),
            aliases=_normalize_list(model_section.get("aliases")),
            fallback_model=_optional_text(model_section.get("fallback_model")),
        )
    if not models:
        raise ValueError("missing required config field: model.models")
    for key, model in models.items():
        if model.fallback_model and model.fallback_model not in models:
            raise ValueError(f"model '{key}' fallback references unknown model '{model.fallback_model}'")
    return models


def _parse_model_defaults(raw_model: dict[str, Any], models: dict[str, ModelDefinition]) -> ModelDefaults:
    defaults_section = _ensure_dict(raw_model.get("defaults", {}), field="model.defaults")
    defaults = ModelDefaults(
        text_analysis=_required_text(defaults_section.get("text_analysis"), field="model.defaults.text_analysis"),
        planner_fusion=_required_text(defaults_section.get("planner_fusion"), field="model.defaults.planner_fusion"),
        creative_prompt=_required_text(defaults_section.get("creative_prompt"), field="model.defaults.creative_prompt"),
        vision_analysis=_required_text(defaults_section.get("vision_analysis"), field="model.defaults.vision_analysis"),
        prompt_rewrite=_required_text(defaults_section.get("prompt_rewrite"), field="model.defaults.prompt_rewrite"),
        image_generation=_required_text(defaults_section.get("image_generation"), field="model.defaults.image_generation"),
        video_generation=_required_text(defaults_section.get("video_generation"), field="model.defaults.video_generation"),
    )
    for field_name, model_name in (
        ("text_analysis", defaults.text_analysis),
        ("planner_fusion", defaults.planner_fusion),
        ("creative_prompt", defaults.creative_prompt),
        ("vision_analysis", defaults.vision_analysis),
        ("prompt_rewrite", defaults.prompt_rewrite),
        ("image_generation", defaults.image_generation),
        ("video_generation", defaults.video_generation),
    ):
        if model_name not in models:
            raise ValueError(f"model.defaults.{field_name} references unknown model '{model_name}'")
    return defaults


def resolve_text_analysis_target(model: ModelSettings, requested_model: str | None = None) -> RemoteModelTarget:
    model_name = _normalize_name(requested_model) or model.defaults.text_analysis
    definition = model.models.get(model_name)
    if definition is None:
        raise ValueError(f"unknown model: {model_name}")
    provider = model.providers.get(definition.provider)
    if provider is None:
        raise ValueError(f"unknown provider: {definition.provider}")
    adapter = str(provider.extras.get("adapter") or provider.provider).strip()
    family = _normalize_name(definition.family) or definition.kind
    return RemoteModelTarget(
        provider=provider.provider,
        family=family,
        mode=adapter,
        model_name=definition.name,
        fallback_model_name=definition.fallback_model,
        endpoint=provider.base_url,
        api_key=provider.api_key,
    )


def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path) if config_path is not None else default_config_path()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    app = _ensure_dict(raw.get("app", {}), field="app")
    database = _ensure_dict(raw.get("database", {}), field="database")
    redis = _ensure_dict(raw.get("redis", {}), field="redis")
    storage = _ensure_dict(raw.get("storage", {}), field="storage")
    model = _ensure_dict(raw.get("model", {}), field="model")
    pipeline = _ensure_dict(raw.get("pipeline", {}), field="pipeline")
    prompt = _ensure_dict(raw.get("prompt", {}), field="prompt")

    repo = repo_root()

    def _pick(section: dict[str, Any], key: str, env_name: str) -> Any:
        env_value = os.getenv(env_name)
        if env_value is not None and env_value != "":
            return env_value
        return section.get(key)

    prompt_path_value = _pick(prompt, "file", "AI_CUT_PROMPTS_PATH")
    prompt_config_path = (
        _resolve_path(repo, _required_text(prompt_path_value, field="prompt.file"))
        if prompt_path_value is not None and str(prompt_path_value).strip()
        else default_prompt_config_path()
    )
    prompts = _load_prompt_settings(prompt_config_path)

    providers = _parse_provider_settings(model)
    models = _parse_model_definitions(model, providers)
    defaults = _parse_model_defaults(model, models)

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
            providers=providers,
            models=models,
            defaults=defaults,
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
