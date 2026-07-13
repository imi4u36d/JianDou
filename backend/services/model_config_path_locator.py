"""Filesystem discovery for split application and model configuration."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)
MAX_CHECKED_CANDIDATES_IN_MESSAGE = 12


@dataclass
class LocatedConfig:
    config_dir: Path | None
    project_root: Path | None
    config_files: list[Path]
    source: str
    detail: str

    def config_file(self) -> Path | None:
        return self.config_files[0] if self.config_files else None


class GenerationConfigPathLocator:
    """Locate split generation configuration files in supported directories."""

    def __init__(self, config_dir: str = "./config"):
        self._config_dir = Path(config_dir)

    def locate_app_config(self) -> LocatedConfig:
        checked_candidates: list[Path] = []
        explicit_config_requested = self._has_configured_value(
            "JIANDOU_CONFIG_DIR",
            "jiandou.config.dir",
            "spring.config.additional-location",
            "SPRING_CONFIG_ADDITIONAL_LOCATION",
            "spring.config.location",
            "SPRING_CONFIG_LOCATION",
        )
        explicit_dir = self._resolve_explicit_config_dir(checked_candidates)
        if explicit_dir is not None:
            return self._build_located_config(explicit_dir, "explicit-dir")

        spring_locations = (
            (
                self._first_non_blank(
                    os.environ.get("spring.config.additional-location", ""),
                    os.environ.get("SPRING_CONFIG_ADDITIONAL_LOCATION", ""),
                ),
                "spring.config.additional-location",
            ),
            (
                self._first_non_blank(
                    os.environ.get("spring.config.location", ""),
                    os.environ.get("SPRING_CONFIG_LOCATION", ""),
                ),
                "spring.config.location",
            ),
        )
        for location, source_key in spring_locations:
            resolved = self._resolve_from_spring_location(
                location, source_key, checked_candidates
            )
            if resolved is not None:
                return self._build_located_config(resolved, source_key)

        for candidate in self._spring_default_external_candidates():
            checked_candidates.append(candidate)
            if self._is_config_directory(candidate):
                return self._build_located_config(candidate, "spring-default")
        if not explicit_config_requested:
            for candidate in self._ancestor_external_candidates():
                checked_candidates.append(candidate)
                if self._is_config_directory(candidate):
                    return self._build_located_config(candidate, "parent-default")

        detail = self._describe_checked_candidates(checked_candidates)
        logger.warning("Generation config directory not found; %s", detail)
        return LocatedConfig(None, None, [], "missing", detail)

    def resolve_path(self, configured_path: str) -> Path | None:
        normalized = self._trim_to_empty(configured_path)
        if not normalized:
            return None
        if normalized.startswith("classpath:"):
            logger.warning(
                "Classpath resource cannot be resolved as filesystem path: %s", normalized
            )
            return None
        path = Path(normalized)
        if path.is_absolute():
            return path.resolve()
        located = self.locate_app_config()
        if self._starts_with_config_prefix(normalized) and located.project_root is not None:
            return (located.project_root / path).resolve()
        if located.config_dir is not None:
            return (located.config_dir / path).resolve()
        return (Path.cwd() / path).resolve()

    def resolve_secrets_config_path(self) -> Path | None:
        located = self.locate_app_config()
        if located.config_dir is None:
            return None
        return (located.config_dir / "model" / "providers.secrets.yml").resolve()

    def collect_config_files(self, config_directory: Path | None) -> list[Path]:
        if config_directory is None:
            return []
        normalized_dir = config_directory.resolve()
        if not normalized_dir.is_dir():
            return []
        files: list[Path] = []
        files.extend(self._collect_yaml_files(normalized_dir / "app"))
        files.extend(self._collect_yaml_files(normalized_dir / "pipeline"))
        files.extend(self._collect_yaml_files(normalized_dir / "catalog"))
        files.extend(
            self._collect_yaml_files(
                normalized_dir / "model",
                filter_func=lambda path: (
                    ".secrets." not in path.name
                    and path.parent != normalized_dir / "model" / "providers"
                ),
            )
        )
        files.extend(
            self._collect_yaml_files(
                normalized_dir / "model" / "providers",
                filter_func=lambda path: ".secrets." not in path.name,
            )
        )
        return files

    def _resolve_explicit_config_dir(self, checked_candidates: list[Path]) -> Path | None:
        for key in ("JIANDOU_CONFIG_DIR", "jiandou.config.dir"):
            value = os.environ.get(key, "").strip()
            if not value:
                continue
            candidate = Path(value).resolve()
            checked_candidates.append(candidate)
            if self._is_config_directory(candidate):
                return candidate
            logger.warning(
                "Ignored config dir without split config files from %s=%s", key, value
            )
        return None

    def _resolve_from_spring_location(
        self,
        location: str,
        source_key: str,
        checked_candidates: list[Path],
    ) -> Path | None:
        value = self._trim_to_empty(location)
        if not value:
            return None
        for token in value.split(","):
            raw = self._strip_optional_prefix(self._trim_to_empty(token))
            if not raw or raw.startswith("classpath:"):
                continue
            cleaned = raw[5:] if raw.startswith("file:") else raw
            if "*" in cleaned:
                continue
            candidate = Path(cleaned)
            treat_as_dir = raw.endswith(("/", "\\")) or candidate.is_dir()
            if not treat_as_dir:
                continue
            normalized = candidate.resolve()
            checked_candidates.append(normalized)
            if self._is_config_directory(normalized):
                return normalized
        logger.debug("No usable config directory found in %s", source_key)
        return None

    @staticmethod
    def _spring_default_external_candidates() -> list[Path]:
        cwd = Path.cwd().resolve()
        return list(dict.fromkeys(((cwd / "config").resolve(), cwd)))

    @staticmethod
    def _ancestor_external_candidates() -> list[Path]:
        candidates: list[Path] = []
        current = Path.cwd().resolve().parent
        while True:
            candidates.extend(((current / "config").resolve(), current))
            parent = current.parent
            if parent == current:
                break
            current = parent
        return list(dict.fromkeys(candidates))

    def _is_config_directory(self, directory: Path) -> bool:
        return bool(self.collect_config_files(directory))

    @staticmethod
    def _collect_yaml_files(
        directory: Path,
        filter_func: Callable[[Path], bool] = lambda _path: True,
    ) -> list[Path]:
        if not directory.is_dir():
            return []
        try:
            files: list[Path] = []
            for entry in sorted(directory.iterdir(), key=str):
                resolved = entry.resolve()
                if not resolved.is_file() or resolved.suffix.lower() not in {".yml", ".yaml"}:
                    continue
                if filter_func(resolved):
                    files.append(resolved)
            return files
        except OSError as ex:
            logger.warning("Failed to list config directory: %s (%s)", directory.resolve(), ex)
            return []

    def _build_located_config(
        self, config_directory: Path, source_tag: str
    ) -> LocatedConfig:
        config_dir = config_directory.resolve()
        project_root = config_dir.parent if config_dir.name.lower() == "config" else config_dir
        return LocatedConfig(
            config_dir=config_dir,
            project_root=project_root,
            config_files=self.collect_config_files(config_dir),
            source=f"dir:{config_dir}",
            detail=source_tag,
        )

    @staticmethod
    def _describe_checked_candidates(checked_candidates: list[Path]) -> str:
        if not checked_candidates:
            return "no candidate config files were provided"
        unique = list(dict.fromkeys(checked_candidates))
        joined = ", ".join(str(path) for path in unique[:MAX_CHECKED_CANDIDATES_IN_MESSAGE])
        if len(unique) > MAX_CHECKED_CANDIDATES_IN_MESSAGE:
            joined += ", ..."
        return f"checked config candidates: {joined}"

    @staticmethod
    def _strip_optional_prefix(value: str) -> str:
        return value[len("optional:") :].strip() if value.startswith("optional:") else value

    @staticmethod
    def _starts_with_config_prefix(value: str) -> bool:
        return value.replace("\\", "/").startswith("config/")

    @staticmethod
    def _trim_to_empty(value: str | None) -> str:
        return "" if value is None else value.strip()

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        return next((value.strip() for value in values if value and value.strip()), "")

    @staticmethod
    def _has_configured_value(*keys: str) -> bool:
        return any(bool(os.environ.get(key, "").strip()) for key in keys)
