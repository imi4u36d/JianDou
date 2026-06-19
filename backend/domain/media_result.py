from __future__ import annotations

from typing import Any


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _map_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_non_blank(*values: str | None) -> str:
    for value in values:
        if value is not None and value.strip():
            return value.strip()
    return ""


def result_metadata(result: dict[str, Any] | None) -> dict[str, Any]:
    return _map_value((result or {}).get("metadata"))


def media_output_url(result: dict[str, Any] | None, metadata: dict[str, Any] | None = None) -> str:
    source = result or {}
    meta = metadata if isinstance(metadata, dict) else result_metadata(source)
    return _first_non_blank(
        _string_value(source.get("outputUrl")),
        _string_value(meta.get("outputUrl")),
        _string_value(meta.get("fileUrl")),
        _string_value(meta.get("remoteSourceUrl")),
    )


def remote_source_url(metadata: dict[str, Any] | None) -> str:
    return _string_value((metadata or {}).get("remoteSourceUrl"))


def thumbnail_candidate(metadata: dict[str, Any] | None) -> str:
    meta = metadata or {}
    return _first_non_blank(
        _string_value(meta.get("thumbnailUrl")),
        _string_value(meta.get("posterUrl")),
        _string_value(meta.get("firstFrameUrl")),
        _string_value(meta.get("startFrameUrl")),
    )
