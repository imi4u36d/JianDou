from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import string_value


def reference_image_urls(task: TaskRecord) -> list[str]:
    raw = (task.execution_context or {}).get("referenceImageUrls")
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        normalized = string_value(item)
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def compatible_image_reference_urls(urls: list[str], local_media_artifact_service: Any | None) -> list[str]:
    resolved: list[str] = []
    for url in urls:
        normalized = string_value(url)
        if not normalized:
            continue
        compatible = _compatible_reference_url(normalized, local_media_artifact_service)
        if compatible not in resolved:
            resolved.append(compatible)
    return resolved


def _compatible_reference_url(url: str, local_media_artifact_service: Any | None) -> str:
    if not url.startswith("/storage/"):
        return url
    if not local_media_artifact_service:
        raise ValueError("referenceImageUrl is local storage address; local media artifact service is required")
    try:
        data_uri = local_media_artifact_service.image_data_uri_from_public_url(url)
    except RuntimeError as exc:
        raise ValueError("referenceImageUrl is local storage address but cannot be converted to data URI") from exc
    if not data_uri:
        raise ValueError("referenceImageUrl is local storage address; local media artifact service is required")
    return data_uri
