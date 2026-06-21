"""Shared utility functions used across the backend.

Previously these helpers were duplicated in many files (37+ copies of
``_safe_int``, ``_first_non_blank``, etc.).  Import from here instead.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

# ── String helpers ────────────────────────────────────────────────────────

def string_value(value: Any) -> str:
    """Return ``value`` as a stripped string, or ``""`` on None."""
    if value is None:
        return ""
    return str(value).strip()


def first_non_blank(*values: str | None) -> str:
    """Return the first non-empty, non-whitespace string, or ``""``."""
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""


def trim(value: str | None, fallback: str = "") -> str:
    """Trim *value*; return *fallback* if the result is empty."""
    if value is None:
        return fallback
    stripped = value.strip()
    return stripped if stripped else fallback


# ── Numeric helpers ───────────────────────────────────────────────────────

def safe_int(value: Any, fallback: int = 0) -> int:
    """Coerce *value* to an int, returning *fallback* on failure."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def safe_float(value: Any, fallback: float = 0.0) -> float:
    """Coerce *value* to a float, returning *fallback* on failure."""
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def safe_bool(value: Any) -> bool:
    """Coerce common truthy/falsy representations to ``bool``."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    s = str(value).strip().lower()
    return s in ("true", "1", "yes")


def positive_int(raw: Any, fallback: int) -> int:
    """Parse a positive int; return *fallback* on failure or zero."""
    v = safe_int(raw, 0)
    return v if v > 0 else fallback


def first_positive_int(*values: int) -> int:
    """Return the first positive value, or 0."""
    for v in values:
        if v > 0:
            return v
    return 0


# ── Dict / JSON helpers ───────────────────────────────────────────────────

def map_value(value: Any) -> dict[str, Any]:
    """Return *value* as a dict, or an empty dict."""
    if isinstance(value, dict):
        return value
    return {}


def read_json(text: str | None) -> dict[str, Any]:
    """Parse JSON text; return ``{}`` on failure."""
    if not text or not text.strip():
        return {}
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def write_json(data: dict[str, Any]) -> str:
    """Serialize *data* to a compact JSON string."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


# ── Nested accessors ──────────────────────────────────────────────────────

def nested_value(
    payload: dict[str, Any], parent_key: str, child_key: str, default: str = ""
) -> str:
    """Return ``payload[parent_key][child_key]`` as a string, or *default*."""
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return default
    return string_value(parent.get(child_key)) or default


def nested_string_list(
    payload: dict[str, Any], parent_key: str, child_key: str
) -> list[str]:
    """Return ``payload[parent_key][child_key]`` as a list of strings."""
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return []
    raw = parent.get(child_key)
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None]
    return []


def nested_int(
    payload: dict[str, Any], parent_key: str, child_key: str, default: int = 0
) -> int:
    """Return ``payload[parent_key][child_key]`` as an int, or *default*."""
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return default
    return safe_int(parent.get(child_key), default)


def nested_nullable_int(
    payload: dict[str, Any], parent_key: str, child_key: str
) -> int | None:
    """Return ``payload[parent_key][child_key]`` as an int, or ``None``."""
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return None
    raw = parent.get(child_key)
    if raw is None:
        return None
    return safe_int(raw, 0) if raw is not None else None


def nested_boolean(
    payload: dict[str, Any], parent_key: str, child_key: str, default: bool = False
) -> bool:
    """Return ``payload[parent_key][child_key]`` as a bool."""
    parent = payload.get(parent_key)
    if not isinstance(parent, dict):
        return default
    raw = parent.get(child_key)
    if raw is None:
        return default
    return safe_bool(raw)


def find_nested_string(value: Any, *keys: str) -> str:
    """Walk nested dicts via *keys*; return first non-blank string leaf."""
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
        if current is None:
            return ""
    return string_value(current)


# ── Date / time helpers ───────────────────────────────────────────────────

def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


# ── Identity generator ────────────────────────────────────────────────────

import uuid as _uuid


def random_id() -> str:
    """Return a random hex identifier (UUID4 hex)."""
    return _uuid.uuid4().hex


# ── Text helpers ──────────────────────────────────────────────────────────

def truncate_text(value: str, limit: int) -> str:
    """Truncate *value* to *limit* characters; return ``""`` for None."""
    if not value:
        return ""
    return value if len(value) <= limit else value[:limit]
