from __future__ import annotations

import pytest

from backend.domain.task_storyboard_planner import ShotPlan as FacadeShotPlan
from backend.domain.task_storyboard_shots import ShotPlan, StoryboardShotPlanParser


def test_shot_parser_builds_continuous_clip_prompts() -> None:
    parser = StoryboardShotPlanParser()
    markdown = """
【分镜脚本】
| 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
| --- | --- | --- | --- | --- |
| 1 | 门外 | 门内 | 推镜进入房间 | 6秒 |
| 2 | 旧首帧 | 窗前 | 角色走到窗边 | 8秒 |
"""

    plans = parser.parse(markdown)

    assert FacadeShotPlan is ShotPlan
    assert plans[0].camera_movement == "推镜进入房间"
    assert plans[1].first_frame_prompt == "门内"
    assert plans[1].image_prompt == ""
    assert "首帧：门内" in plans[1].video_prompt


def test_shot_parser_reports_missing_required_columns() -> None:
    with pytest.raises(ValueError, match="缺少必填列"):
        StoryboardShotPlanParser().parse(
            "| 镜号 | 首帧描述 | 尾帧描述 |\n| --- | --- | --- |\n| 1 | A | B |"
        )
