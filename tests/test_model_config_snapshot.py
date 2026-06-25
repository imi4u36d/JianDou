from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from backend.services.model_config_snapshot import (
    ConfigSnapshot,
    merge_maps,
    normalize_map,
    parse_path,
    string_value,
)


def test_parse_path_keeps_quoted_model_names_with_dots() -> None:
    assert parse_path('model.models."gpt-5.5".provider') == [
        "model",
        "models",
        "gpt-5.5",
        "provider",
    ]
    assert parse_path(" model.providers.'openai.video'.extras.task_base_url ") == [
        "model",
        "providers",
        "openai.video",
        "extras",
        "task_base_url",
    ]


def test_config_snapshot_reads_values_sections_and_maps_from_normalized_tree() -> None:
    snapshot = ConfigSnapshot(
        {
            "model": {
                "models": {
                    "gpt-5.5": {
                        "kind": "text",
                        "provider": "openai",
                        "supported_sizes": ["1024x1024", "720x1280"],
                    }
                },
                "providers": {
                    "openai": {
                        "vendor": "openai",
                        "extras": {"timeout_seconds": 90},
                    },
                    "disabled": "not-a-section",
                },
            }
        },
        "unit-test",
        [],
    )

    assert snapshot.source == "unit-test"
    assert snapshot.errors == []
    assert snapshot.value('model.models."gpt-5.5"', "provider") == "openai"
    assert snapshot.section("model.providers.openai") == {
        "vendor": "openai",
        "extras": "OrderedDict({'timeout_seconds': 90})",
    }
    assert [section.name for section in snapshot.list_sections("model.providers")] == ["openai"]
    assert snapshot.map('model.models."gpt-5.5"')["supported_sizes"] == ["1024x1024", "720x1280"]


def test_merge_maps_overlays_nested_provider_config_without_dropping_siblings() -> None:
    base = normalize_map(
        {
            "model": {
                "providers": {
                    "openai": {
                        "base_url": "https://api.openai.com/v1",
                        "extras": {"timeout_seconds": 120, "use_responses_api": True},
                    }
                }
            }
        }
    )
    override = normalize_map(
        {
            "model": {
                "providers": {
                    "openai": {
                        "api_key": "sk-test",
                        "extras": {"timeout_seconds": 30},
                    }
                }
            }
        }
    )

    merged = merge_maps(base, override)

    assert merged["model"]["providers"]["openai"]["base_url"] == "https://api.openai.com/v1"
    assert merged["model"]["providers"]["openai"]["api_key"] == "sk-test"
    assert merged["model"]["providers"]["openai"]["extras"] == {
        "timeout_seconds": 30,
        "use_responses_api": True,
    }


def test_string_value_preserves_list_wire_contract() -> None:
    assert string_value([" 720x1280 ", "", None, "1024x1024"]) == "720x1280,1024x1024"
