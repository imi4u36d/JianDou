from __future__ import annotations

from typing import Any

from backend.domain.task_monitoring import task_monitoring_snapshot
from backend.domain.task_record import TaskRecord
from backend.shared import first_non_blank, map_value, safe_int, string_value


class TaskViewMapper:
    """Maps raw task records to list and detail view models."""

    def __init__(self, local_media_artifact_service: Any | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service

    def to_list_item(self, task: TaskRecord) -> dict[str, Any]:
        monitoring = self._monitoring_summary(task)
        diagnosis = self._diagnosis_summary(task, monitoring)
        failure = self._failure_summary(task)
        return {
            "id": task.id,
            "taskType": task.task_type,
            "title": task.title,
            "status": task.status,
            "progress": task.progress,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
            "sourceFileName": task.source_file_name,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "retryCount": task.retry_count,
            "startedAt": task.started_at,
            "finishedAt": task.finished_at,
            "completedOutputCount": task.completed_output_count,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "effectRatingNote": task.effect_rating_note,
            "ratedAt": task.rated_at,
            "hasTranscript": task.has_transcript,
            "hasTimedTranscript": task.has_timed_transcript,
            "sourceAssetCount": task.source_asset_count,
            "editingMode": task.editing_mode,
            "isQueued": task.is_queued,
            "queuePosition": task.queue_position,
            "currentStage": monitoring.get("currentStage"),
            "activeWorkerInstanceId": monitoring.get("activeWorkerInstanceId"),
            "plannedClipCount": monitoring.get("plannedClipCount", 0),
            "renderedClipCount": monitoring.get("renderedClipCount", 0),
            "diagnosisSeverity": diagnosis.get("severity"),
            "diagnosisCode": diagnosis.get("code"),
            "diagnosisHint": diagnosis.get("hint"),
            "recommendedAction": diagnosis.get("recommendedAction"),
            "failureReason": failure.get("reason"),
            "failureStage": failure.get("stage"),
            "failureClipIndex": failure.get("clipIndex"),
            "thumbnailUrl": self._task_thumbnail_url(task, monitoring),
        }

    def to_detail(self, task: TaskRecord) -> dict[str, Any]:
        row = dict(self.to_list_item(task))
        monitoring = self._monitoring_summary(task)
        row["artifactDirectories"] = monitoring.get("artifactDirectories", {})
        row["introTemplate"] = task.intro_template
        row["outroTemplate"] = task.outro_template
        row["creativePrompt"] = task.creative_prompt
        row["taskSeed"] = task.task_seed
        row["effectRating"] = task.effect_rating
        row["effectRatingNote"] = task.effect_rating_note
        row["ratedAt"] = task.rated_at
        row["errorMessage"] = task.error_message
        row["failureReason"] = self._failure_summary(task).get("reason")
        row["failureStage"] = self._failure_summary(task).get("stage")
        row["failureClipIndex"] = self._failure_summary(task).get("clipIndex")
        row["transcriptPreview"] = task.transcript_text[:min(220, len(task.transcript_text))] if task.transcript_text else None
        row["transcriptCueCount"] = 0
        row["source"] = None
        row["sourceAssets"] = []
        row["storyboardScript"] = task.storyboard_script
        row["materials"] = task.materials
        row["executionContext"] = task.execution_context
        row["requestSnapshot"] = task.request_snapshot or {}
        row["durationDiagnostics"] = []
        row["sourceAssetIds"] = []
        row["sourceFileNames"] = []
        row["plan"] = []
        row["activeAttemptId"] = task.active_attempt_id
        row["attempts"] = task.attempts
        row["stageRuns"] = task.stage_runs
        row["outputs"] = task.outputs
        row["monitoring"] = monitoring
        return row

    def _monitoring_summary(self, task: TaskRecord) -> dict[str, Any]:
        return task_monitoring_snapshot(task)

    def _diagnosis_summary(self, task: TaskRecord, monitoring: dict[str, Any]) -> dict[str, Any]:
        return {"severity": "info", "code": "healthy", "hint": "任务正常", "recommendedAction": "继续观察"}

    def _failure_summary(self, task: TaskRecord) -> dict[str, Any]:
        return {"reason": None, "stage": None, "clipIndex": None}

    def _task_thumbnail_url(self, task: TaskRecord, monitoring: dict[str, Any]) -> str:
        context = task.execution_context or {}
        return first_non_blank(
            self._material_thumbnail_url(task.materials, prefer_non_source=True),
            self._output_thumbnail_url(task.outputs),
            string_value(context.get("videoThumbnailUrl")),
            string_value(context.get("thumbnailUrl")),
            self._material_thumbnail_url(task.materials),
            self._material_thumbnail_url(task.source_assets),
        )

    def _material_thumbnail_url(self, materials: list[dict[str, Any]], prefer_non_source: bool = False) -> str:
        fallback = ""
        for material in materials:
            thumbnail_url = first_non_blank(
                string_value(material.get("thumbnailUrl")),
                string_value(material.get("previewUrl")),
            )
            if not thumbnail_url:
                continue
            kind = string_value(material.get("kind") or material.get("assetRole")).lower()
            if prefer_non_source and kind == "source":
                fallback = fallback or thumbnail_url
                continue
            return thumbnail_url
        return fallback

    def _output_thumbnail_url(self, outputs: list[dict[str, Any]]) -> str:
        for output in sorted(outputs, key=lambda item: safe_int(item.get("clipIndex"), 0), reverse=True):
            extra = map_value(output.get("extra"))
            thumbnail_url = first_non_blank(
                string_value(output.get("thumbnailUrl")),
                string_value(extra.get("thumbnailUrl")),
                string_value(extra.get("posterUrl")),
                string_value(output.get("previewUrl")) if _looks_like_image_url(output.get("previewUrl")) else "",
                string_value(output.get("previewPath")) if _looks_like_image_url(output.get("previewPath")) else "",
            )
            if thumbnail_url:
                return thumbnail_url
        return ""


def _looks_like_image_url(value: Any) -> bool:
    url = string_value(value).lower()
    return url.startswith("/storage/thumbs/") or url.endswith((".avif", ".gif", ".jpg", ".jpeg", ".png", ".webp"))
