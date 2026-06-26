from __future__ import annotations

import os
import uuid
from typing import Any

from backend.domain.media_artifacts import (
    file_ext,
    file_ext_or_default,
    file_name_from_url,
    image_mime_type,
)
from backend.domain.media_result import (
    media_output_url,
    remote_source_url,
    result_metadata,
    thumbnail_candidate,
)
from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import IMAGE, TEXT, VIDEO, VIDEO_JOIN
from backend.shared import first_non_blank, map_value, now_iso, string_value


def _int_value(value: Any, fallback: int = 0) -> int:
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


def _float_value(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return string_value(value).lower() in ("true", "1", "yes")


def _stable_id(prefix: str, *parts: str) -> str:
    seed = prefix + ":" + ":".join(parts)
    return prefix + "_" + uuid.uuid5(uuid.NAMESPACE_OID, seed).hex


_JOIN_OUTPUT_CLIP_INDEX_BASE = 10000


class _TaskArtifactNaming:
    @staticmethod
    def task_base_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}"

    @staticmethod
    def task_running_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}/running"

    @staticmethod
    def task_joined_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}/joined"

    @staticmethod
    def storyboard_file_name(task: TaskRecord, ext: str) -> str:
        return f"storyboard-{task.id}.{ext}"

    @staticmethod
    def clip_frame_file_name(clip_index: int, frame_role: str, ext: str) -> str:
        return f"clip{clip_index}-{frame_role}.{ext}"

    @staticmethod
    def clip_file_name(clip_index: int, ext: str) -> str:
        return f"clip{clip_index}.{ext}"

    @staticmethod
    def last_frame_file_name(clip_index: int, ext: str) -> str:
        return f"clip{clip_index}-last-frame.{ext}"

    @staticmethod
    def join_name(end_clip_index: int) -> str:
        return f"join-{end_clip_index}"


class _StoredArtifact:
    def __init__(self, public_url: str = "") -> None:
        self._public_url = public_url

    def public_url(self) -> str:
        return self._public_url


def _artifact_public_url(artifact: Any, fallback: str = "") -> str:
    value = getattr(artifact, "public_url", "")
    if callable(value):
        return string_value(value())
    return string_value(value) or fallback


class TaskExecutionArtifactAssembler:
    """Assembles execution artifacts, material rows, and result rows from task data."""

    def __init__(self, local_media_artifact_service: Any | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service

    def create_text_material(self, task: TaskRecord, run: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        file_url = string_value(result.get("markdownUrl", ""))
        artifact = self._normalize_task_artifact(
            task,
            file_url,
            _TaskArtifactNaming.storyboard_file_name(task, file_ext_or_default(file_name_from_url(file_url), "md")),
            "storyboard",
        )
        return self._create_material(
            task,
            run,
            TEXT,
            f"{task.title} 分镜脚本",
            _artifact_public_url(artifact, file_url),
            _artifact_public_url(artifact, file_url),
            string_value(result.get("mimeType", "text/markdown")),
            0.0,
            0,
            0,
            False,
            1,
            "storyboard",
            {},
            {"taskArtifact": True},
            "",
        )

    def create_image_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        clip_index: int,
        frame_role: str,
    ) -> dict[str, Any]:
        output_url = string_value(result.get("outputUrl", ""))
        metadata = result_metadata(result)
        normalized_frame_role = "last" if frame_role.lower() == "last" else "first"
        artifact = self._normalize_task_artifact(
            task,
            output_url,
            _TaskArtifactNaming.clip_frame_file_name(
                clip_index,
                normalized_frame_role,
                file_ext_or_default(file_name_from_url(output_url), "png"),
            ),
            "keyframe",
        )
        return self._create_material(
            task,
            run,
            IMAGE,
            f"{task.title} {'尾帧关键画面' if normalized_frame_role == 'last' else '首帧关键画面'}",
            _artifact_public_url(artifact, output_url),
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "image/png")),
            0.0,
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            False,
            clip_index,
            f"keyframe-{normalized_frame_role}",
            metadata,
            {
                "taskArtifact": True,
                "clipIndex": clip_index,
                "frameRole": normalized_frame_role,
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_character_sheet_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        character_index: int,
        character: Any,
    ) -> dict[str, Any]:
        """Persist a generated character sheet as a reusable task material."""
        output_url = string_value(result.get("outputUrl", ""))
        metadata = result_metadata(result)
        normalized_character_index = max(1, character_index)
        artifact = self._normalize_task_artifact(
            task,
            output_url,
            f"character{normalized_character_index}-sheet.{file_ext_or_default(file_name_from_url(output_url), 'png')}",
            "keyframe",
        )
        character_name = string_value(getattr(character, "name", ""))
        character_appearance = string_value(getattr(character, "appearance", ""))
        return self._create_material(
            task,
            run,
            IMAGE,
            f"{task.title} {character_name or f'角色{normalized_character_index}'} 三视图",
            _artifact_public_url(artifact, output_url),
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "image/png")),
            0.0,
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            False,
            1000 + normalized_character_index,
            "character_sheet",
            metadata,
            {
                "taskArtifact": True,
                "variantKind": "character_sheet",
                "characterIndex": normalized_character_index,
                "characterName": character_name,
                "characterAppearance": character_appearance,
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_workspace_image_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        output_index: int = 1,
    ) -> dict[str, Any]:
        metadata = result_metadata(result)
        output_url = media_output_url(result, metadata)
        normalized_output_index = max(1, output_index)
        name_suffix = "" if normalized_output_index <= 1 else f"-{normalized_output_index}"
        artifact = self._normalize_task_artifact(
            task,
            output_url,
            f"workspace-image-{task.id}{name_suffix}.{file_ext_or_default(file_name_from_url(output_url), 'png')}",
            "keyframe",
        )
        snapshot = task.request_snapshot or {}
        asset_type = string_value(snapshot.get("assetType", "")) or string_value(task.task_type)
        return self._create_material(
            task,
            run,
            IMAGE,
            task.title,
            _artifact_public_url(artifact, output_url),
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "image/png")),
            0.0,
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            False,
            normalized_output_index,
            asset_type if asset_type else "free",
            metadata,
            {
                "taskArtifact": True,
                "assetType": asset_type,
                "taskType": task.task_type,
                "outputIndex": normalized_output_index,
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_reference_frame_material(
        self,
        task: TaskRecord,
        clip_index: int,
        source_url: str,
        frame_role: str,
    ) -> dict[str, Any]:
        normalized_frame_role = "last" if frame_role.lower() == "last" else "first"
        target_file_name = _TaskArtifactNaming.clip_frame_file_name(
            clip_index,
            normalized_frame_role,
            file_ext_or_default(file_name_from_url(source_url), "png"),
        )
        file_url = string_value(source_url)
        try:
            artifact = self._normalize_task_artifact(task, source_url, target_file_name, "keyframe")
            file_url = _artifact_public_url(artifact, file_url)
        except Exception:  # noqa: S110 — best-effort artifact normalization
            pass
        return self._create_material(
            task,
            {},
            IMAGE,
            f"{task.title} {'尾帧关键画面' if normalized_frame_role == 'last' else '首帧关键画面'}",
            file_url,
            file_url,
            image_mime_type(target_file_name),
            0.0,
            0,
            0,
            False,
            clip_index,
            f"keyframe-{normalized_frame_role}",
            {},
            {
                "taskArtifact": file_url.startswith("/storage/"),
                "clipIndex": clip_index,
                "frameRole": normalized_frame_role,
                "remoteSourceUrl": string_value(source_url),
                "reusedFromPreviousClip": True,
            },
            string_value(source_url),
        )

    def create_video_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        clip_index: int,
        fallback_duration_seconds: int,
    ) -> dict[str, Any]:
        metadata = result_metadata(result)
        output_url = media_output_url(result, metadata)
        artifact = self._normalize_task_artifact(
            task,
            output_url,
            _TaskArtifactNaming.clip_file_name(clip_index, file_ext_or_default(file_name_from_url(output_url), "mp4")),
            "clip",
        )
        return self._create_material(
            task,
            run,
            VIDEO,
            f"{task.title} 片段输出",
            _artifact_public_url(artifact, output_url),
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "video/mp4")),
            _float_value(result.get("durationSeconds"), float(fallback_duration_seconds)),
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            _bool_value(result.get("hasAudio")),
            clip_index,
            "clip",
            metadata,
            {
                "taskArtifact": True,
                "clipIndex": clip_index,
                "firstFrameUrl": string_value(metadata.get("firstFrameUrl")),
                "lastFrameUrl": self.extract_last_frame_url(result),
                "requestedLastFrameUrl": string_value(metadata.get("requestedLastFrameUrl")),
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_result(
        self,
        task: TaskRecord,
        video_run: dict[str, Any],
        video_result: dict[str, Any],
        video_material: dict[str, Any],
        image_material: dict[str, Any],
        video_model_call: dict[str, Any],
        resolved_last_frame_url: str,
        clip_index: int,
        fallback_duration_seconds: int,
        min_duration_seconds: int,
        max_duration_seconds: int,
    ) -> dict[str, Any]:
        video_metadata = result_metadata(video_result)
        return {
            "id": _stable_id("result", task.id, VIDEO, str(clip_index)),
            "resultType": VIDEO,
            "clipIndex": clip_index,
            "title": f"{task.title} 成片输出 #{clip_index}",
            "reason": "Spring Boot worker 已按分镜顺序完成视频片段输出。",
            "sourceModelCallId": string_value(video_model_call.get("modelCallId")),
            "materialAssetId": video_material.get("id"),
            "startSeconds": 0.0,
            "endSeconds": _float_value(video_result.get("durationSeconds"), float(fallback_duration_seconds)),
            "durationSeconds": _float_value(video_result.get("durationSeconds"), float(fallback_duration_seconds)),
            "previewUrl": string_value(video_material.get("previewUrl")),
            "downloadUrl": string_value(video_material.get("fileUrl")),
            "mimeType": string_value(video_result.get("mimeType", "video/mp4")),
            "width": _int_value(video_result.get("width"), 0),
            "height": _int_value(video_result.get("height"), 0),
            "sizeBytes": self._file_size(self._resolve_absolute_path(string_value(video_material.get("fileUrl")))),
            "remoteUrl": string_value(video_metadata.get("remoteSourceUrl")),
            "extra": {
                "runId": string_value(video_run.get("id")),
                "posterUrl": string_value(image_material.get("fileUrl")),
                "thumbnailUrl": string_value(video_result.get("thumbnailUrl")),
                "hasAudio": _bool_value(video_result.get("hasAudio")),
                "clipIndex": clip_index,
                "targetDurationSeconds": fallback_duration_seconds,
                "minDurationSeconds": min_duration_seconds,
                "maxDurationSeconds": max_duration_seconds,
                "requestedDurationSeconds": fallback_duration_seconds,
                "appliedDurationSeconds": _float_value(
                    video_result.get("durationSeconds"),
                    float(fallback_duration_seconds),
                ),
                "remoteTaskId": string_value(video_metadata.get("taskId")),
                "firstFrameUrl": first_non_blank(
                    string_value(video_metadata.get("firstFrameUrl")),
                    string_value(image_material.get("remoteUrl")),
                ),
                "lastFrameUrl": resolved_last_frame_url,
                "requestedLastFrameUrl": string_value(video_metadata.get("requestedLastFrameUrl")),
            },
            "createdAt": now_iso(),
        }

    def create_join_material(
        self,
        task: TaskRecord,
        artifact: Any,
        end_clip_index: int,
        source_video_urls: list[str],
        total_duration_seconds: float,
    ) -> dict[str, Any]:
        public_url = _artifact_public_url(artifact, "")
        clip_index = _JOIN_OUTPUT_CLIP_INDEX_BASE + max(1, end_clip_index)
        metadata = {
            "taskId": task.id,
            "kind": VIDEO_JOIN,
            "clipIndex": clip_index,
            "joinName": _TaskArtifactNaming.join_name(end_clip_index),
            "clipIndices": list(range(1, max(1, end_clip_index) + 1)),
            "sourceVideoUrls": source_video_urls,
        }
        return self._create_material(
            task,
            {
                "id": f"join_{task.id}_{end_clip_index}",
                "result": {
                    "modelInfo": {
                        "provider": "local",
                        "providerModel": "ffmpeg",
                        "resolvedModel": "ffmpeg",
                    }
                },
            },
            VIDEO,
            f"{task.title} 完整视频",
            public_url,
            public_url,
            "video/mp4",
            total_duration_seconds,
            0,
            0,
            True,
            clip_index,
            VIDEO_JOIN,
            metadata,
            metadata,
            "",
        )

    def create_join_result(
        self,
        task: TaskRecord,
        join_material: dict[str, Any],
        end_clip_index: int,
        source_video_urls: list[str],
        total_duration_seconds: float,
    ) -> dict[str, Any]:
        clip_index = _JOIN_OUTPUT_CLIP_INDEX_BASE + max(1, end_clip_index)
        join_name = _TaskArtifactNaming.join_name(end_clip_index)
        return {
            "id": _stable_id("result", task.id, VIDEO_JOIN, str(end_clip_index)),
            "resultType": VIDEO_JOIN,
            "clipIndex": clip_index,
            "title": f"{task.title} 完整视频",
            "reason": "已按任务片段顺序完成视频拼接。",
            "sourceModelCallId": "",
            "materialAssetId": join_material.get("id"),
            "startSeconds": 0.0,
            "endSeconds": float(total_duration_seconds),
            "durationSeconds": float(total_duration_seconds),
            "previewUrl": string_value(join_material.get("previewUrl")),
            "downloadUrl": string_value(join_material.get("fileUrl")),
            "mimeType": "video/mp4",
            "width": _int_value(join_material.get("width"), 0),
            "height": _int_value(join_material.get("height"), 0),
            "sizeBytes": self._file_size(self._resolve_absolute_path(string_value(join_material.get("fileUrl")))),
            "remoteUrl": string_value(join_material.get("remoteUrl")),
            "extra": {
                "joinName": join_name,
                "clipIndices": list(range(1, max(1, end_clip_index) + 1)),
                "sourceVideoUrls": source_video_urls,
            },
            "createdAt": now_iso(),
        }

    def create_image_result(
        self,
        task: TaskRecord,
        image_run: dict[str, Any],
        image_result: dict[str, Any],
        image_material: dict[str, Any],
        model_call: dict[str, Any],
        output_index: int = 1,
    ) -> dict[str, Any]:
        metadata = result_metadata(image_result)
        snapshot = task.request_snapshot or {}
        normalized_output_index = max(1, output_index)
        return {
            "id": _stable_id("result", task.id, IMAGE, str(normalized_output_index)),
            "resultType": IMAGE,
            "clipIndex": normalized_output_index,
            "title": task.title if normalized_output_index <= 1 else f"{task.title} #{normalized_output_index}",
            "reason": "工作台图片生成已完成。",
            "sourceModelCallId": string_value(model_call.get("modelCallId")),
            "materialAssetId": image_material.get("id"),
            "startSeconds": 0.0,
            "endSeconds": 0.0,
            "durationSeconds": 0.0,
            "previewUrl": string_value(image_material.get("previewUrl")),
            "downloadUrl": string_value(image_material.get("fileUrl")),
            "mimeType": string_value(image_result.get("mimeType", "image/png")),
            "width": _int_value(image_result.get("width"), 0),
            "height": _int_value(image_result.get("height"), 0),
            "sizeBytes": self._file_size(self._resolve_absolute_path(string_value(image_material.get("fileUrl")))),
            "remoteUrl": string_value(metadata.get("remoteSourceUrl")),
            "extra": {
                "runId": string_value(image_run.get("id")),
                "assetType": string_value(snapshot.get("assetType", "")),
                "taskType": task.task_type,
                "outputIndex": normalized_output_index,
                "referenceImageUrls": metadata.get("referenceImageUrls", []),
            },
            "createdAt": now_iso(),
        }

    def normalize_optional_task_artifact(self, task: TaskRecord, source_url: str, target_file_name: str) -> None:
        if not string_value(source_url) or not string_value(target_file_name):
            return
        if self._local_media_artifact_service:
            try:
                self._local_media_artifact_service.materialize_artifact(
                    source_url,
                    _TaskArtifactNaming.task_running_relative_dir(task),
                    target_file_name,
                )
            except Exception:  # noqa: S110 — best-effort materialization
                pass

    def extract_last_frame_url(self, value: Any) -> str:
        direct = self._find_nested_string(value, "lastFrameUrl", "last_frame_url")
        if direct:
            return direct
        return self._find_nested_role_url(value, "last_frame")

    def _normalize_task_artifact(
        self, task: TaskRecord, source_url: str, target_file_name: str, fallback_kind: str
    ) -> Any:
        resolved = string_value(target_file_name)
        if not resolved:
            if fallback_kind == "storyboard":
                resolved = _TaskArtifactNaming.storyboard_file_name(task, "bin")
            elif fallback_kind == "keyframe":
                resolved = _TaskArtifactNaming.clip_frame_file_name(1, "first", "bin")
            else:
                resolved = _TaskArtifactNaming.clip_file_name(1, "bin")
        if self._local_media_artifact_service:
            return self._local_media_artifact_service.materialize_artifact(
                source_url,
                _TaskArtifactNaming.task_running_relative_dir(task),
                resolved,
            )
        return _StoredArtifact(public_url=source_url)

    def _create_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        media_type: str,
        title: str,
        file_url: str,
        preview_url: str,
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
        absolute_path = self._resolve_absolute_path(file_url) if file_url else ""
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
            "sizeBytes": self._file_size(absolute_path) if absolute_path else 0,
            "durationSeconds": duration_seconds,
            "width": width,
            "height": height,
            "hasAudio": has_audio,
            "storagePath": absolute_path,
            "localFilePath": absolute_path,
            "fileUrl": file_url or "",
            "previewUrl": preview_url or "",
            "thumbnailUrl": thumbnail_url or "",
            "remoteUrl": remote_url or "",
            "metadata": metadata,
            "createdAt": now_iso(),
        }

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

    def _file_size(self, absolute_path: str) -> int:
        if not absolute_path:
            return 0
        try:
            return os.path.getsize(absolute_path) if os.path.exists(absolute_path) else 0
        except OSError:
            return 0

    def _resolve_absolute_path(self, file_url: str) -> str:
        if self._local_media_artifact_service:
            return self._local_media_artifact_service.resolve_absolute_path(file_url)
        return file_url

    def _find_nested_string(self, value: Any, *keys: str) -> str:
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
                if isinstance(candidate, dict):
                    nested = self._find_nested_string(candidate, "url", "href", "uri")
                    if nested:
                        return nested
            for nested in value.values():
                resolved = self._find_nested_string(nested, *keys)
                if resolved:
                    return resolved
        if isinstance(value, list):
            for item in value:
                resolved = self._find_nested_string(item, *keys)
                if resolved:
                    return resolved
        return ""

    def _find_nested_role_url(self, value: Any, role: str) -> str:
        if isinstance(value, dict):
            current_role = string_value(value.get("role")).lower()
            if role == current_role:
                image_url = value.get("image_url") or value.get("imageUrl")
                resolved = self._find_nested_string(image_url, "url", "href", "uri")
                if resolved:
                    return resolved
            for nested in value.values():
                resolved = self._find_nested_role_url(nested, role)
                if resolved:
                    return resolved
        if isinstance(value, list):
            for item in value:
                resolved = self._find_nested_role_url(item, role)
                if resolved:
                    return resolved
        return ""
