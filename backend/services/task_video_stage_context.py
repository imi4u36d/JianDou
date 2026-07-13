"""Task video-stage context queries and mutations."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import is_join, is_primary_video
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.shared import first_non_blank, map_value, safe_int, string_value


class TaskVideoStageContext:
    """Resolve clip inputs and update execution context without persistence."""

    def __init__(self, runtime_support: TaskExecutionRuntimeSupport, media_service: Any | None) -> None:
        self._runtime_support = runtime_support
        self._media_service = media_service

    def assert_can_continue(self, task: TaskRecord) -> None:
        if string_value(task.task_type) and string_value(task.task_type) != "video_generation":
            raise ValueError("只有视频任务支持视频片段续跑。")
        if string_value(task.status).upper() in {"FAILED", "CANCELLED", "PAUSED"}:
            raise ValueError(f"任务当前状态为 {task.status}，不能继续生成视频。")

    def clip_frame_contexts(self, task: TaskRecord) -> list[dict[str, Any]]:
        raw = (task.execution_context or {}).get("clipFrameContexts")
        rows = [dict(item) for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        rows.sort(key=lambda item: safe_int(item.get("clipIndex"), 0))
        return rows

    def planned_clip_count(self, task: TaskRecord, contexts: list[dict[str, Any]]) -> int:
        execution_context = task.execution_context or {}
        return max(
            safe_int(execution_context.get("plannedClipCount"), 0),
            safe_int(execution_context.get("requestedOutputCount"), 0),
            len(contexts),
        )

    def next_missing_clip_index(self, task: TaskRecord) -> int:
        existing = set(self.primary_video_outputs_by_clip(task))
        planned = self.planned_clip_count(task, self.clip_frame_contexts(task))
        return next((index for index in range(1, planned + 1) if index not in existing), max(1, planned))

    def primary_video_outputs_by_clip(self, task: TaskRecord) -> dict[int, dict[str, Any]]:
        rows: dict[int, dict[str, Any]] = {}
        for output in task.outputs or []:
            if not isinstance(output, dict) or not is_primary_video(output.get("resultType")):
                continue
            clip_index = safe_int(output.get("clipIndex"), 0)
            if clip_index > 0:
                rows[clip_index] = output
        return rows

    def existing_join_for_clip_count(self, task: TaskRecord, clip_count: int) -> dict[str, Any]:
        expected = list(range(1, clip_count + 1))
        for output in task.outputs or []:
            if not isinstance(output, dict) or not is_join(output.get("resultType")):
                continue
            if map_value(output.get("extra")).get("clipIndices") == expected and self.output_url(output):
                return output
        return {}

    def duration_for_clip(
        self,
        task: TaskRecord,
        frame_context: dict[str, Any],
        clip_index: int,
    ) -> tuple[int, int, int]:
        storyboard = self.storyboard_clip(task, clip_index)
        duration_row = self.duration_plan_row(task, clip_index)
        target = self.first_positive_int(
            frame_context.get("targetDurationSeconds"),
            storyboard.get("targetDurationSeconds"),
            duration_row.get("targetDurationSeconds"),
            task.min_duration_seconds,
            fallback=8,
        )
        min_duration = self.first_positive_int(
            storyboard.get("minDurationSeconds"),
            duration_row.get("minDurationSeconds"),
            target,
            fallback=target,
        )
        max_duration = self.first_positive_int(
            storyboard.get("maxDurationSeconds"),
            duration_row.get("maxDurationSeconds"),
            target,
            fallback=target,
        )
        target = max(1, target)
        min_duration = max(1, min_duration)
        return target, min_duration, max(min_duration, max_duration)

    def video_prompt_for_clip(
        self, task: TaskRecord, frame_context: dict[str, Any], clip_index: int
    ) -> str:
        storyboard = self.storyboard_clip(task, clip_index)
        return first_non_blank(
            storyboard.get("videoPrompt"),
            frame_context.get("videoPrompt"),
            frame_context.get("scene"),
            frame_context.get("startFramePrompt"),
            frame_context.get("endFramePrompt"),
            task.creative_prompt,
            task.title,
        )

    def video_size(self, task: TaskRecord) -> str:
        configured = string_value((task.execution_context or {}).get("videoSize"))
        if configured:
            return configured
        width, height = self._runtime_support.resolve_dimensions(task)
        return f"{width}*{height}"

    def storyboard_clip(self, task: TaskRecord, clip_index: int) -> dict[str, Any]:
        return self._indexed_context_row(task, "storyboardClips", clip_index)

    def duration_plan_row(self, task: TaskRecord, clip_index: int) -> dict[str, Any]:
        return self._indexed_context_row(task, "clipDurationPlan", clip_index)

    @staticmethod
    def _indexed_context_row(task: TaskRecord, key: str, clip_index: int) -> dict[str, Any]:
        raw = (task.execution_context or {}).get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and safe_int(item.get("clipIndex"), 0) == clip_index:
                    return item
        return {}

    @staticmethod
    def frame_input_url(frame_context: dict[str, Any], role: str) -> str:
        if role == "start":
            return first_non_blank(
                frame_context.get("startFrameUrl"),
                frame_context.get("startFrameKeyframeUrl"),
                frame_context.get("startFrameSourceUrl"),
            )
        return first_non_blank(
            frame_context.get("endFrameConstraintUrl"),
            frame_context.get("endFrameKeyframeUrl"),
            frame_context.get("endFrameSourceUrl"),
        )

    def provider_frame_url(self, frame_url: str) -> str:
        normalized = string_value(frame_url)
        if not normalized or normalized.lower().startswith(("http://", "https://", "data:")):
            return normalized
        publisher = getattr(self._media_service, "publish_local_artifact", None)
        if callable(publisher):
            return string_value(publisher(normalized))
        external = getattr(self._media_service, "build_externally_accessible_url", None)
        return string_value(external(normalized)) if callable(external) else normalized

    def image_material_for_clip(
        self,
        task: TaskRecord,
        clip_index: int,
        first_frame_url: str,
        first_frame_remote_url: str,
    ) -> dict[str, Any]:
        for material in task.materials or []:
            if not isinstance(material, dict):
                continue
            metadata = map_value(material.get("metadata"))
            if (
                safe_int(material.get("clipIndex"), 0) != clip_index
                and safe_int(metadata.get("clipIndex"), 0) != clip_index
            ):
                continue
            frame_role = first_non_blank(metadata.get("frameRole"), material.get("frameRole"))
            kind = first_non_blank(material.get("kind"), material.get("assetRole"))
            if frame_role == "first" or kind == "keyframe-first":
                return material
        return {
            "id": "",
            "fileUrl": first_frame_url,
            "previewUrl": first_frame_url,
            "remoteUrl": first_frame_remote_url,
        }

    @staticmethod
    def context_video_run_ids(task: TaskRecord) -> list[str]:
        raw = (task.execution_context or {}).get("clipVideoRunIds")
        return [string_value(item) for item in raw if string_value(item)] if isinstance(raw, list) else []

    def latest_primary_video_url(self, task: TaskRecord) -> str:
        candidates = (
            (clip_index, self.output_url(output))
            for clip_index, output in self.primary_video_outputs_by_clip(task).items()
        )
        return next((url for _, url in sorted(candidates, reverse=True) if url), "")

    @staticmethod
    def output_url(output: dict[str, Any] | None) -> str:
        if not output:
            return ""
        return first_non_blank(
            output.get("downloadUrl"),
            output.get("downloadPath"),
            output.get("previewUrl"),
            output.get("previewPath"),
        )

    def update_clip_video_context(
        self,
        task: TaskRecord,
        clip_index: int,
        video_run_id: str,
        video_output_url: str,
        returned_last_frame_url: str,
        returned_last_frame_source_type: str,
    ) -> None:
        rows = self.clip_frame_contexts(task)
        for row in rows:
            if safe_int(row.get("clipIndex"), 0) == clip_index:
                row.update(
                    videoRunId=video_run_id,
                    videoOutputUrl=video_output_url,
                    returnedLastFrameUrl=returned_last_frame_url,
                    returnedLastFrameSourceType=returned_last_frame_source_type,
                )
        self.put_execution_context(task, "clipFrameContexts", rows)

    def submitted_video_run_id(
        self, task: TaskRecord, frame_context: dict[str, Any], clip_index: int
    ) -> str:
        direct = string_value(frame_context.get("videoRunId"))
        if direct:
            return direct
        row = next(
            (item for item in self.clip_frame_contexts(task) if safe_int(item.get("clipIndex"), 0) == clip_index),
            {},
        )
        return string_value(row.get("videoRunId"))

    def mark_clip_video_submitted(self, task: TaskRecord, clip_index: int, run_id: str) -> None:
        rows = self.clip_frame_contexts(task)
        for row in rows:
            if safe_int(row.get("clipIndex"), 0) == clip_index:
                row["videoRunId"] = run_id
        self.put_execution_context(task, "clipFrameContexts", rows)

    def put_join_context(self, task: TaskRecord, clip_count: int, join_url: str) -> None:
        self.put_execution_context(task, "latestJoinName", f"join-{clip_count}")
        self.put_execution_context(task, "latestJoinOutputUrl", join_url)
        self.put_execution_context(task, "latestJoinClipIndices", list(range(1, clip_count + 1)))

    @staticmethod
    def active_attempt(task: TaskRecord) -> dict[str, Any]:
        return next(
            (
                attempt
                for attempt in task.attempts or []
                if string_value(attempt.get("attemptId")) == string_value(task.active_attempt_id)
            ),
            {},
        )

    @staticmethod
    def put_execution_context(task: TaskRecord, key: str, value: Any) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        if value is None or (isinstance(value, str) and not value.strip()):
            task.execution_context.pop(key, None)
        else:
            task.execution_context[key] = value

    @staticmethod
    def float_value(value: Any, fallback: float = 0.0) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip()) if value is not None else fallback
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def first_positive_int(*values: Any, fallback: int = 0) -> int:
        for value in values:
            resolved = safe_int(value, 0)
            if resolved > 0:
                return resolved
        return fallback
