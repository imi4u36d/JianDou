from __future__ import annotations

from typing import Any

from backend.shared import first_non_blank, map_value, string_value


def result_metadata(result: dict[str, Any] | None) -> dict[str, Any]:
    return map_value((result or {}).get("metadata"))

def media_output_url(result: dict[str, Any] | None, metadata: dict[str, Any] | None = None) -> str:
    source = result or {}
    meta = metadata if isinstance(metadata, dict) else result_metadata(source)
    return first_non_blank(
        string_value(source.get("outputUrl")),
        string_value(meta.get("outputUrl")),
        string_value(meta.get("fileUrl")),
        string_value(meta.get("remoteSourceUrl")),
    )

def remote_source_url(metadata: dict[str, Any] | None) -> str:
    return string_value((metadata or {}).get("remoteSourceUrl"))

def thumbnail_candidate(metadata: dict[str, Any] | None) -> str:
    meta = metadata or {}
    return first_non_blank(
        string_value(meta.get("thumbnailUrl")),
        string_value(meta.get("posterUrl")),
        string_value(meta.get("firstFrameUrl")),
        string_value(meta.get("startFrameUrl")),
    )
