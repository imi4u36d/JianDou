"""Maintain render-stage execution context and progress projections."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_render_stage_payloads import FrameResolution, build_clip_frame_context
from backend.shared import first_non_blank, safe_int, string_value


class TaskRenderStageContext:
    """Own per-clip and terminal render execution-context updates."""

    def record_clip(
        self,
        task: TaskRecord,
        shot_plan: Any,
        clip_index: int,
        duration_seconds: int,
        start_frame: FrameResolution,
        end_frame: FrameResolution,
    ) -> None:
        values = {
            "imageRunId": first_non_blank(start_frame.run_id(), end_frame.run_id()),
            "keyframeOutputUrl": start_frame.material_url(),
            "keyframeRemoteSourceUrl": start_frame.source_url(),
            "firstFrameUrl": start_frame.video_input_url(),
            "startFrameUrl": start_frame.video_input_url(),
            "startFrameSourceType": start_frame.source_type(),
            "startFrameSourceUrl": start_frame.source_url(),
            "startFrameKeyframeUrl": start_frame.material_url(),
            "startFrameKeyframeRemoteSourceUrl": start_frame.remote_url(),
            "startFrameKeyframeRunId": start_frame.run_id(),
            "lastFrameImageRunId": end_frame.run_id(),
            "requestedLastFrameUrl": end_frame.video_input_url(),
            "endFrameConstraintUrl": end_frame.video_input_url(),
            "endFrameConstraintSourceType": end_frame.source_type(),
            "endFrameConstraintSourceUrl": end_frame.source_url(),
            "endFrameKeyframeUrl": end_frame.material_url(),
            "endFrameKeyframeRemoteSourceUrl": end_frame.remote_url(),
            "endFrameKeyframeRunId": end_frame.run_id(),
        }
        for key, value in values.items():
            self.put(task, key, value)
        self.put_clip_frame(
            task,
            clip_index,
            build_clip_frame_context(
                shot_plan,
                clip_index,
                duration_seconds,
                start_frame,
                end_frame,
                "",
                "",
                "",
                "",
            ),
        )

    def record_clip_progress(
        self,
        task: TaskRecord,
        clip_index: int,
        clip_count: int,
        end_frame: FrameResolution,
    ) -> None:
        task.progress = min(95, 45 + int(45.0 * clip_index / max(1, clip_count)))
        task.completed_output_count = max(task.completed_output_count, clip_index)
        self.put(task, "lastFrameUrl", end_frame.material_url())
        self.put(task, "lastFrameSourceType", end_frame.source_type())
        self.put(task, "lastFrameSourceUrl", end_frame.source_url())

    def complete(self, task: TaskRecord, image_run_ids: list[str], clip_count: int) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        self.put(
            task,
            "clipImageRunIds",
            self.merge_string_list(task.execution_context.get("clipImageRunIds"), image_run_ids),
        )
        for key, value in {
            "clipVideoRunIds": [],
            "videoRunId": None,
            "videoOutputUrl": None,
            "videoThumbnailUrl": None,
            "videoRemoteTaskId": None,
            "videoRemoteSourceUrl": None,
            "resumeExistingOutputCount": None,
            "resumeExistingClipIndices": None,
            "resumeRenderFromClipIndex": None,
            "attemptResumeFromStage": None,
            "attemptResumeFromClipIndex": None,
        }.items():
            self.put(task, key, value)
        task.completed_output_count = clip_count

    def put_clip_frame(
        self,
        task: TaskRecord,
        clip_index: int,
        clip_frame_context: dict[str, Any],
    ) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        rows = [
            dict(item)
            for item in task.execution_context.get("clipFrameContexts", [])
            if isinstance(item, dict) and safe_int(item.get("clipIndex"), 0) != clip_index
        ]
        rows.append(clip_frame_context)
        rows.sort(key=lambda row: safe_int(row.get("clipIndex"), 0))
        self.put(task, "clipFrameContexts", rows)

    @staticmethod
    def put(task: TaskRecord, key: str, value: Any) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        if value is None:
            task.execution_context.pop(key, None)
            return
        if isinstance(value, str) and not value.strip():
            task.execution_context.pop(key, None)
            return
        task.execution_context[key] = value

    @staticmethod
    def merge_string_list(existing: Any, appended: list[str]) -> list[str]:
        values = existing if isinstance(existing, list) else []
        merged = {string_value(item) for item in [*values, *appended]}
        return [value for value in merged if value]
