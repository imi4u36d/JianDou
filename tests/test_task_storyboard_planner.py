from __future__ import annotations

from types import SimpleNamespace

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


def test_build_storyboard_shot_plans_skips_markdown_separator_rows() -> None:
    planner = TaskStoryboardPlanner()
    storyboard = """
【角色定义信息】
| 角色 | 性别年龄 | 人物定位 | 脸部五官 | 发型 | 体型身高 | 服装 | 稳定穿戴配饰 | 不可变视觉锚点 | 行为气质 | 说话风格 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 老周 | 男，68岁 | 社区药箱管理员 | 眉骨高、眼角皱纹深 | 灰白短发 | 微驼背 | 深蓝雨衣 | 旧帆布挎包 | 右手虎口有旧疤 | 沉稳 | 话少 |

【分镜脚本】
| 镜号 | 首帧描述 StartFrame | 尾帧描述 EndFrame | 分镜内容描述 | 时长 |
| :--- | :--- | :--- | :--- | :--- |
| 001 | 暴雨夜，老周站在楼道口 | 老周打开社区药箱 | 老周在雨声里确认药品清单 | 5-6秒 |
| 002 | 药箱抽屉特写 | 老周把药递给邻居 | 邻居接过药后松一口气 | 5-6秒 |
"""

    plans = planner.build_storyboard_shot_plans(object(), storyboard)

    assert [plan.shot_label for plan in plans] == ["001", "002"]
    assert all(":---" not in plan.scene for plan in plans)
    assert "性别年龄" in plans[0].first_frame_prompt


def test_duration_planner_parses_storyboard_ranges_and_distributes_remaining_clips() -> None:
    planner = TaskStoryboardPlanner()
    storyboard = """
【分镜脚本】
| 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
| --- | --- | --- | --- | --- |
| 001 | 门外 | 门内 | 推门进入 | 5-6秒 |
| 002 | 桌前 | 窗边 | 起身走动 | 7秒 |
"""
    task = SimpleNamespace(min_duration_seconds=18, max_duration_seconds=24)

    ranges = planner.extract_storyboard_shot_duration_ranges(storyboard)
    plan = planner.build_clip_duration_plan(task, 20, 3, storyboard)

    assert ranges == [[5, 6], [7, 7]]
    assert plan == [[5, 5, 6], [7, 7, 7], [8, 6, 11]]


def test_character_parser_prefers_list_definitions_and_extracts_appearance_anchor() -> None:
    planner = TaskStoryboardPlanner()
    storyboard = """
【角色定义信息】
- 林医生：外观锚点：短黑发、白大褂、银框眼镜；人物定位：急诊医生

【分镜脚本】
| 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
| --- | --- | --- | --- | --- |
"""

    definitions = planner.extract_character_definitions(storyboard)

    assert [(item.name, item.appearance) for item in definitions] == [("林医生", "短黑发、白大褂、银框眼镜")]
    assert "人物定位" in definitions[0].definition


def test_planner_exposes_public_visual_assets_and_keeps_character_projection() -> None:
    planner = TaskStoryboardPlanner()
    storyboard = """
【公共素材定义】
| 素材类型 | 素材名称 | 视觉描述 | 一致性锚点 |
| --- | --- | --- | --- |
| 角色 | 林医生 | 短黑发、白大褂 | 银框眼镜 |
| 道具 | 急救箱 | 红色硬壳箱 | 白色十字标志 |
| 建筑 | 急诊楼 | 白色三层建筑 | 红色雨棚入口 |

【分镜脚本】
| 镜号 | 首帧描述 | 尾帧描述 | 分镜内容描述 | 时长 |
| --- | --- | --- | --- | --- |
"""

    assets = planner.extract_visual_asset_definitions(storyboard)
    characters = planner.extract_character_definitions(storyboard)

    assert [asset["assetType"] for asset in assets] == ["character", "prop", "building"]
    assert characters[0].name == "林医生"
