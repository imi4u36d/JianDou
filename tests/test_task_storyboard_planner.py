from __future__ import annotations

import pytest

from backend.domain.task_storyboard_planner import TaskStoryboardPlanner

pytestmark = pytest.mark.service


class _Resolver:
    def section(self, path: str) -> dict[str, str]:
        assert path == 'model.models."agnes-video-v2.0"'
        return {"supported_durations": "4,5,6,8,10,12"}


def test_normalize_clip_duration_plan_caps_agnes_to_provider_frame_limit() -> None:
    planner = TaskStoryboardPlanner(model_resolver=_Resolver())

    normalized = planner.normalize_clip_duration_plan(
        "agnes-video-v2.0",
        [[10, 10, 10]],
    )

    assert normalized == [[6, 6, 6]]


def test_normalize_clip_duration_plan_caps_agnes_without_resolver() -> None:
    planner = TaskStoryboardPlanner()

    normalized = planner.normalize_clip_duration_plan(
        "agnes-video-v2.0",
        [[10, 10, 10]],
    )

    assert normalized == [[6, 6, 6]]
