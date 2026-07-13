from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_contracts import AdminModelConfigResponse
from backend.services.model_config_user_catalog import UserModelProviderCatalog

pytestmark = pytest.mark.service


class _Resolver:
    def __init__(self) -> None:
        self.models = {
            GenerationModelKinds.TEXT: [
                {"value": "gpt", "provider": "openai", "vendor": "OpenAI"},
            ],
            GenerationModelKinds.IMAGE: [
                {"value": "image-1", "provider": "openai", "vendor": "OpenAI"},
            ],
            GenerationModelKinds.VIDEO: [],
        }
        self.sections = [
            SimpleNamespace(name="openai", values={"provider": "openai", "vendor": "OpenAI"}),
            SimpleNamespace(name="agnes", values={"provider": "agnes", "vendor": "Agnes"}),
        ]

    def list_models_by_kind(self, kind):
        return self.models[kind]

    def list_sections(self, path):
        assert path == "model.providers"
        return self.sections

    def resolve_text_profile(self, name, user_id):
        return SimpleNamespace(base_url="https://api.example/v1", api_key="", task_base_url="")

    def resolve_media_profile(self, name, kind, user_id):
        return SimpleNamespace(base_url="https://media.example/v1", api_key="", task_base_url="")

    def value(self, path, key, default):
        if path == "model.providers.agnes" and key == "base_url":
            return "https://agnes.example/v1/"
        return default


def _model(name: str, kind: str) -> AdminModelConfigResponse.ModelItem:
    return AdminModelConfigResponse.ModelItem(
        name=name,
        label=name,
        kind=kind,
        provider="openai",
        vendor="OpenAI",
        family="",
        description="",
        supports_seed=False,
        supports_responses_api=False,
        generation_mode="",
        supported_sizes=[],
        supported_durations=[],
        ready=True,
        config_source="test",
        endpoint_host="",
        task_endpoint_host="",
        issues=[],
    )


def test_user_provider_catalog_groups_models_and_includes_config_only_sections() -> None:
    catalog = UserModelProviderCatalog(_Resolver())

    providers = catalog.read_providers(
        [_model("gpt", GenerationModelKinds.TEXT), _model("image-1", GenerationModelKinds.IMAGE)],
        {"AGNES": "secret"},
        user_id=7,
    )

    assert [provider.key for provider in providers] == ["agnes", "openai"]
    assert providers[0].base_url == "https://agnes.example/v1"
    assert providers[0].api_key_configured is True
    assert providers[1].kinds == [GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE]
    assert providers[1].model_names == ["gpt", "image-1"]


def test_user_provider_catalog_builds_key_update_catalog_from_models_and_sections() -> None:
    providers = UserModelProviderCatalog(_Resolver()).read_provider_catalog()

    assert [provider.key for provider in providers] == ["agnes", "openai"]
    assert providers[1].kinds == [GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE]
    assert providers[1].model_names == ["gpt", "image-1"]
