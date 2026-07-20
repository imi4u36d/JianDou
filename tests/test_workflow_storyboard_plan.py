from __future__ import annotations

import pytest

pytestmark = pytest.mark.domain
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown


def test_parse_workflow_storyboard_markdown_extracts_characters_and_clips() -> None:
    markdown = """
## 角色定义
| 角色 | 外观 | 性格 |
| --- | --- | --- |
| 阿宁 | 红色外套<br/>短发 | 冷静\\|敏锐 |

## 分镜脚本
| 镜号 | 起始画面 | 结束画面 | 场景 | 时长 |
| --- | --- | --- | --- | --- |
| 1 | 阿宁推门 | 灯光亮起 | 旧仓库 | 6秒 |
| 2 | 她回头 | 镜头拉远 | 走廊 | 8-10s |
"""

    plan = parse_workflow_storyboard_markdown(markdown)
    characters, clips = plan.to_view()

    assert characters == [
        {
            "name": "阿宁",
            "appearance": "外观: 红色外套 短发；性格: 冷静|敏锐",
            "summary": "外观: 红色外套 短发；性格: 冷静|敏锐",
        }
    ]
    assert clips[0]["clipIndex"] == 1
    assert clips[0]["shotLabel"] == "镜头 1"
    assert clips[0]["targetDurationSeconds"] == 6
    assert clips[1]["clipIndex"] == 2
    assert clips[1]["durationHint"] == "8-10s"
    assert clips[1]["targetDurationSeconds"] == 8


def test_parse_workflow_storyboard_markdown_handles_empty_input() -> None:
    plan = parse_workflow_storyboard_markdown("")

    assert plan.characters == []
    assert plan.clips == []
    assert plan.visual_assets == []


def test_parse_workflow_storyboard_markdown_extracts_public_visual_assets() -> None:
    markdown = """
【公共素材定义】
| 素材类型 | 素材名称 | 视觉描述 | 一致性锚点 |
| --- | --- | --- | --- |
| 道具 | 铜钥匙 | 三齿旧铜钥匙 | 红绳始终系在圆环上 |
| 建筑 | 钟楼 | 灰色石砌哥特钟楼 | 东侧拱门和破裂钟面 |
| 角色 | 阿宁 | 黑色短发，红色外套 | 左眉尾小痣 |

【分镜脚本】
| 镜号 | 首帧描述 (Start Frame) | 尾帧描述 (End Frame) | 分镜内容描述 | 时长 |
| --- | --- | --- | --- | --- |
| 001 | 阿宁站在钟楼前握着铜钥匙 | 阿宁推开东侧拱门 | 镜头缓慢推近 | 6秒 |
"""

    plan = parse_workflow_storyboard_markdown(markdown)

    assert [asset.asset_type for asset in plan.visual_assets] == ["character", "prop", "building"]
    assert [asset.name for asset in plan.visual_assets] == ["阿宁", "铜钥匙", "钟楼"]
    assert plan.characters[0].name == "阿宁"
    assert "红绳" in plan.visual_assets[1].description
