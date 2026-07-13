"""Fallback response mapping for task query records."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import string_value


def _active_attempt_context(task: TaskRecord) -> tuple[str, str]:
    for attempt in task.attempts:
        if attempt.get("attemptId") == task.active_attempt_id:
            return (
                string_value(attempt.get("resumeFromStage", "")),
                string_value(attempt.get("workerInstanceId", "")),
            )
    return "", ""


def task_list_item(task: TaskRecord) -> dict[str, Any]:
    current_stage, active_worker = _active_attempt_context(task)
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
        "currentStage": current_stage,
        "activeWorkerInstanceId": active_worker,
        "plannedClipCount": 0,
        "renderedClipCount": 0,
        "diagnosisSeverity": "",
        "diagnosisCode": "",
        "diagnosisHint": "",
        "recommendedAction": "",
        "failureReason": task.error_message or "",
        "failureStage": "",
        "failureClipIndex": None,
        "thumbnailUrl": "",
        "ownerUserId": task.owner_user_id,
        "ownerUsername": "",
        "ownerRole": "",
    }


def task_detail(task: TaskRecord) -> dict[str, Any]:
    current_stage, active_worker = _active_attempt_context(task)
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
        "isQueued": task.is_queued,
        "queuePosition": task.queue_position,
        "currentStage": current_stage,
        "activeWorkerInstanceId": active_worker,
        "ownerUserId": task.owner_user_id,
        "ownerUsername": "",
        "errorMessage": task.error_message or "",
        "editingMode": task.editing_mode,
        "creativePrompt": task.creative_prompt,
        "hasTranscript": task.has_transcript,
        "hasTimedTranscript": task.has_timed_transcript,
        "sourceAssetCount": task.source_asset_count,
        "transcriptPreview": task.transcript_text[: min(220, len(task.transcript_text))] if task.transcript_text else None,
        "transcriptCueCount": 0,
        "executionContext": task.execution_context,
        "requestSnapshot": task.request_snapshot or {},
        "storyboardScript": task.storyboard_script,
        "artifactDirectories": {},
        "durationDiagnostics": [],
        "plan": [],
        "trace": list(task.trace),
        "statusHistory": list(task.status_history),
        "attempts": list(task.attempts),
        "stageRuns": list(task.stage_runs),
        "modelCalls": list(task.model_calls),
        "materials": list(task.materials),
        "outputs": list(task.outputs),
        "sourceAssets": list(task.source_assets),
    }
