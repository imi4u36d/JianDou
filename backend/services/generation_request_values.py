from __future__ import annotations

from typing import Any


def map_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    return {}


def nested_value(payload: dict[str, Any], parent_key: str, child_key: str, default: str = "") -> str:
    parent = payload.get(parent_key)
    if isinstance(parent, dict):
        child = parent.get(child_key)
        if child is not None:
            return str(child)
    return default


def nested_string_list(payload: dict[str, Any], parent_key: str, child_key: str) -> list[str]:
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return []
    child = parent.get(child_key)
    if not isinstance(child, list):
        return []
    return [str(v).strip() for v in child if isinstance(v, str) and v.strip()]


def nested_int(payload: dict[str, Any], parent_key: str, child_key: str, default: int = 0) -> int:
    value = nested_nullable_int(payload, parent_key, child_key)
    return default if value is None else value


def nested_nullable_int(payload: dict[str, Any], parent_key: str, child_key: str) -> int | None:
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return None
    child = parent.get(child_key)
    if isinstance(child, (int, float)):
        return int(child)
    if child is not None:
        try:
            return int(round(float(str(child))))
        except (ValueError, TypeError):
            pass
    return None


def nested_boolean(payload: dict[str, Any], parent_key: str, child_key: str, default: bool = False) -> bool:
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return default
    child = parent.get(child_key)
    if isinstance(child, bool):
        return child
    if isinstance(child, (int, float)):
        return int(child) != 0
    if isinstance(child, str):
        normalized = child.strip().lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
    return default


def string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def first_non_blank(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def find_nested_string(value: Any, *keys: str) -> str:
    wanted = {key for key in keys if key}
    if isinstance(value, dict):
        for key in wanted:
            direct = value.get(key)
            if isinstance(direct, str) and direct.strip():
                return direct.strip()
        for nested in value.values():
            resolved = find_nested_string(nested, *keys)
            if resolved:
                return resolved
    elif isinstance(value, list):
        for item in value:
            resolved = find_nested_string(item, *keys)
            if resolved:
                return resolved
    return ""


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    return []

