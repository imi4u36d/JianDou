"""Filesystem configuration and prompt-template resolution for model invocation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from backend.services.model_config_path_locator import (
    GenerationConfigPathLocator as GenerationConfigPathLocator,
)
from backend.services.model_config_path_locator import LocatedConfig as LocatedConfig

logger = logging.getLogger(__name__)

class GenerationConfigurationException(Exception):
    """Raised when generation configuration is missing or invalid."""


class PromptTemplateResolver:
    """Resolve named system prompts from YAML templates."""

    def __init__(
        self,
        config_path_locator: GenerationConfigPathLocator | None = None,
        fail_fast_on_prompt_error: bool | None = None,
    ):
        self._config_path_locator = config_path_locator or GenerationConfigPathLocator()
        self._errors: list[str] = []
        self._fail_fast = (
            fail_fast_on_prompt_error if fail_fast_on_prompt_error is not None else self._resolve_prompt_fail_fast()
        )

    def system_prompt(self, prompt_name: str, key: str) -> str:
        prompt_file = self._locate_prompt_file(prompt_name)
        if prompt_file is None or not prompt_file.exists():
            return self._fail_or_empty(f"Prompt file not found for promptName={prompt_name} key={key}", None)
        try:
            resolved = self._load_yaml_prompt(prompt_file, key)
            self._errors = []
            return resolved
        except (ValueError, KeyError, yaml.YAMLError) as ex:
            return self._fail_or_empty(
                f"Failed to load prompt template from file={prompt_file.resolve()} key={key}: {ex}", ex
            )

    def prompt_errors(self) -> list[str]:
        return list(self._errors)

    def _locate_prompt_file(self, prompt_name: str) -> Path | None:
        prompt_directory = self._first_non_blank(
            os.environ.get("JIANDOU_PROMPT_DIR", ""),
            os.environ.get("jiandou.prompt.dir", ""),
            "prompts",
        )
        base = self._config_path_locator.resolve_path(prompt_directory)
        if base is None:
            self._fail_or_empty(f"Prompt directory cannot be resolved: {prompt_directory}", None)
            return None
        for suffix in (".yml", ".yaml"):
            candidate = (base / f"{prompt_name}{suffix}").resolve()
            if candidate.exists():
                return candidate
        return None

    @classmethod
    def _load_yaml_prompt(cls, prompt_file: Path, key: str) -> str:
        with prompt_file.open(encoding="utf-8") as file:
            loaded = yaml.safe_load(file)
        if not isinstance(loaded, dict):
            raise ValueError("Prompt yaml is empty")
        system_prompts = cls._normalize_map(loaded).get("system_prompts")
        if not isinstance(system_prompts, dict):
            raise ValueError("Prompt yaml missing system_prompts section")
        value = cls._normalize_map(system_prompts).get(key)
        if value is None:
            raise KeyError(f"Prompt key not found: {key}")
        text = str(value).strip()
        if not text:
            raise ValueError(f"Prompt key is blank: {key}")
        return text

    def _fail_or_empty(self, message: str, cause: Exception | None) -> str:
        self._errors = [message]
        if cause is None:
            logger.warning(message)
        else:
            logger.error(message, exc_info=cause)
        if self._fail_fast:
            raise GenerationConfigurationException(message)
        return ""

    def _resolve_prompt_fail_fast(self) -> bool:
        prompt_level = self._first_non_blank(
            os.environ.get("JIANDOU_PROMPT_FAIL_FAST", ""),
            os.environ.get("jiandou.prompt.fail-fast", ""),
        )
        if prompt_level:
            return self._bool_value(prompt_level)
        return self._bool_value(self._first_non_blank(os.environ.get("JIANDOU_CONFIG_FAIL_FAST", ""), "false"))

    @staticmethod
    def _bool_value(raw: str) -> bool:
        return (raw or "").strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _normalize_map(cls, source: dict[Any, Any]) -> dict[str, Any]:
        return {
            str(key): cls._normalize_map(value) if isinstance(value, dict) else value
            for key, value in source.items()
        }

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        return next((value.strip() for value in values if value and value.strip()), "")
