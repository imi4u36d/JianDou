from __future__ import annotations

from typing import Any

from backend.domain.task_result_types import is_join, is_primary_video
from backend.domain.task_resume import existing_video_clip_indices, last_contiguous_completed_clip_index


def task_outputs(task: Any) -> list[dict[str, Any]]:
    if hasattr(task, "outputs_view") and callable(task.outputs_view):
        return _dict_list(task.outputs_view())
    if hasattr(task, "outputs_view"):
        return _dict_list(task.outputs_view)
    return _dict_list(getattr(task, "outputs", []))


def task_monitoring_snapshot(task: Any) -> dict[str, Any]:
    outputs = task_outputs(task)
    active_attempt = _active_attempt(task)
    latest_trace = _latest_by(getattr(task, "trace", []), "timestamp")
    latest_stage_run = _latest_by(getattr(task, "stage_runs", []), "startedAt")
    latest_video_output = latest_video_output_of(outputs)
    latest_join_output = latest_join_output_of(outputs)

    rendered_clip_indices = existing_video_clip_indices(outputs)
    planned_clip_count = _planned_clip_count(getattr(task, "execution_context", {}) or {})
    contiguous_count = last_contiguous_completed_clip_index(rendered_clip_indices)
    ctx = getattr(task, "execution_context", {}) or {}

    return {
        "currentStage": _first_non_blank(
            _string_value(ctx.get("currentStage")),
            _string_value(latest_stage_run.get("stageName")),
            _string_value(latest_stage_run.get("stage")),
            _string_value(active_attempt.get("stageName")),
            _string_value(active_attempt.get("resumeFromStage")),
            _string_value(latest_trace.get("stage")),
        ),
        "activeWorkerInstanceId": _first_non_blank(
            _string_value(active_attempt.get("workerInstanceId")),
            _string_value(ctx.get("workerInstanceId")),
            _string_value(latest_stage_run.get("workerInstanceId")),
            _string_value(latest_trace.get("workerInstanceId")),
        ),
        "activeAttemptStatus": _string_value(active_attempt.get("status")),
        "plannedClipCount": planned_clip_count,
        "renderedClipCount": len(rendered_clip_indices),
        "renderedClipIndices": rendered_clip_indices,
        "contiguousRenderedClipCount": contiguous_count,
        "missingClipIndices": missing_clip_indices(planned_clip_count, rendered_clip_indices),
        "latestRenderedClipIndex": rendered_clip_indices[-1] if rendered_clip_indices else 0,
        "resumeFromStage": _first_non_blank(_string_value(active_attempt.get("resumeFromStage")), "render"),
        "resumeFromClipIndex": max(1, contiguous_count + 1),
        "latestVideoOutputUrl": _first_non_blank(
            _string_value(latest_video_output.get("downloadUrl")),
            _string_value(latest_video_output.get("previewUrl")),
        ),
        "latestJoinName": _first_non_blank(
            _string_value(ctx.get("latestJoinName")),
            _string_value(_map_value(latest_join_output.get("extra")).get("joinName")),
        ),
        "latestJoinOutputUrl": _first_non_blank(
            _string_value(ctx.get("latestJoinOutputUrl")),
            _string_value(latest_join_output.get("downloadUrl")),
        ),
        "latestJoinClipIndex": _int_value(latest_join_output.get("clipIndex"), 0),
        "latestJoinClipIndices": _list_value(_map_value(latest_join_output.get("extra")).get("clipIndices")),
        "artifactDirectories": {},
        "latestVideoOutput": latest_video_output,
        "latestJoinOutput": latest_join_output,
    }


def latest_video_output_of(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    return _latest_by([output for output in outputs if is_primary_video(output.get("resultType"))], "clipIndex")


def latest_join_output_of(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    return _latest_by([output for output in outputs if is_join(output.get("resultType"))], "clipIndex")


def missing_clip_indices(planned_clip_count: int, rendered_clip_indices: list[int]) -> list[int]:
    if planned_clip_count <= 0:
        return []
    rendered_set = set(rendered_clip_indices)
    return [idx for idx in range(1, planned_clip_count + 1) if idx not in rendered_set]


def _active_attempt(task: Any) -> dict[str, Any]:
    attempts = _dict_list(getattr(task, "attempts", []))
    active_attempt_id = _string_value(getattr(task, "active_attempt_id", ""))
    if active_attempt_id:
        for attempt in attempts:
            if attempt.get("attemptId") == active_attempt_id:
                return attempt
    return _latest_by(attempts, "startedAt")


def _planned_clip_count(execution_context: dict[str, Any]) -> int:
    planned = _int_value(execution_context.get("plannedClipCount"), 0)
    if planned > 0:
        return planned
    return len(_list_value(execution_context.get("clipPrompts")))


def _latest_by(items: list[Any], key: str) -> dict[str, Any]:
    dicts = _dict_list(items)
    if not dicts:
        return {}
    if key == "clipIndex":
        return max(dicts, key=lambda item: _int_value(item.get(key), 0), default={})
    return max(dicts, key=lambda item: _string_value(item.get(key)), default={})


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _map_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


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


def _first_non_blank(*values: str | None) -> str:
    for value in values:
        if value is not None and value.strip():
            return value.strip()
    return ""
