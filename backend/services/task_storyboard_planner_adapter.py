"""Adapter from the domain storyboard planner to the worker stub contract."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.domain.task_storyboard_planner import TaskStoryboardPlanner
from backend.services.stubs import TaskStoryboardPlannerStub
from backend.shared import safe_int, string_value


class TaskStoryboardPlannerAdapter:
    def __init__(self, planner: TaskStoryboardPlanner | None = None) -> None:
        self._planner = planner or TaskStoryboardPlanner()

    def build_storyboard_shot_plans(
        self, task: TaskRecord, storyboard_markdown: str
    ) -> list[TaskStoryboardPlannerStub.StoryboardShotPlan]:
        plans: list[TaskStoryboardPlannerStub.StoryboardShotPlan] = []
        for plan in self._planner.build_storyboard_shot_plans(task, storyboard_markdown):
            plans.append(
                TaskStoryboardPlannerStub.StoryboardShotPlan(
                    sequential_index=safe_int(getattr(plan, "sequential_index", 0), len(plans) + 1),
                    shot_label=string_value(getattr(plan, "shot_label", "")),
                    scene=string_value(getattr(plan, "scene", "")),
                    video_prompt=string_value(getattr(plan, "video_prompt", "")),
                    image_prompt=string_value(getattr(plan, "image_prompt", "")),
                    first_frame_prompt=string_value(getattr(plan, "first_frame_prompt", "")),
                    last_frame_prompt=string_value(getattr(plan, "last_frame_prompt", "")),
                    motion=string_value(getattr(plan, "motion", "")),
                    camera_movement=string_value(getattr(plan, "camera_movement", "")),
                    duration_hint=string_value(getattr(plan, "duration_hint", "")),
                )
            )
        return plans

    def extract_character_definitions(self, storyboard_markdown: str) -> list[Any]:
        return self._planner.extract_character_definitions(storyboard_markdown)

    def resolve_requested_output_count(self, task: TaskRecord, storyboard_clip_count: int) -> int:
        return self._planner.resolve_requested_output_count(task, storyboard_clip_count)

    def extract_storyboard_shot_duration_ranges(self, storyboard_markdown: str) -> list[list[int]]:
        return self._planner.extract_storyboard_shot_duration_ranges(storyboard_markdown)

    def build_clip_duration_plan(
        self, task: TaskRecord, duration_seconds: int, clip_count: int, storyboard_markdown: str
    ) -> list[list[int]]:
        return self._planner.build_clip_duration_plan(task, duration_seconds, clip_count, storyboard_markdown)

    def normalize_clip_duration_plan(self, video_model: str, plan: list[list[int]]) -> list[list[int]]:
        return self._planner.normalize_clip_duration_plan(video_model, plan)

    def request_snapshot_output_count(self, task: TaskRecord) -> Any:
        return self._planner.request_snapshot_output_count(task)

    def build_clip_duration_plan_context(
        self, plan: list[list[int]], ranges: list[list[int]]
    ) -> list[dict[str, Any]]:
        return self._planner.build_clip_duration_plan_context(plan, ranges)
