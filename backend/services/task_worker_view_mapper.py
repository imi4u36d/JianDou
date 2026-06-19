from __future__ import annotations

from typing import Any

from backend.domain.task_monitoring import task_monitoring_snapshot
from backend.domain.task_record import TaskRecord


class TaskViewMapper:
    """Maps raw task records to view models (list item, detail, showcase)."""

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

    def to_showcase_item(self, task: TaskRecord) -> dict[str, Any]:
        monitoring = self._monitoring_summary(task)
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
            "sourceFileName": task.source_file_name,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "completedOutputCount": task.completed_output_count,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "description": task.title,
            "previewUrl": monitoring.get("latestVideoOutputUrl", ""),
            "downloadUrl": monitoring.get("latestVideoOutputUrl", ""),
            "joinName": monitoring.get("latestJoinName", ""),
            "models": task.request_snapshot or {},
            "media": {},
        }

    def _monitoring_summary(self, task: TaskRecord) -> dict[str, Any]:
        return task_monitoring_snapshot(task)

    def _diagnosis_summary(self, task: TaskRecord, monitoring: dict[str, Any]) -> dict[str, Any]:
        return {"severity": "info", "code": "healthy", "hint": "任务正常", "recommendedAction": "继续观察"}

    def _failure_summary(self, task: TaskRecord) -> dict[str, Any]:
        return {"reason": None, "stage": None, "clipIndex": None}

    def _task_thumbnail_url(self, task: TaskRecord, monitoring: dict[str, Any]) -> str:
        return ""
