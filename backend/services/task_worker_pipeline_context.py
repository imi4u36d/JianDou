"""Pure task worker classification and execution-context builders."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import string_value


def is_video_generation_task(task: TaskRecord) -> bool:
    return task.task_type is None or task.task_type == "video_generation"


def stop_before_video_generation(task: TaskRecord) -> bool:
    return bool((task.request_snapshot or {}).get("stopBeforeVideoGeneration"))


def build_storyboard_clip_context(
    shot_plans: list[Any], clip_duration_plan: list[list[int]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, shot_plan in enumerate(shot_plans):
        duration = clip_duration_plan[index] if index < len(clip_duration_plan) else [0, 0, 0]
        row: dict[str, Any] = {
            "clipIndex": shot_plan.sequential_index(),
            "shotLabel": shot_plan.shot_label(),
            "scene": shot_plan.scene(),
            "startFramePrompt": shot_plan.first_frame_prompt(),
            "endFramePrompt": shot_plan.last_frame_prompt(),
            "firstFramePrompt": shot_plan.first_frame_prompt(),
            "lastFramePrompt": shot_plan.last_frame_prompt(),
            "actionPath": shot_plan.motion(),
            "motion": shot_plan.motion(),
            "cameraMovement": shot_plan.camera_movement(),
            "durationHint": shot_plan.duration_hint(),
            "imagePrompt": shot_plan.image_prompt(),
            "videoPrompt": shot_plan.video_prompt(),
            "targetDurationSeconds": duration[0],
            "minDurationSeconds": duration[1],
            "maxDurationSeconds": duration[2],
            "continuityRule": "current_end_frame_matches_next_start_frame",
        }
        if index + 1 < len(shot_plans):
            next_shot = shot_plans[index + 1]
            row.update(
                nextClipIndex=next_shot.sequential_index(),
                nextClipShotLabel=next_shot.shot_label(),
                nextClipStartFramePrompt=next_shot.first_frame_prompt(),
            )
        rows.append(row)
    return rows


def build_character_definition_context(character_definitions: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "characterIndex": index,
            "name": string_value(getattr(character, "name", "")),
            "appearance": string_value(getattr(character, "appearance", "")),
            "definition": string_value(getattr(character, "definition", "")),
        }
        for index, character in enumerate(character_definitions, start=1)
    ]


def put_execution_context(task: TaskRecord, key: str, value: Any) -> None:
    if task.execution_context is None:
        task.execution_context = {}
    if value is None:
        task.execution_context.pop(key, None)
        return
    if isinstance(value, str):
        value = value.strip()
        if not value:
            task.execution_context.pop(key, None)
            return
    task.execution_context[key] = value


def generation_result_map(run: dict[str, Any]) -> dict[str, Any]:
    result = run.get("result")
    return result if isinstance(result, dict) else {}
