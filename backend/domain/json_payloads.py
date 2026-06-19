from __future__ import annotations

import json
from typing import Any


def read_json_value(text: str | None, fallback: Any = None) -> Any:
    if fallback is None:
        fallback = {}
    if not text:
        return fallback
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return fallback
    return fallback if parsed is None else parsed


def read_json_object(text: str | None) -> dict[str, Any]:
    parsed = read_json_value(text, {})
    return parsed if isinstance(parsed, dict) else {}


def read_json_list(text: str | None) -> list[Any]:
    parsed = read_json_value(text, [])
    return parsed if isinstance(parsed, list) else []


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def write_json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def write_json_object(value: Any) -> str:
    return write_json_value(object_value(value))

