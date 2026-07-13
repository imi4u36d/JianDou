"""Shared material-row construction and local file metadata lookup."""

from __future__ import annotations

import os
from typing import Any

from backend.domain.media_artifacts import file_ext, file_name_from_url
from backend.domain.media_result import thumbnail_candidate
from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_support import _stable_id
from backend.shared import first_non_blank, map_value, now_iso, string_value


class TaskMaterialFactory:
    def __init__(self, local_media_artifact_service: Any | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service

    def create(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        media_type: str,
        title: str,
        file_url: str,
        _preview_url: str,
        mime_type: str,
        duration_seconds: float,
        width: int,
        height: int,
        has_audio: bool,
        clip_index: int,
        kind: str,
        source_metadata: dict[str, Any],
        extra_metadata: dict[str, Any],
        remote_url: str,
    ) -> dict[str, Any]:
        run_result = map_value(run.get("result"))
        model_info = map_value(run_result.get("modelInfo"))
        absolute_path = self.resolve_absolute_path(file_url) if file_url else ""
        file_name = file_name_from_url(file_url) if file_url else ""
        metadata: dict[str, Any] = {
            "taskId": task.id,
            "kind": kind,
            "clipIndex": clip_index,
            "runId": string_value(run.get("id")),
            "sourceMetadata": source_metadata if source_metadata else {},
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        thumbnail_url = self._media_thumbnail_url(media_type, file_url, metadata)
        return {
            "id": _stable_id("asset", task.id, kind, str(clip_index)),
            "ownerUserId": task.owner_user_id,
            "kind": kind,
            "mediaType": media_type,
            "title": title,
            "originProvider": string_value(model_info.get("provider", "spring-placeholder")),
            "originModel": string_value(model_info.get("resolvedModel", model_info.get("providerModel"))),
            "remoteTaskId": first_non_blank(string_value(source_metadata.get("taskId")), string_value(run.get("id"))),
            "remoteAssetId": "",
            "originalFileName": file_name,
            "storedFileName": file_name,
            "fileExt": file_ext(file_name),
            "storageProvider": "local",
            "mimeType": mime_type,
            "sizeBytes": self.file_size(absolute_path) if absolute_path else 0,
            "durationSeconds": duration_seconds,
            "width": width,
            "height": height,
            "hasAudio": has_audio,
            "storagePath": absolute_path,
            "localFilePath": absolute_path,
            "publicUrl": file_url or "",
            "fileUrl": file_url or "",
            "previewUrl": thumbnail_url or "",
            "thumbnailUrl": thumbnail_url or "",
            "remoteUrl": remote_url or "",
            "metadata": metadata,
            "createdAt": now_iso(),
        }

    def file_size(self, absolute_path: str) -> int:
        if not absolute_path:
            return 0
        try:
            return os.path.getsize(absolute_path) if os.path.exists(absolute_path) else 0
        except OSError:
            return 0

    def resolve_absolute_path(self, file_url: str) -> str:
        if self._local_media_artifact_service:
            return self._local_media_artifact_service.resolve_absolute_path(file_url)
        return file_url

    def _media_thumbnail_url(self, media_type: str, file_url: str, metadata: dict[str, Any]) -> str:
        candidate = thumbnail_candidate(metadata)
        if self._local_media_artifact_service:
            return string_value(
                self._local_media_artifact_service.ensure_media_thumbnail(
                    media_type,
                    file_url,
                    [candidate] if candidate else [],
                    480,
                )
            )
        return candidate or ""
