from __future__ import annotations

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_runtime_credentials import RuntimeCredentialResolver
from backend.services.model_config_runtime_media import resolve_media_runtime_profile
from backend.services.model_config_runtime_text import resolve_text_runtime_profile
from backend.services.model_config_snapshot import ConfigSnapshot


def test_empty_text_runtime_profile_uses_snapshot_defaults() -> None:
    snapshot = ConfigSnapshot(
        {"model": {"timeout_seconds": 45, "temperature": 0.3, "max_tokens": 4096}},
        "test-config",
        [],
    )

    profile = resolve_text_runtime_profile(snapshot, RuntimeCredentialResolver(None), "")

    assert profile.config.model == ""
    assert profile.config.timeout_seconds == 45
    assert profile.config.temperature == 0.3
    assert profile.config.max_tokens == 4096
    assert profile.source == "test-config"


def test_empty_media_runtime_profile_preserves_kind_defaults() -> None:
    snapshot = ConfigSnapshot({"model": {"timeout_seconds": 90}}, "test-config", [])

    image = resolve_media_runtime_profile(
        snapshot,
        RuntimeCredentialResolver(None),
        "",
        GenerationModelKinds.IMAGE,
    )
    video = resolve_media_runtime_profile(
        snapshot,
        RuntimeCredentialResolver(None),
        "",
        GenerationModelKinds.VIDEO,
    )

    assert image.config.timeout_seconds == 90
    assert image.capabilities.watermark is False
    assert video.generation_mode() == "i2v"
    assert video.capabilities.poll_interval_seconds == 8
    assert video.capabilities.poll_timeout_seconds == 600
