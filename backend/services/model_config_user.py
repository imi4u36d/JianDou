"""Per-user model catalog responses and credential update orchestration."""

from __future__ import annotations

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_contracts import (
    AdminModelConfigKeyUpdateRequest,
    AdminModelConfigResponse,
    AdminModelConfigValidationResponse,
)
from backend.services.model_config_credentials import MybatisUserModelCredentialRepository
from backend.services.model_config_response_support import ModelConfigResponseSupport
from backend.services.model_config_runtime import ModelRuntimePropertiesResolver
from backend.services.model_config_snapshot import string_value as _string_value
from backend.services.model_config_user_catalog import UserModelProviderCatalog
from backend.services.model_config_values import bool_value as _bool_value
from backend.services.model_config_values import double_value as _double_value
from backend.services.model_config_values import first_non_blank as _first_non_blank
from backend.services.model_config_values import parse_integer_list as _parse_integer_list
from backend.services.model_config_values import parse_string_list as _parse_string_list


class UserModelConfigService(ModelConfigResponseSupport):
    """Per-user model configuration service.

    Mirrors the Java UserModelConfigService.
    """

    KIND_ORDER = [GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO]
    MISSING_API_KEY_ISSUE = "缺少 api_key"

    def __init__(
        self,
        model_resolver: ModelRuntimePropertiesResolver,
        user_credential_repo: MybatisUserModelCredentialRepository | None = None,
    ):
        self._model_resolver = model_resolver
        self._user_credential_repo = user_credential_repo
        self._provider_catalog = UserModelProviderCatalog(model_resolver)

    def read(self, user_id: int) -> AdminModelConfigResponse:
        api_keys: dict[str, str] = {}
        if self._user_credential_repo:
            api_keys = self._user_credential_repo.find_api_keys_by_user_id(user_id)

        models: list[AdminModelConfigResponse.ModelItem] = []
        models.extend(self._read_text_models(GenerationModelKinds.TEXT, user_id))
        models.extend(self._read_media_models(GenerationModelKinds.IMAGE, user_id))
        models.extend(self._read_media_models(GenerationModelKinds.VIDEO, user_id))
        models.sort(key=lambda m: (self._kind_index(m.kind), m.name.lower()))

        providers = self._provider_catalog.read_providers(models, api_keys, user_id)
        return AdminModelConfigResponse(
            config_source="user-db",
            summary=self._build_summary(models, providers),
            defaults=self._read_defaults(),
            providers=providers,
            models=list(models),
            config_errors=list(self._model_resolver.config_errors()),
        )

    def validate_keys(
        self, user_id: int, request: AdminModelConfigKeyUpdateRequest
    ) -> AdminModelConfigValidationResponse:
        current = self.read(user_id)
        snapshot = self._apply_api_key_overrides(current, self._collect_api_key_updates(request, current.providers))
        valid = not snapshot.config_errors and all(m.ready for m in snapshot.models)
        return AdminModelConfigValidationResponse(valid=valid, snapshot=snapshot)

    def save_keys(self, user_id: int, request: AdminModelConfigKeyUpdateRequest) -> AdminModelConfigResponse:
        current = self.read(user_id)
        updates = self._collect_api_key_updates(request, current.providers)
        if updates.errors:
            raise ValueError(" / ".join(updates.errors))
        if updates.api_keys and self._user_credential_repo:
            self._user_credential_repo.save_api_keys(user_id, updates.api_keys)
        return self.read(user_id)

    def reset_keys(self, user_id: int, request: AdminModelConfigKeyUpdateRequest) -> None:
        if user_id is None:
            raise ValueError("缺少用户ID")
        updates = self._collect_api_key_updates(request, self._provider_catalog.read_provider_catalog())
        if updates.errors:
            raise ValueError(" / ".join(updates.errors))
        if updates.api_keys and self._user_credential_repo:
            self._user_credential_repo.save_api_keys(user_id, updates.api_keys)

    # ---- Private helpers --------------------------------------------------

    def _read_defaults(self) -> AdminModelConfigResponse.Defaults:
        return AdminModelConfigResponse.Defaults(
            default_aspect_ratio=self._model_resolver.value("pipeline", "default_aspect_ratio", "9:16"),
            image_size=self._model_resolver.value("catalog.defaults", "image_size", "1024x1024"),
            video_size=self._model_resolver.value("catalog.defaults", "video_size", "720*1280"),
            video_duration_seconds=self._model_resolver.int_value("catalog.defaults", "video_duration_seconds", 8),
            timeout_seconds=self._model_resolver.int_value("model", "timeout_seconds", 120),
            temperature=_double_value(self._model_resolver.value("model", "temperature", "0.15"), 0.15),
            max_tokens=self._model_resolver.int_value("model", "max_tokens", 2000),
        )

    def _read_text_models(self, kind: str, user_id: int) -> list[AdminModelConfigResponse.ModelItem]:
        items: list[AdminModelConfigResponse.ModelItem] = []
        for item in self._model_resolver.list_models_by_kind(kind):
            name = _string_value(item.get("value"))
            profile = self._model_resolver.resolve_text_profile(name, user_id)
            issues: list[str] = []
            if not profile.api_key:
                issues.append(self.MISSING_API_KEY_ISSUE)
            if not profile.base_url:
                issues.append("缺少 base_url")
            items.append(
                AdminModelConfigResponse.ModelItem(
                    name=name,
                    label=_first_non_blank(_string_value(item.get("label")), name),
                    kind=kind,
                    provider=profile.provider,
                    vendor=_string_value(item.get("vendor")),
                    family=_string_value(item.get("family")),
                    description=_string_value(item.get("description")),
                    supports_seed=_bool_value(str(item.get("supportsSeed", ""))),
                    supports_responses_api=_bool_value(str(item.get("supportsResponsesApi", ""))),
                    generation_mode="",
                    supported_sizes=[],
                    supported_durations=[],
                    ready=not issues and profile.ready,
                    config_source=profile.source,
                    endpoint_host=profile.endpoint_host,
                    task_endpoint_host="",
                    issues=issues,
                )
            )
        return items

    def _read_media_models(self, kind: str, user_id: int) -> list[AdminModelConfigResponse.ModelItem]:
        items: list[AdminModelConfigResponse.ModelItem] = []
        for item in self._model_resolver.list_models_by_kind(kind):
            name = _string_value(item.get("value"))
            profile = self._model_resolver.resolve_media_profile(name, kind, user_id)
            issues: list[str] = []
            if not profile.api_key:
                issues.append(self.MISSING_API_KEY_ISSUE)
            if not profile.base_url:
                issues.append("缺少 base_url")
            if kind == GenerationModelKinds.VIDEO and not profile.task_base_url:
                issues.append("缺少 task_base_url")
            items.append(
                AdminModelConfigResponse.ModelItem(
                    name=name,
                    label=_first_non_blank(_string_value(item.get("label")), name),
                    kind=kind,
                    provider=profile.provider,
                    vendor=_string_value(item.get("vendor")),
                    family=_string_value(item.get("family")),
                    description=_string_value(item.get("description")),
                    supports_seed=_bool_value(str(item.get("supportsSeed", ""))),
                    supports_responses_api=False,
                    generation_mode=_string_value(item.get("generationMode")),
                    supported_sizes=_parse_string_list(item.get("supportedSizes")),
                    supported_durations=_parse_integer_list(item.get("supportedDurations")),
                    ready=not issues and profile.ready,
                    config_source=profile.source,
                    endpoint_host=profile.endpoint_host,
                    task_endpoint_host=profile.task_endpoint_host,
                    issues=issues,
                )
            )
        return items
