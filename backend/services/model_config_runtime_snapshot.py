"""Cached YAML snapshot loading for runtime model configuration."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from backend.services.model_config_runtime_credentials import env_value
from backend.services.model_config_snapshot import ConfigSnapshot, merge_maps, normalize_map
from backend.services.model_config_values import bool_value, first_non_blank, int_value


class ModelConfigSnapshotLoader:
    """Discover, merge, cache, and validate model configuration files."""

    def __init__(self, config_dir: str | Path) -> None:
        self._config_dir = Path(config_dir)
        self._cache_ttl_ms = self._resolve_cache_ttl()
        self._fail_fast = self._resolve_fail_fast()
        self._cached_snapshot: tuple[ConfigSnapshot, float] | None = None

    def snapshot(self) -> ConfigSnapshot:
        now = time.time() * 1000
        cached = self._cached_snapshot
        if cached is not None and self._cache_ttl_ms > 0 and now - cached[1] < self._cache_ttl_ms:
            return cached[0]
        loaded = self._load_snapshot()
        self._cached_snapshot = (loaded, now)
        return loaded

    def refresh(self) -> None:
        self._cached_snapshot = None

    def _load_snapshot(self) -> ConfigSnapshot:
        files, sources = self._config_files()
        if not files:
            return self._fail_or_snapshot(
                {},
                f"Generation config directory missing: {self._config_dir}",
                None,
            )
        source = " + ".join(sources)
        try:
            root: dict[str, Any] = {}
            for path in files:
                with path.open() as stream:
                    data = yaml.safe_load(stream)
                if isinstance(data, dict):
                    root = merge_maps(root, normalize_map(data))
            return ConfigSnapshot(root, source, [])
        except Exception as exc:
            return self._fail_or_snapshot({}, f"error:{source}", exc)

    def _config_files(self) -> tuple[list[Path], list[str]]:
        model_dir = self._config_dir / "model"
        models_yml = model_dir / "models.yml"
        providers_dir = model_dir / "providers"
        secrets_yml = model_dir / "providers.secrets.yml"
        legacy_models = self._config_dir / "app" / "models.yml"
        legacy_secrets = self._config_dir / "secrets" / "models.yml"
        files: list[Path] = []

        self._append_first_existing(files, models_yml, legacy_models)
        if providers_dir.is_dir():
            files.extend(
                path
                for path in sorted(providers_dir.iterdir())
                if path.is_file()
                and path.suffix in {".yml", ".yaml"}
                and ".secrets." not in path.name
            )
        self._append_first_existing(files, secrets_yml, legacy_secrets)
        return files, [f"file:{path.resolve()}" for path in files]

    @staticmethod
    def _append_first_existing(files: list[Path], primary: Path, fallback: Path) -> None:
        if primary.exists():
            files.append(primary)
        elif fallback.exists():
            files.append(fallback)

    def _fail_or_snapshot(
        self,
        root: dict[str, Any],
        source: str,
        exc: Exception | None,
    ) -> ConfigSnapshot:
        if self._fail_fast:
            message = f"Generation configuration error (source={source})"
            if exc:
                message += f" (cause={exc.__class__.__name__})"
            raise RuntimeError(message)
        error = f"Failed to load generation config from {source}"
        if exc:
            error += f": {exc}"
        return ConfigSnapshot(root, source, [error])

    @staticmethod
    def _resolve_cache_ttl() -> int:
        seconds = int_value(
            first_non_blank(
                env_value("JIANDOU_CONFIG_CACHE_TTL_SECONDS"),
                env_value("JIANDOU_CONFIG_REFRESH_SECONDS"),
                "5",
            ),
            5,
        )
        return max(0, min(seconds, 3600)) * 1000

    @staticmethod
    def _resolve_fail_fast() -> bool:
        model_level = first_non_blank(env_value("JIANDOU_MODEL_CONFIG_FAIL_FAST"))
        if model_level:
            return bool_value(model_level)
        return bool_value(first_non_blank(env_value("JIANDOU_CONFIG_FAIL_FAST"), "false"))
