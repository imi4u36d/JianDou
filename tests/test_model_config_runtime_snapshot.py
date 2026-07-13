from __future__ import annotations

from backend.services.model_config_runtime_snapshot import ModelConfigSnapshotLoader


def test_snapshot_loader_merges_provider_files_and_refreshes_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("JIANDOU_CONFIG_CACHE_TTL_SECONDS", "60")
    model_dir = tmp_path / "model"
    provider_dir = model_dir / "providers"
    provider_dir.mkdir(parents=True)
    (model_dir / "models.yml").write_text(
        "model:\n  models:\n    demo:\n      kind: text\n      provider: openai\n",
        encoding="utf-8",
    )
    provider = provider_dir / "openai.yml"
    provider.write_text(
        "model:\n  providers:\n    openai:\n      base_url: https://one.example/v1\n",
        encoding="utf-8",
    )
    loader = ModelConfigSnapshotLoader(tmp_path)

    first = loader.snapshot()
    provider.write_text(
        "model:\n  providers:\n    openai:\n      base_url: https://two.example/v1\n",
        encoding="utf-8",
    )

    assert first.value("model.providers.openai", "base_url") == "https://one.example/v1"
    assert loader.snapshot() is first
    loader.refresh()
    assert loader.snapshot().value("model.providers.openai", "base_url") == "https://two.example/v1"


def test_snapshot_loader_reports_missing_configuration(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("JIANDOU_MODEL_CONFIG_FAIL_FAST", raising=False)
    monkeypatch.setenv("JIANDOU_CONFIG_FAIL_FAST", "false")

    snapshot = ModelConfigSnapshotLoader(tmp_path).snapshot()

    assert snapshot.errors
    assert "directory missing" in snapshot.source
