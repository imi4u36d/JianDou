"""Sanitises large base64 image payloads in observability data.

Mirrors the Java ProviderPayloadSanitizer.  Recursively walks dicts and
lists, replacing any base64-encoded image strings with a redacted summary
so that log output stays manageable.
"""
from __future__ import annotations

import base64
import hashlib
import re
from typing import Any

_LARGE_BASE64_THRESHOLD = 512


class ProviderPayloadSanitizer:
    """Sanitises base64 image payloads in observability data.

    All methods are static; the class is never instantiated.
    """

    @staticmethod
    def sanitize(value: Any) -> Any:
        """Recursively sanitise a payload, redacting large base64 image data."""
        return ProviderPayloadSanitizer._sanitize("", value)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize(key: str, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for k, v in value.items():
                child_key = str(k) if k is not None else ""
                sanitized[child_key] = ProviderPayloadSanitizer._sanitize(child_key, v)
            return sanitized
        if isinstance(value, list):
            return [ProviderPayloadSanitizer._sanitize("", item) for item in value]
        if isinstance(value, str) and ProviderPayloadSanitizer._should_redact(key, value):
            return ProviderPayloadSanitizer._redacted_summary(value)
        return value

    @staticmethod
    def _should_redact(key: str, value: str) -> bool:
        trimmed = (value or "").strip()
        if not trimmed:
            return False
        if ProviderPayloadSanitizer._is_base64_image_key(key):
            return True
        if trimmed.lower().startswith("data:") and ";base64," in trimmed.lower():
            return True
        return len(trimmed) >= _LARGE_BASE64_THRESHOLD and ProviderPayloadSanitizer._looks_like_base64(trimmed)

    @staticmethod
    def _is_base64_image_key(key: str) -> bool:
        normalized = (key or "").strip().replace("_", "").replace("-", "").lower()
        return normalized in ("b64json", "base64data", "base64", "imagebase64")

    @staticmethod
    def _looks_like_base64(value: str) -> bool:
        compact = re.sub(r"\s+", "", value)
        if len(compact) < _LARGE_BASE64_THRESHOLD:
            return False
        base64_chars = sum(
            1 for ch in compact
            if ch.isalnum() or ch in "+/=-_"
        )
        return base64_chars >= len(compact) * 0.95

    @staticmethod
    def _redacted_summary(value: str) -> dict[str, Any]:
        return {
            "redacted": True,
            "type": "base64_image",
            "length": len(value) if value else 0,
            "sha256": hashlib.sha256((value or "").encode("utf-8")).hexdigest(),
            "mimeType": ProviderPayloadSanitizer._infer_mime_type(value),
        }

    @staticmethod
    def _infer_mime_type(value: str) -> str:
        normalized = (value or "").strip()
        if normalized.lower().startswith("data:"):
            semicolon = normalized.find(";")
            if semicolon > 5:
                return normalized[5:semicolon]
        return "image/*"
