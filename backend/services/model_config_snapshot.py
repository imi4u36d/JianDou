"""Pure helpers for model YAML configuration snapshots."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


def string_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(string_value(item) for item in value if string_value(item))
    return str(value).strip()


def normalize_map(source: dict[Any, Any]) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for key, value in source.items():
        result[str(key)] = normalize_value(value)
    return result


def normalize_value(value: object) -> object:
    if isinstance(value, dict):
        return normalize_map(value)
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


def parse_path(raw_path: str) -> list[str]:
    value = "" if raw_path is None else str(raw_path).strip()
    if not value:
        return []
    tokens: list[str] = []
    current: list[str] = []
    quote = ""
    for ch in value:
        if ch in ("'", '"') and not quote:
            quote = ch
            continue
        if ch == quote:
            quote = ""
            continue
        if ch == "." and not quote:
            token = "".join(current).strip()
            if token:
                tokens.append(token)
            current = []
            continue
        current.append(ch)
    token = "".join(current).strip()
    if token:
        tokens.append(token)
    return tokens


def merge_maps(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = OrderedDict(base)
    for key, override_value in override.items():
        current_value = merged.get(key)
        if isinstance(current_value, dict) and isinstance(override_value, dict):
            merged[key] = merge_maps(normalize_map(current_value), normalize_map(override_value))
        else:
            merged[key] = override_value
    return merged


@dataclass
class ConfigSection:
    name: str
    values: dict[str, str]


class ConfigSnapshot:
    """Immutable-ish view over normalized model configuration data."""

    def __init__(self, root: dict[str, Any], source: str, errors: list[str]):
        self._root = normalize_map(root)
        self._source = source
        self._errors = list(errors)

    @property
    def source(self) -> str:
        return self._source

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    def value(self, section_name: str, key: str) -> str:
        return string_value(self._path_value(f"{section_name}.{key}"))

    def section(self, section_name: str) -> dict[str, str]:
        value = self._path_value(section_name)
        if not isinstance(value, dict):
            return {}
        result: dict[str, str] = OrderedDict()
        for key, child_value in normalize_map(value).items():
            result[key] = string_value(child_value)
        return result

    def list_sections(self, prefix: str) -> list[ConfigSection]:
        value = self._path_value(prefix)
        if not isinstance(value, dict):
            return []
        sections: list[ConfigSection] = []
        for key, child in normalize_map(value).items():
            if not isinstance(child, dict):
                continue
            values: dict[str, str] = OrderedDict()
            for child_key, child_value in normalize_map(child).items():
                values[child_key] = string_value(child_value)
            sections.append(ConfigSection(key, values))
        return sections

    def map(self, path: str) -> dict[str, Any]:
        value = self._path_value(path)
        if isinstance(value, dict):
            return normalize_map(value)
        return {}

    def _path_value(self, path: str) -> object:
        current: object = self._root
        for token in parse_path(path):
            if not isinstance(current, dict):
                return None
            current = normalize_map(current).get(token)
            if current is None:
                return None
        return current
