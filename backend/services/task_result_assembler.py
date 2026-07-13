"""Task result-row assembly for image, video, and joined outputs."""

from __future__ import annotations

from typing import Any

from backend.domain.media_result import result_metadata
from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import IMAGE, VIDEO, VIDEO_JOIN
from backend.services.task_artifact_support import (
    _JOIN_OUTPUT_CLIP_INDEX_BASE,
    _bool_value,
    _float_value,
    _int_value,
    _stable_id,
    _TaskArtifactNaming,
)
from backend.shared import first_non_blank, now_iso, string_value


class TaskResultAssembler:
    def __init__(self, owner: Any) -> None:
        self._owner = owner

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
            "sizeBytes": self._owner._file_size(self._owner._resolve_absolute_path(string_value(video_material.get("fileUrl")))),
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
            "sizeBytes": self._owner._file_size(self._owner._resolve_absolute_path(string_value(join_material.get("fileUrl")))),
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
            "sizeBytes": self._owner._file_size(self._owner._resolve_absolute_path(string_value(image_material.get("fileUrl")))),
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
