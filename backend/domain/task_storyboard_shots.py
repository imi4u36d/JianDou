"""Structured storyboard table parsing and shot prompt construction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.domain.task_storyboard_characters import StoryboardCharacterParser


@dataclass(frozen=True)
class ShotPlan:
    sequential_index: int = 0
    shot_label: str = ""
    scene: str = ""
    first_frame_prompt: str = ""
    last_frame_prompt: str = ""
    motion: str = ""
    camera_movement: str = ""
    duration_hint: str = ""
    image_prompt: str = ""
    video_prompt: str = ""

    def start_frame_prompt(self) -> str:
        return self.first_frame_prompt

    def end_frame_prompt(self) -> str:
        return self.last_frame_prompt

    def action_path(self) -> str:
        return self.motion


@dataclass
class StoryboardTableSchema:
    header_cells: list[str] = field(default_factory=list)
    shot_no_index: int | None = None
    first_frame_prompt_index: int | None = None
    last_frame_prompt_index: int | None = None
    content_description_index: int | None = None
    duration_index: int | None = None

    @staticmethod
    def empty() -> StoryboardTableSchema:
        return StoryboardTableSchema()

    @staticmethod
    def from_header(headers: list[str]) -> StoryboardTableSchema:
        return StoryboardTableSchema(
            header_cells=list(headers),
            shot_no_index=_resolve_header(headers, "镜号"),
            first_frame_prompt_index=_resolve_header(
                headers, "首帧描述startframe", "首帧描述", "startframe"
            ),
            last_frame_prompt_index=_resolve_header(
                headers, "尾帧描述endframe", "尾帧描述", "endframe"
            ),
            content_description_index=_resolve_header(headers, "分镜内容描述"),
            duration_index=_resolve_header(headers, "时长", "duration"),
        )

    def missing_structured_required_columns(self) -> list[str]:
        columns = [
            (self.shot_no_index, "镜号"),
            (self.first_frame_prompt_index, "首帧描述"),
            (self.last_frame_prompt_index, "尾帧描述"),
            (self.content_description_index, "分镜内容描述"),
            (self.duration_index, "时长"),
        ]
        return [label for index, label in columns if index is None]

    def is_header_row(self, cells: list[str]) -> bool:
        return bool(self.header_cells) and len(cells) == len(self.header_cells) and all(
            cell.strip().lower() == self.header_cells[index].strip().lower()
            for index, cell in enumerate(cells)
        )

    @staticmethod
    def cell(cells: list[str], index: int | None, fallback_index: int) -> str:
        resolved = index if index is not None else fallback_index
        return cells[resolved] if 0 <= resolved < len(cells) else ""


def string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_header(text: str) -> str:
    return (
        string_value(text)
        .lower()
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
        .strip()
    )


def _normalize_storyboard_header(text: str) -> str:
    return re.sub(r"[\s_\-()（）/\\+:：·,.，]", "", string_value(text).lower().strip())


def _normalize_prompt_value(value: str) -> str:
    result = (
        string_value(value)
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
    )
    return re.sub(r"\s+", " ", result).strip()


def _resolve_header(headers: list[str], *aliases: str) -> int | None:
    return next(
        (
            index
            for index, header in enumerate(headers)
            if any(_normalize_header(alias) in _normalize_header(header) for alias in aliases)
        ),
        None,
    )


class StoryboardShotPlanParser:
    """Translate the structured storyboard Markdown section into shot plans."""

    def __init__(self, character_parser: StoryboardCharacterParser | None = None) -> None:
        self._character_parser = character_parser or StoryboardCharacterParser()

    def parse(self, storyboard_markdown: str) -> list[ShotPlan]:
        normalized = string_value(storyboard_markdown)
        if not normalized:
            raise ValueError("分镜解析失败，分镜脚本不能为空，且必须是结构化 Markdown 表格。")
        character_appearances = self._extract_character_appearance_map(normalized)
        lines = self._storyboard_section(normalized).splitlines()
        schema = self._detect_storyboard_table_schema(lines)
        self._validate_structured_storyboard_schema(schema)

        shot_plans: list[ShotPlan] = []
        previous_last_frame_prompt = ""
        for raw_line in lines:
            cells = self._storyboard_cells(raw_line, schema)
            if cells is None:
                continue
            shot_label = _normalize_prompt_value(schema.cell(cells, schema.shot_no_index, 0))
            if not shot_label or "镜号" in shot_label or "shot" in shot_label.lower():
                continue
            sequential_index = len(shot_plans) + 1
            duration_hint = _normalize_prompt_value(schema.cell(cells, schema.duration_index, -1))
            parsed_first_frame = self._augment_character_appearances(
                _normalize_prompt_value(schema.cell(cells, schema.first_frame_prompt_index, -1)),
                character_appearances,
            )
            last_frame = self._augment_character_appearances(
                _normalize_prompt_value(schema.cell(cells, schema.last_frame_prompt_index, -1)),
                character_appearances,
            )
            content = _normalize_prompt_value(
                schema.cell(cells, schema.content_description_index, -1)
            )
            camera_movement = self._extract_camera_movement(content) or "static"
            self._assert_structured_row(
                shot_label, parsed_first_frame, last_frame, content, duration_hint
            )
            first_frame = (
                previous_last_frame_prompt
                if sequential_index > 1 and previous_last_frame_prompt
                else parsed_first_frame
            )
            shot_plans.append(
                ShotPlan(
                    sequential_index=sequential_index,
                    shot_label=shot_label,
                    scene=self.first_non_blank(first_frame, parsed_first_frame, last_frame),
                    first_frame_prompt=first_frame,
                    last_frame_prompt=last_frame,
                    motion=content,
                    camera_movement=camera_movement,
                    duration_hint=duration_hint,
                    image_prompt=first_frame if sequential_index == 1 else "",
                    video_prompt=self._build_continuous_clip_prompt(
                        first_frame, last_frame, content, camera_movement, duration_hint
                    ),
                )
            )
            previous_last_frame_prompt = last_frame
        if not shot_plans:
            raise ValueError("分镜解析失败，结构化分镜表未生成有效镜头。")
        return shot_plans

    def _storyboard_cells(
        self, raw_line: str, schema: StoryboardTableSchema
    ) -> list[str] | None:
        stripped = raw_line.strip()
        if not stripped.startswith("|"):
            return None
        cells = self._split_table_row(stripped)
        if len(cells) < 2 or self._is_divider_row(cells) or schema.is_header_row(cells):
            return None
        return cells

    @staticmethod
    def _validate_structured_storyboard_schema(schema: StoryboardTableSchema) -> None:
        if not schema.header_cells:
            raise ValueError(
                "分镜解析失败，必须提供结构化 Markdown 分镜表，"
                "表头需包含：镜号、首帧描述、尾帧描述、分镜内容描述、时长。"
            )
        missing = schema.missing_structured_required_columns()
        if missing:
            raise ValueError("分镜解析失败，结构化分镜表缺少必填列：" + "、".join(missing))

    @staticmethod
    def _assert_structured_row(
        shot_label: str,
        first_frame: str,
        last_frame: str,
        content: str,
        duration_hint: str,
    ) -> None:
        values = [
            (shot_label, "镜号"),
            (first_frame, "首帧描述"),
            (last_frame, "尾帧描述"),
            (content, "分镜内容描述"),
            (duration_hint, "时长"),
        ]
        missing = [label for value, label in values if not _normalize_prompt_value(value)]
        if missing:
            raise ValueError(f"分镜解析失败，镜头 {shot_label} 缺少必填字段：" + "、".join(missing))

    def _extract_character_appearance_map(self, markdown: str) -> dict[str, str]:
        return {
            definition.name: definition.appearance
            for definition in self._character_parser.extract_character_definitions(markdown)
            if definition.name and definition.appearance
        }

    @staticmethod
    def _augment_character_appearances(prompt: str, appearances: dict[str, str]) -> str:
        augmented = _normalize_prompt_value(prompt)
        if not augmented:
            return augmented
        for name, appearance in sorted(appearances.items(), key=lambda item: len(item[0]), reverse=True):
            character = _normalize_prompt_value(name)
            description = _normalize_prompt_value(appearance)
            if (
                not character
                or not description
                or character not in augmented
                or f"{character}（{description}）" in augmented
                or f"{character}({description})" in augmented
            ):
                continue
            match = re.search(re.escape(character) + r"(?!\s*[（(])", augmented)
            if match:
                augmented = (
                    augmented[: match.start()]
                    + f"{character}（{description}）"
                    + augmented[match.end() :]
                )
        return augmented

    @classmethod
    def _extract_camera_movement(cls, value: str) -> str:
        normalized = _normalize_prompt_value(value)
        if not normalized:
            return ""
        return next(
            (
                token.strip()
                for token in re.split(r"[/／+＋,，;；|｜]", normalized)
                if cls._looks_like_camera_movement(token.strip())
            ),
            normalized if cls._looks_like_camera_movement(normalized) else "",
        )

    @staticmethod
    def _looks_like_camera_movement(value: str) -> bool:
        normalized = _normalize_prompt_value(value).lower()
        keywords = [
            "推", "拉", "摇", "移", "跟", "甩", "升", "降", "环绕", "环拍", "手持",
            "dolly", "push", "pull", "pan", "tilt", "truck", "track", "orbit", "handheld", "whip",
        ]
        return bool(normalized) and any(keyword in normalized for keyword in keywords)

    @staticmethod
    def _build_continuous_clip_prompt(
        first_frame: str,
        last_frame: str,
        content: str,
        camera_movement: str,
        duration_hint: str,
    ) -> str:
        parts = []
        if first_frame:
            parts.append("首帧：" + first_frame)
        if last_frame:
            parts.append("尾帧：" + last_frame)
        if content:
            parts.append("分镜内容：" + content)
        if camera_movement and camera_movement.lower() != "static":
            parts.append("运镜关键词：" + camera_movement)
        if duration_hint:
            parts.append("时长：" + duration_hint)
        value = "；".join(parts)
        return value if len(value) <= 2200 else value[:2199].strip() + "…"

    @staticmethod
    def _storyboard_section(markdown: str) -> str:
        normalized = string_value(markdown)
        start = normalized.find("【分镜脚本】")
        return normalized[start:] if start >= 0 else normalized

    @staticmethod
    def _split_table_row(row: str) -> list[str]:
        trimmed = row.strip()
        if not trimmed.startswith("|"):
            return []
        content = trimmed[1:-1] if trimmed.endswith("|") else trimmed[1:]
        return [part.strip() for part in content.split("|")]

    def _detect_storyboard_table_schema(self, lines: list[str]) -> StoryboardTableSchema:
        for raw_line in lines:
            cells = self._split_table_row(raw_line.strip())
            if cells and not self._is_divider_row(cells) and self._looks_like_header_row(cells):
                return StoryboardTableSchema.from_header(cells)
        return StoryboardTableSchema.empty()

    @staticmethod
    def _looks_like_header_row(cells: list[str]) -> bool:
        keywords = [
            "shot", "镜号", "首帧", "尾帧", "startframe", "endframe", "分镜内容描述",
            "剧情画面与声音描述", "合并长段描述", "画面叙述", "storydescription",
            "contentdescription", "duration", "时长",
        ]
        return any(
            keyword in _normalize_storyboard_header(cell)
            for cell in cells
            for keyword in keywords
        )

    @staticmethod
    def _is_divider_row(cells: list[str]) -> bool:
        return bool(cells) and all(
            re.fullmatch(r"\s*:?-{3,}:?\s*", cell or "") is not None for cell in cells
        )

    @staticmethod
    def first_non_blank(*values: str) -> str:
        return next((value for value in values if value and value.strip()), "")
