from __future__ import annotations

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
