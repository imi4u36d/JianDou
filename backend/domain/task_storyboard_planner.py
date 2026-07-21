"""Public storyboard planning facade for task execution."""

from __future__ import annotations

from typing import Any

from backend.domain.task_storyboard_characters import CharacterDefinition, StoryboardCharacterParser
from backend.domain.task_storyboard_duration import StoryboardDurationPlanner
from backend.domain.task_storyboard_shots import ShotPlan, StoryboardShotPlanParser, string_value
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown

__all__ = ["ShotPlan", "TaskStoryboardPlanner", "string_value"]


class TaskStoryboardPlanner:
    """Compose shot parsing, character extraction, and duration planning."""

    def __init__(self, model_resolver: Any = None) -> None:
        self._model_resolver = model_resolver
        self._character_parser = StoryboardCharacterParser()
        self._shot_parser = StoryboardShotPlanParser(self._character_parser)
        self._duration_planner = StoryboardDurationPlanner(self._shot_parser, model_resolver)

    def build_sequential_clip_prompts(self, task: Any, storyboard_markdown: str) -> list[str]:
        return [plan.video_prompt for plan in self.build_storyboard_shot_plans(task, storyboard_markdown)]

    def build_storyboard_shot_plans(self, task: Any, storyboard_markdown: str) -> list[ShotPlan]:
        return self._shot_parser.parse(storyboard_markdown)

    def build_storyboard_video_prompts(self, storyboard_markdown: str) -> list[str]:
        return [plan.video_prompt for plan in self._shot_parser.parse(storyboard_markdown)]

    def extract_character_definitions(self, storyboard_markdown: str) -> list[CharacterDefinition]:
        return self._character_parser.extract_character_definitions(storyboard_markdown)

    def extract_visual_asset_definitions(self, storyboard_markdown: str) -> list[dict[str, Any]]:
        """Return all reusable visual entities discovered during storyboard analysis."""
        return parse_workflow_storyboard_markdown(storyboard_markdown).visual_assets_view()

    def resolve_requested_output_count(self, task: Any, storyboard_clip_count: int) -> int:
        available = max(1, storyboard_clip_count)
        snapshot = getattr(task, "request_snapshot", None) or {}
        output_count = snapshot.get("outputCount", {}) if isinstance(snapshot, dict) else {}
        if not output_count or output_count.get("auto", False):
            return available
        requested = output_count.get("count")
        return available if requested is None else max(1, min(int(requested), available))

    def request_snapshot_output_count(self, task: Any) -> Any:
        snapshot = getattr(task, "request_snapshot", None) or {}
        output_count = snapshot.get("outputCount", {}) if isinstance(snapshot, dict) else {}
        if not output_count:
            return "auto"
        return output_count.get("auto", True) or output_count.get("count", 1)

    def build_clip_duration_plan_context(
        self,
        clip_duration_plan: list[list[int]],
        storyboard_duration_ranges: list[list[int]],
    ) -> list[dict[str, Any]]:
        return self._duration_planner.build_clip_duration_plan_context(
            clip_duration_plan,
            storyboard_duration_ranges,
        )

    def build_clip_duration_plan(
        self,
        task: Any,
        default_duration_seconds: int,
        clip_count: int,
        storyboard_markdown: str,
    ) -> list[list[int]]:
        return self._duration_planner.build_clip_duration_plan(
            task,
            default_duration_seconds,
            clip_count,
            storyboard_markdown,
        )

    def normalize_clip_duration_plan(
        self,
        requested_video_model: str,
        clip_duration_plan: list[list[int]],
    ) -> list[list[int]]:
        return self._duration_planner.normalize_clip_duration_plan(
            requested_video_model, clip_duration_plan
        )

    def extract_storyboard_shot_duration_ranges(
        self, storyboard_markdown: str
    ) -> list[list[int]]:
        return self._duration_planner.extract_storyboard_shot_duration_ranges(storyboard_markdown)

    def _extract_storyboard_shot_plans(self, storyboard_markdown: str) -> list[ShotPlan]:
        """Compatibility seam for existing internal callers."""
        return self._shot_parser.parse(storyboard_markdown)
