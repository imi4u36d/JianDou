from __future__ import annotations

import pytest

from backend.services.task_execution_prompt_support import (
    append_aspect_ratio_instruction,
    build_character_sheet_prompt,
    build_video_clip_execution_prompt,
    build_workspace_image_prompt,
)

pytestmark = pytest.mark.service


def test_character_sheet_prompts_share_the_same_generation_requirements() -> None:
    character_prompt = build_character_sheet_prompt("林", "短发，蓝色外套")
    workspace_prompt = build_workspace_image_prompt("character_sheet", "角色素材", "短发", True)

    for requirement in ("正面、侧面、背面", "完整从头到脚全身像", "禁止手拿"):
        assert requirement in character_prompt
        assert requirement in workspace_prompt
    assert "严格沿用参考图" in workspace_prompt


def test_free_workspace_prompt_is_not_decorated() -> None:
    assert build_workspace_image_prompt("free", "ignored", " original prompt ", False) == "original prompt"


def test_aspect_ratio_instruction_uses_known_resolution_and_skips_auto() -> None:
    assert append_aspect_ratio_instruction("prompt", "智能") == "prompt"
    decorated = append_aspect_ratio_instruction("prompt", "3:2")
    assert "画面比例：3:2" in decorated
    assert "3504x2336" in decorated


def test_video_prompt_is_normalized_and_bounded() -> None:
    prompt = build_video_clip_execution_prompt("line\n" * 800)
    assert "\n" not in prompt
    assert len(prompt) == 2203
    assert prompt.endswith("...")
