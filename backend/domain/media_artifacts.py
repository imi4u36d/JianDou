"""Media artifact filename and MIME helpers."""

from __future__ import annotations

import re
from typing import Any


def file_name_from_url(url: str) -> str:
    """Return the final path segment from a URL or storage path."""
    normalized = re.sub(r"[?#].*$", "", string_value(url)).rstrip("/")
    index = normalized.rfind("/")
    return normalized[index + 1:] if index >= 0 else normalized


def file_ext(file_name: str) -> str:
    """Return a safe lowercase extension without a dot."""
    normalized = re.sub(r"[?#].*$", "", string_value(file_name))
    index = normalized.rfind(".")
    if index < 0 or index == len(normalized) - 1:
        return ""
    candidate = normalized[index + 1:].lower()
    return candidate if re.match(r"^[a-z0-9]{1,10}$", candidate) else ""


def file_ext_or_default(file_name: str, fallback: str) -> str:
    """Return the file extension, or a fallback when missing/unsafe."""
    ext = file_ext(file_name)
    return ext if ext else fallback


def image_mime_type(file_name: str) -> str:
    """Infer the common image MIME type from a file name."""
    ext = file_ext(file_name)
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "webp":
        return "image/webp"
    return "image/png"


def string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()
