"""Task storyboard planner - translates storyboard markdown into shot plans.

Mirrors the Java TaskStoryboardPlanner class located in the api-spring module.
Handles parsing of storyboard markdown tables, extraction of shot information,
duration planning, character definition extraction, camera movement detection,
and prompt construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLIP_MIN_SECONDS = 5
CLIP_MAX_SECONDS = 12

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches duration ranges in storyboard text, e.g. "5-10s", "3~5秒"
_SCRIPT_DURATION_RANGE_PATTERN = re.compile(
    r"(?P<left>\d{1,3}(?:\.\d+)?)\s*(?:-|~|～|—|到)\s*(?P<right>\d{1,3}(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|秒)",
    re.IGNORECASE,
)

# Matches single duration values in storyboard text, e.g. "5s", "3秒"
_SCRIPT_DURATION_VALUE_PATTERN = re.compile(
    r"(?<![.\d])(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|秒)(?![a-zA-Z])",
    re.IGNORECASE,
)

# Matches plain duration ranges, e.g. "5-10", "3~5"
_PLAIN_DURATION_RANGE_PATTERN = re.compile(
    r"^\s*(?P<left>\d{1,3}(?:\.\d+)?)\s*(?:-|~|～|—|到)\s*(?P<right>\d{1,3}(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

# Matches plain single duration values, e.g. "5", "3"
_PLAIN_DURATION_VALUE_PATTERN = re.compile(
    r"^\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

# Matches character definition list items: "- name: definition" or "- name：definition"
_CHARACTER_DEFINITION_LIST_PATTERN = re.compile(
    r"^[-*]\s*(?P<name>[^：:|]+)[:：]\s*(?P<definition>.+)$"
)

# Matches appearance anchor within character definition
_CHARACTER_APPEARANCE_ANCHOR_PATTERN = re.compile(
    r"外观锚点[:：](?P<appearance>.*?)(?:[；;。.]\s*(?:人物定位|行为特征|说话风格)[:：]|$)"
)

# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
# =============================================================================
# STORYBOARD PLANNER
# =============================================================================
class CharacterDefinition:
    """A character definition extracted from storyboard markdown.

    Mirrors the Java ``TaskStoryboardPlanner.CharacterDefinition`` record.
    """

    name: str = ""
    appearance: str = ""
    definition: str = ""

    def __post_init__(self) -> None:
        """If definition is empty, fall back to appearance."""
        if not self.definition:
            object.__setattr__(self, "definition", self.appearance)


@dataclass(frozen=True)
class ShotPlan:
    """A single shot/clip plan from storyboard planning.

    Mirrors the Java ``TaskStoryboardPlanner.StoryboardShotPlan`` record.
    """

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

    # -- Semantic aliases matching Java record accessors ---------------------

    def start_frame_prompt(self) -> str:
        """Alias for first_frame_prompt."""
        return self.first_frame_prompt

    def end_frame_prompt(self) -> str:
        """Alias for last_frame_prompt."""
        return self.last_frame_prompt

    def action_path(self) -> str:
        """Alias for motion."""
        return self.motion


# ---------------------------------------------------------------------------
# Internal helper classes
# ---------------------------------------------------------------------------


class _CharacterDefinitionBuilder:
    """Mutable builder for CharacterDefinition.

    Mirrors the Java ``TaskStoryboardPlanner.CharacterDefinitionBuilder``
    private static class.
    """

    __slots__ = (
        "_name",
        "_single_row_definition",
        "_single_row_appearance",
        "_gender",
        "_age",
        "_parts",
    )

    def __init__(self, name: str) -> None:
        self._name = name
        self._single_row_definition = ""
        self._single_row_appearance = ""
        self._gender = ""
        self._age = ""
        self._parts: dict[str, str] = {}

    # -- Factory for single-row schema ---------------------------------------

    @staticmethod
    def from_single_row(
        name: str,
        gender_age: str,
        position: str,
        face: str,
        hair: str,
        body: str,
        clothing: str,
        stable_accessories: str,
        immutable_visual: str,
        appearance: str,
        behavior: str,
        speech: str,
    ) -> _CharacterDefinitionBuilder:
        builder = _CharacterDefinitionBuilder(name)
        builder._single_row_appearance = _join_labeled_known_values(
            ("性别年龄", gender_age),
            ("脸部五官", face),
            ("发型", hair),
            ("体型身高", body),
            ("服装", clothing),
            ("稳定穿戴配饰", stable_accessories),
            ("不可变视觉锚点", _first_known_value(immutable_visual, appearance)),
        )
        if not builder._single_row_appearance:
            builder._single_row_appearance = _trim_static_appearance_definition(appearance)

        chunks: list[str] = []
        if _has_known_value(gender_age):
            chunks.append("性别年龄：" + _trim_static_appearance_definition(gender_age))
        if _has_known_value(position):
            chunks.append("人物定位：" + _trim_static_appearance_definition(position))
        _add_known_chunk(chunks, "脸部五官", face)
        _add_known_chunk(chunks, "发型", hair)
        _add_known_chunk(chunks, "体型身高", body)
        _add_known_chunk(chunks, "服装", clothing)
        _add_known_chunk(chunks, "稳定穿戴配饰", stable_accessories)
        _add_known_chunk(chunks, "不可变视觉锚点", immutable_visual)
        if _has_known_value(appearance):
            chunks.append("外观锚点：" + _trim_static_appearance_definition(appearance))
        if _has_known_value(behavior):
            chunks.append("行为气质：" + _trim_static_appearance_definition(behavior))
        if _has_known_value(speech):
            chunks.append("说话风格：" + _trim_static_appearance_definition(speech))
        builder._single_row_definition = "；".join(chunks)
        return builder

    # -- Mutators for multi-row schema ---------------------------------------

    def set_gender(self, value: str) -> None:
        if not self._gender and value:
            self._gender = value

    def set_age(self, value: str) -> None:
        if not self._age and value:
            self._age = value

    def add_part(self, part: str, detail: str) -> None:
        p = part.strip() if part else ""
        d = detail.strip() if detail else ""
        if p and d:
            self._parts[p] = d

    # -- Build ---------------------------------------------------------------

    def build(self) -> CharacterDefinition:
        if self._single_row_appearance:
            return CharacterDefinition(self._name, self._single_row_appearance, self._single_row_definition)
        chunks: list[str] = []
        if self._gender:
            chunks.append("性别：" + self._gender)
        if self._age:
            chunks.append("年龄：" + self._age)
        for key, val in self._parts.items():
            chunks.append(f"{key}：{val}")
        definition = "；".join(chunks)
        return CharacterDefinition(self._name, definition, definition)


@dataclass
class _CharacterDefinitionTableSchema:
    """Schema for a character definition markdown table.

    Mirrors the Java ``TaskStoryboardPlanner.CharacterDefinitionTableSchema``
    private record.
    """

    header_cells: list[str] = field(default_factory=list)
    name_index: int | None = None
    gender_age_index: int | None = None
    position_index: int | None = None
    appearance_index: int | None = None
    face_index: int | None = None
    hair_index: int | None = None
    body_index: int | None = None
    clothing_index: int | None = None
    stable_accessories_index: int | None = None
    immutable_visual_index: int | None = None
    behavior_index: int | None = None
    speech_index: int | None = None
    gender_index: int | None = None
    age_index: int | None = None
    part_index: int | None = None
    detail_index: int | None = None

    @staticmethod
    def empty() -> _CharacterDefinitionTableSchema:
        return _CharacterDefinitionTableSchema()

    @staticmethod
    def from_header(headers: list[str]) -> _CharacterDefinitionTableSchema:
        return _CharacterDefinitionTableSchema(
            header_cells=list(headers),
            name_index=_resolve_header(headers, "角色", "姓名", "名称"),
            gender_age_index=_resolve_header(headers, "性别年龄", "性别与年龄", "年龄性别"),
            position_index=_resolve_header(headers, "人物定位"),
            appearance_index=_resolve_header(headers, "外观锚点", "外观定义", "外形定义", "人物外观"),
            face_index=_resolve_header(headers, "脸部五官", "脸部", "五官", "面部特征"),
            hair_index=_resolve_header(headers, "发型"),
            body_index=_resolve_header(headers, "体型身高", "身高体型", "体型", "身高"),
            clothing_index=_resolve_header(headers, "服装", "着装", "衣着"),
            stable_accessories_index=_resolve_header(
                headers, "稳定穿戴配饰", "固定穿戴配饰", "稳定配饰", "穿戴配饰", "配饰"
            ),
            immutable_visual_index=_resolve_header(headers, "不可变视觉锚点", "固定视觉锚点", "视觉锚点"),
            behavior_index=_resolve_header(headers, "行为气质", "行为特征", "气质"),
            speech_index=_resolve_header(headers, "说话风格"),
            gender_index=_resolve_header(headers, "性别"),
            age_index=_resolve_header(headers, "年龄"),
            part_index=_resolve_header(headers, "部位"),
            detail_index=_resolve_header(headers, "详细描述", "描述"),
        )

    @staticmethod
    def looks_like_header(cells: list[str]) -> bool:
        has_name = False
        has_appearance = False
        has_detailed_visual = False
        has_legacy_part = False
        has_legacy_detail = False
        for cell in cells:
            norm = _normalize_header(cell)
            has_name = has_name or _contains_any(norm, "角色", "姓名", "名称")
            has_appearance = has_appearance or _contains_any(norm, "外观锚点", "外观定义", "外形定义")
            has_detailed_visual = has_detailed_visual or _contains_any(
                norm, "脸部五官", "发型", "体型身高", "服装", "不可变视觉锚点"
            )
            has_legacy_part = has_legacy_part or _contains_any(norm, "部位")
            has_legacy_detail = has_legacy_detail or _contains_any(norm, "详细描述", "描述")
        return has_name and (has_appearance or has_detailed_visual or (has_legacy_part and has_legacy_detail))

    def is_valid(self) -> bool:
        return self.is_single_row_schema() or (
            self.name_index is not None
            and self.gender_index is not None
            and self.age_index is not None
            and self.part_index is not None
            and self.detail_index is not None
        )

    def is_single_row_schema(self) -> bool:
        return (
            self.name_index is not None
            and self.position_index is not None
            and self.behavior_index is not None
            and self.speech_index is not None
            and (
                self.appearance_index is not None
                or self.face_index is not None
                or self.hair_index is not None
                or self.body_index is not None
                or self.clothing_index is not None
                or self.immutable_visual_index is not None
            )
        )

    def is_header_row(self, cells: list[str]) -> bool:
        if not self.header_cells or len(cells) != len(self.header_cells):
            return False
        for i, cell in enumerate(cells):
            if _normalize_header(cell) != _normalize_header(self.header_cells[i]):
                return False
        return True

    def value(self, cells: list[str], index: int | None) -> str:
        if index is None or index < 0 or index >= len(cells):
            return ""
        return cells[index]


@dataclass
class _StoryboardTableSchema:
    """Schema for a storyboard markdown table.

    Mirrors the Java ``TaskStoryboardPlanner.StoryboardTableSchema`` private record.
    """

    header_cells: list[str] = field(default_factory=list)
    shot_no_index: int | None = None
    first_frame_prompt_index: int | None = None
    last_frame_prompt_index: int | None = None
    content_description_index: int | None = None
    duration_index: int | None = None

    @staticmethod
    def empty() -> _StoryboardTableSchema:
        return _StoryboardTableSchema()

    @staticmethod
    def from_header(headers: list[str]) -> _StoryboardTableSchema:
        return _StoryboardTableSchema(
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
        missing: list[str] = []
        if self.shot_no_index is None:
            missing.append("镜号")
        if self.first_frame_prompt_index is None:
            missing.append("首帧描述")
        if self.last_frame_prompt_index is None:
            missing.append("尾帧描述")
        if self.content_description_index is None:
            missing.append("分镜内容描述")
        if self.duration_index is None:
            missing.append("时长")
        return missing

    def is_header_row(self, cells: list[str]) -> bool:
        if not self.header_cells or len(cells) != len(self.header_cells):
            return False
        for i, cell in enumerate(cells):
            if cell.strip().lower() != self.header_cells[i].strip().lower():
                return False
        return True

    def cell(self, cells: list[str], index: int | None, fallback_index: int) -> str:
        resolved = index if index is not None else fallback_index
        if resolved < 0 or resolved >= len(cells):
            return ""
        return cells[resolved]


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------


def string_value(value: Any) -> str:
    """Safely convert a value to a trimmed string."""
    if value is None:
        return ""
    return str(value).strip()


def _normalize_header(text: str) -> str:
    """Normalize a header cell for comparison (stripped, lowercased, no separators)."""
    return (
        string_value(text)
        .lower()
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
        .strip()
    )


def _normalize_storyboard_header(text: str) -> str:
    """Normalize storyboard header text by removing whitespace and separators."""
    return re.sub(r"[\s_\-()（）/\\+:：·,.，]", "", string_value(text).lower().strip())


def _normalize_storyboard_prompt_value(value: str) -> str:
    """Normalize a storyboard prompt cell value."""
    return (
        string_value(value)
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
    )


def _normalize_prompt_value(value: str) -> str:
    """Normalize a storyboard prompt cell value (replace <br> with space, collapse whitespace)."""
    result = (
        string_value(value)
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
    )
    return re.sub(r"\s+", " ", result).strip()


def _trim_appearance_definition(value: str) -> str:
    """Remove trailing punctuation from appearance definitions."""
    return re.sub(r"[。；;，,]+$", "", _normalize_prompt_value(value)).strip()


def _trim_static_appearance_definition(value: str) -> str:
    """Static version of trim_appearance_definition."""
    if value is None:
        return ""
    result = (
        str(value)
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
    )
    result = re.sub(r"\s+", " ", result)
    result = re.sub(r"[。；;，,]+$", "", result)
    return result.strip()


def _resolve_header(headers: list[str], *aliases: str) -> int | None:
    """Find the index of a header matching any of the given aliases."""
    for idx, header in enumerate(headers):
        norm = _normalize_header(header)
        for alias in aliases:
            if _normalize_header(alias) in norm:
                return idx
    return None


def _contains_any(text: str, *values: str) -> bool:
    """Check if text contains any of the given values."""
    for v in values:
        if v in text:
            return True
    return False


def _has_known_value(value: str) -> bool:
    """Check if a value is non-blank and not a known 'unknown' marker."""
    normalized = _trim_static_appearance_definition(value)
    if not normalized:
        return False
    return normalized not in ("未明确", "不明确", "未知", "无", "无明确")


def _has_any_known_value(*values: str) -> bool:
    """Check if any of the given values has known content."""
    for v in values:
        if _has_known_value(v):
            return True
    return False


def _first_known_value(*values: str) -> str:
    """Return the first value that has known content."""
    for v in values:
        if _has_known_value(v):
            return _trim_static_appearance_definition(v)
    return ""


def _add_known_chunk(chunks: list[str], label: str, value: str) -> None:
    """Append a labeled chunk if the value has known content."""
    if _has_known_value(value):
        chunks.append(f"{label}：{_trim_static_appearance_definition(value)}")


def _join_labeled_known_values(*label_value_pairs: tuple[str, str]) -> str:
    """Join labeled values that have known content with '；'."""
    chunks: list[str] = []
    for label, value in label_value_pairs:
        if _has_known_value(value):
            chunks.append(f"{label}：{_trim_static_appearance_definition(value)}")
    return "；".join(chunks)


# ---------------------------------------------------------------------------
# Main planner class
# ---------------------------------------------------------------------------


class TaskStoryboardPlanner:
    """Plans storyboard shots from task requests.

    Mirrors the Java ``TaskStoryboardPlanner`` service class.

    Parameters
    ----------
    model_resolver:
        An optional callable/object used to resolve model runtime properties.
        If provided, it should expose a ``section(path: str) -> dict[str, str]``
        method (e.g., a config resolver).
    """

    def __init__(self, model_resolver: Any = None) -> None:
        self._model_resolver = model_resolver

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def build_sequential_clip_prompts(
        self, task: Any, storyboard_markdown: str
    ) -> list[str]:
        """Build sequential clip prompts from storyboard markdown."""
        return [
            plan.video_prompt
            for plan in self.build_storyboard_shot_plans(task, storyboard_markdown)
        ]

    def build_storyboard_shot_plans(
        self, task: Any, storyboard_markdown: str
    ) -> list[ShotPlan]:
        """Parse storyboard markdown and build shot plans."""
        return self._extract_storyboard_shot_plans(storyboard_markdown)

    def build_storyboard_video_prompts(self, storyboard_markdown: str) -> list[str]:
        """Build video prompts from storyboard markdown only (no task)."""
        return [
            plan.video_prompt
            for plan in self._extract_storyboard_shot_plans(storyboard_markdown)
        ]

    # -----------------------------------------------------------------------
    # Character definitions
    # -----------------------------------------------------------------------

    def extract_character_definitions(
        self, storyboard_markdown: str
    ) -> list[CharacterDefinition]:
        """Extract character definitions from storyboard markdown."""
        normalized = string_value(storyboard_markdown)
        if not normalized:
            return []

        definitions_start = normalized.find("【角色定义信息】")
        if definitions_start < 0:
            return []

        script_start = normalized.find("【分镜脚本】")
        definitions_block = (
            normalized[definitions_start:script_start]
            if script_start > definitions_start
            else normalized[definitions_start:]
        )

        list_definitions = self._extract_character_definitions_from_list(
            definitions_block
        )
        if list_definitions:
            return list_definitions

        return self._extract_character_definitions_from_table(definitions_block)

    # -----------------------------------------------------------------------
    # Output count
    # -----------------------------------------------------------------------

    def resolve_requested_output_count(
        self, task: Any, storyboard_clip_count: int
    ) -> int:
        """Determine how many clips to generate.

        Reads ``task.request_snapshot`` (a dict) for ``outputCount``.
        """
        available = max(1, storyboard_clip_count)
        snapshot = getattr(task, "request_snapshot", None) or {}
        output_count = snapshot.get("outputCount", {}) if isinstance(snapshot, dict) else {}
        if not output_count:
            return available
        if output_count.get("auto", False):
            return available
        requested = output_count.get("count")
        if requested is None:
            return available
        return max(1, min(int(requested), available))

    def request_snapshot_output_count(self, task: Any) -> Any:
        """Return the output count value from the task request snapshot."""
        snapshot = getattr(task, "request_snapshot", None) or {}
        output_count = snapshot.get("outputCount", {}) if isinstance(snapshot, dict) else {}
        if not output_count:
            return "auto"
        return output_count.get("auto", True) or output_count.get("count", 1)

    # -----------------------------------------------------------------------
    # Duration planning
    # -----------------------------------------------------------------------

    def build_clip_duration_plan_context(
        self,
        clip_duration_plan: list[list[int]],
        storyboard_duration_ranges: list[list[int]],
    ) -> list[dict[str, Any]]:
        """Build context rows describing clip duration plans."""
        rows: list[dict[str, Any]] = []
        for index, plan in enumerate(clip_duration_plan):
            row: dict[str, Any] = {
                "clipIndex": index + 1,
                "targetDurationSeconds": plan[0],
                "minDurationSeconds": plan[1],
                "maxDurationSeconds": plan[2],
            }
            if index < len(storyboard_duration_ranges):
                scripted = storyboard_duration_ranges[index]
                row["durationSource"] = "storyboard"
                row["scriptMinDurationSeconds"] = scripted[0]
                row["scriptMaxDurationSeconds"] = scripted[1]
            else:
                row["durationSource"] = "task_average"
            rows.append(row)
        return rows

    def build_clip_duration_plan(
        self,
        task: Any,
        default_duration_seconds: int,
        clip_count: int,
        storyboard_markdown: str,
    ) -> list[list[int]]:
        """Build clip duration distribution from task constraints and markdown."""
        normalized_clip_count = max(1, clip_count)
        total_min = max(
            1,
            task.min_duration_seconds if task.min_duration_seconds > 0 else default_duration_seconds,
        )
        total_max = max(
            total_min,
            task.max_duration_seconds if task.max_duration_seconds > 0 else default_duration_seconds,
        )

        ranges = self.extract_storyboard_shot_duration_ranges(storyboard_markdown)
        scripted_clip_count = min(len(ranges), normalized_clip_count)

        scripted_min_sum = 0
        scripted_max_sum = 0
        for i in range(scripted_clip_count):
            r = ranges[i]
            scripted_min_sum += max(1, r[0])
            scripted_max_sum += max(max(1, r[0]), r[1])

        unresolved_clip_count = max(0, normalized_clip_count - scripted_clip_count)

        if unresolved_clip_count == 0:
            global_min = CLIP_MIN_SECONDS
        else:
            global_min = max(
                1,
                round(max(unresolved_clip_count, total_min - scripted_min_sum) / unresolved_clip_count),
            )
        if unresolved_clip_count == 0:
            global_max = global_min
        else:
            global_max = max(
                global_min,
                round(max(unresolved_clip_count, total_max - scripted_max_sum) / unresolved_clip_count),
            )

        global_min = self._clamp(global_min, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
        global_max = self._clamp(global_max, global_min, CLIP_MAX_SECONDS)

        plan: list[list[int]] = []
        for index in range(normalized_clip_count):
            scripted = index < len(ranges)
            clip_min = ranges[index][0] if scripted else global_min
            clip_max = (max(clip_min, ranges[index][1]) if scripted else global_max) if scripted else global_max
            clip_min = self._clamp(clip_min, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
            clip_max = self._clamp(clip_max, clip_min, CLIP_MAX_SECONDS)
            if scripted:
                clip_target = clip_min
            else:
                clip_target = max(clip_min, min(clip_max, round((clip_min + clip_max) / 2.0)))
            clip_target = self._clamp(clip_target, clip_min, clip_max)
            plan.append([clip_target, clip_min, clip_max])

        return plan

    def normalize_clip_duration_plan(
        self,
        requested_video_model: str,
        clip_duration_plan: list[list[int]],
    ) -> list[list[int]]:
        """Normalize duration plan for specific model constraints."""
        if not clip_duration_plan:
            return []

        supported_durations = self._supported_video_durations(requested_video_model)
        if not supported_durations:
            return clip_duration_plan

        normalized: list[list[int]] = []
        for item in clip_duration_plan:
            if item is None or len(item) < 3:
                continue
            normalized.append(
                self._normalize_clip_duration_range(
                    supported_durations, item[0], item[1], item[2]
                )
            )
        return normalized

    # -----------------------------------------------------------------------
    # Duration range extraction
    # -----------------------------------------------------------------------

    def extract_storyboard_shot_duration_ranges(
        self, storyboard_markdown: str
    ) -> list[list[int]]:
        """Extract duration ranges from storyboard markdown."""
        normalized = self._storyboard_section(string_value(storyboard_markdown))
        if not normalized:
            return []

        lines = normalized.splitlines()
        schema = self._detect_storyboard_table_schema(lines)
        if not schema.header_cells or schema.missing_structured_required_columns():
            return []

        ranges: list[list[int]] = []
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped.startswith("|"):
                continue
            cells = self._split_table_row(stripped)
            if len(cells) < 2 or self._is_divider_row(cells) or schema.is_header_row(cells):
                continue
            first = schema.cell(cells, schema.shot_no_index, 0)
            if not first or "镜号" in first or "shot" in first.lower():
                continue
            duration_cell = schema.cell(cells, schema.duration_index, -1)
            parsed = self._parse_duration_range_hint(duration_cell)
            if parsed is not None:
                ranges.append(parsed)
        return ranges

    # -----------------------------------------------------------------------
    # Internal: storyboard shot plan extraction
    # -----------------------------------------------------------------------

    def _extract_storyboard_shot_plans(
        self, storyboard_markdown: str
    ) -> list[ShotPlan]:
        """Parse storyboard markdown and extract individual shot plans."""
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
            stripped = raw_line.strip()
            if not stripped.startswith("|"):
                continue
            cells = self._split_table_row(stripped)
            if len(cells) < 2 or self._is_divider_row(cells) or schema.is_header_row(cells):
                continue
            first = schema.cell(cells, schema.shot_no_index, 0)
            if not first or "镜号" in first or "shot" in first.lower():
                continue

            shot_index = _normalize_prompt_value(first)
            sequential_index = len(shot_plans) + 1
            duration_hint = _normalize_prompt_value(
                schema.cell(cells, schema.duration_index, -1)
            )
            parsed_first_frame = self._augment_character_appearance_definitions(
                _normalize_prompt_value(
                    schema.cell(cells, schema.first_frame_prompt_index, -1)
                ),
                character_appearances,
            )
            last_frame = self._augment_character_appearance_definitions(
                _normalize_prompt_value(
                    schema.cell(cells, schema.last_frame_prompt_index, -1)
                ),
                character_appearances,
            )
            content_description = _normalize_prompt_value(
                schema.cell(cells, schema.content_description_index, -1)
            )
            camera_movement = self._extract_camera_movement(content_description)
            if not camera_movement:
                camera_movement = "static"

            self._assert_structured_storyboard_row(
                shot_index, parsed_first_frame, last_frame, content_description, duration_hint
            )

            first_frame_prompt = (
                previous_last_frame_prompt
                if sequential_index > 1 and previous_last_frame_prompt
                else parsed_first_frame
            )
            scene = self.first_non_blank(first_frame_prompt, parsed_first_frame, last_frame)
            image_prompt = first_frame_prompt if sequential_index == 1 else ""
            video_prompt = self._build_continuous_clip_prompt(
                first_frame_prompt,
                last_frame,
                content_description,
                camera_movement,
                duration_hint,
            )

            shot_plans.append(
                ShotPlan(
                    sequential_index=sequential_index,
                    shot_label=shot_index,
                    scene=scene,
                    first_frame_prompt=first_frame_prompt,
                    last_frame_prompt=last_frame,
                    motion=content_description,
                    camera_movement=camera_movement,
                    duration_hint=duration_hint,
                    image_prompt=image_prompt,
                    video_prompt=video_prompt,
                )
            )
            previous_last_frame_prompt = last_frame

        if not shot_plans:
            raise ValueError("分镜解析失败，结构化分镜表未生成有效镜头。")
        return shot_plans

    # -----------------------------------------------------------------------
    # Internal: storyboard section extraction
    # -----------------------------------------------------------------------

    def _storyboard_section(self, storyboard_markdown: str) -> str:
        """Extract the 【分镜脚本】 section from markdown."""
        normalized = string_value(storyboard_markdown)
        script_start = normalized.find("【分镜脚本】")
        return normalized[script_start:] if script_start >= 0 else normalized

    # -----------------------------------------------------------------------
    # Internal: schema validation
    # -----------------------------------------------------------------------

    def _validate_structured_storyboard_schema(self, schema: _StoryboardTableSchema) -> None:
        """Validate that the storyboard table schema has required columns."""
        if not schema.header_cells:
            raise ValueError(
                "分镜解析失败，必须提供结构化 Markdown 分镜表，"
                "表头需包含：镜号、首帧描述、尾帧描述、分镜内容描述、时长。"
            )
        missing = schema.missing_structured_required_columns()
        if missing:
            raise ValueError(
                "分镜解析失败，结构化分镜表缺少必填列：" + "、".join(missing)
            )

    def _assert_structured_storyboard_row(
        self,
        shot_label: str,
        first_frame_prompt: str,
        last_frame_prompt: str,
        content_description: str,
        duration_hint: str,
    ) -> None:
        """Assert that a storyboard row has all required fields."""
        missing: list[str] = []
        if not _normalize_prompt_value(shot_label):
            missing.append("镜号")
        if not _normalize_prompt_value(first_frame_prompt):
            missing.append("首帧描述")
        if not _normalize_prompt_value(last_frame_prompt):
            missing.append("尾帧描述")
        if not _normalize_prompt_value(content_description):
            missing.append("分镜内容描述")
        if not _normalize_prompt_value(duration_hint):
            missing.append("时长")
        if missing:
            raise ValueError(
                f"分镜解析失败，镜头 {shot_label} 缺少必填字段：" + "、".join(missing)
            )

    # -----------------------------------------------------------------------
    # Internal: character definitions
    # -----------------------------------------------------------------------

    def _extract_character_definitions_from_list(
        self, definitions_block: str
    ) -> list[CharacterDefinition]:
        """Extract character definitions from a list format."""
        definitions: list[CharacterDefinition] = []
        for raw_line in string_value(definitions_block).splitlines():
            stripped = raw_line.strip()
            matcher = _CHARACTER_DEFINITION_LIST_PATTERN.match(stripped)
            if not matcher:
                continue
            name = _normalize_prompt_value(matcher.group("name"))
            definition = _normalize_prompt_value(matcher.group("definition"))
            if not name or not definition:
                continue
            definitions.append(
                CharacterDefinition(
                    name, self._extract_appearance_anchor(definition), definition
                )
            )
        return definitions

    def _extract_appearance_anchor(self, definition: str) -> str:
        """Extract the appearance anchor from a character definition."""
        normalized = _normalize_prompt_value(definition)
        if not normalized:
            return ""
        matcher = _CHARACTER_APPEARANCE_ANCHOR_PATTERN.search(normalized)
        if matcher:
            appearance = _trim_appearance_definition(matcher.group("appearance"))
            if appearance:
                return appearance
        return _trim_appearance_definition(normalized)

    def _extract_character_definitions_from_table(
        self, definitions_block: str
    ) -> list[CharacterDefinition]:
        """Extract character definitions from a markdown table format."""
        builders: dict[str, _CharacterDefinitionBuilder] = {}
        schema = _CharacterDefinitionTableSchema.empty()

        for raw_line in string_value(definitions_block).splitlines():
            stripped = raw_line.strip()
            if not stripped.startswith("|"):
                continue
            cells = self._split_table_row(stripped)
            if not cells or self._is_divider_row(cells):
                continue

            if _CharacterDefinitionTableSchema.looks_like_header(cells):
                schema = _CharacterDefinitionTableSchema.from_header(cells)
                continue

            if not schema.is_valid() or schema.is_header_row(cells):
                continue

            name = _normalize_prompt_value(schema.value(cells, schema.name_index))

            if schema.is_single_row_schema():
                position = _normalize_prompt_value(schema.value(cells, schema.position_index))
                gender_age = _normalize_prompt_value(schema.value(cells, schema.gender_age_index))
                face = _normalize_prompt_value(schema.value(cells, schema.face_index))
                hair = _normalize_prompt_value(schema.value(cells, schema.hair_index))
                body = _normalize_prompt_value(schema.value(cells, schema.body_index))
                clothing = _normalize_prompt_value(schema.value(cells, schema.clothing_index))
                stable_acc = _normalize_prompt_value(schema.value(cells, schema.stable_accessories_index))
                immutable = _normalize_prompt_value(schema.value(cells, schema.immutable_visual_index))
                appearance = _trim_appearance_definition(schema.value(cells, schema.appearance_index))
                behavior = _normalize_prompt_value(schema.value(cells, schema.behavior_index))
                speech = _normalize_prompt_value(schema.value(cells, schema.speech_index))

                if name and _has_any_known_value(
                    appearance, gender_age, face, hair, body, clothing, stable_acc, immutable
                ):
                    builders.setdefault(
                        name,
                        _CharacterDefinitionBuilder.from_single_row(
                            name, gender_age, position, face, hair, body,
                            clothing, stable_acc, immutable, appearance, behavior, speech,
                        ),
                    )
                continue

            # Multi-row schema
            gender = _normalize_prompt_value(schema.value(cells, schema.gender_index))
            age = _normalize_prompt_value(schema.value(cells, schema.age_index))
            part = _normalize_prompt_value(schema.value(cells, schema.part_index))
            detail = _normalize_prompt_value(schema.value(cells, schema.detail_index))
            if name and part and detail:
                builder = builders.setdefault(name, _CharacterDefinitionBuilder(name))
                builder.set_gender(gender)
                builder.set_age(age)
                builder.add_part(part, detail)

        return [
            builder.build()
            for builder in builders.values()
            if builder.build().name and builder.build().appearance
        ]

    def _extract_character_appearance_map(
        self, storyboard_markdown: str
    ) -> dict[str, str]:
        """Extract a map of character name -> appearance from storyboard markdown."""
        appearances: dict[str, str] = {}
        for definition in self.extract_character_definitions(storyboard_markdown):
            if definition.name and definition.appearance:
                appearances[definition.name] = definition.appearance
        return appearances

    def _augment_character_appearance_definitions(
        self, prompt: str, character_appearances: dict[str, str]
    ) -> str:
        """Augment a frame prompt with character appearance definitions.

        For each character whose name appears in the prompt, insert their
        appearance definition in Chinese parentheses after their first mention.
        """
        normalized = _normalize_prompt_value(prompt)
        if not normalized or not character_appearances:
            return normalized

        augmented = normalized
        # Sort by name length descending so longer names match first
        sorted_entries = sorted(
            character_appearances.items(), key=lambda x: len(x[0]), reverse=True
        )

        for char_name, appearance in sorted_entries:
            cname = _normalize_prompt_value(char_name)
            capp = _normalize_prompt_value(appearance)
            if not cname or not capp:
                continue
            if cname not in augmented:
                continue
            if (
                f"{cname}（{capp}）" in augmented
                or f"{cname}({capp})" in augmented
            ):
                continue

            # Replace first occurrence of name that is NOT followed by ( or （
            pattern = re.compile(re.escape(cname) + r"(?!\s*[（(])")
            matcher = pattern.search(augmented)
            if matcher:
                augmented = (
                    augmented[: matcher.start()]
                    + f"{cname}（{capp}）"
                    + augmented[matcher.end() :]
                )

        return augmented

    # -----------------------------------------------------------------------
    # Internal: duration
    # -----------------------------------------------------------------------

    def _parse_duration_range_hint(self, text: str) -> list[int] | None:
        """Parse a duration range hint from text.

        Tries patterns in order:
        1. Script duration range (e.g., "5-10s")
        2. Script single value (e.g., "5s")
        3. Plain duration range (e.g., "5-10")
        4. Plain single value (e.g., "5")
        """
        normalized = string_value(text)
        if not normalized:
            return None

        matcher = _SCRIPT_DURATION_RANGE_PATTERN.search(normalized)
        if matcher:
            left = self._safe_rounded_seconds(matcher.group("left"))
            right = self._safe_rounded_seconds(matcher.group("right"))
            low = self._clamp(min(left, right), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
            high = self._clamp(max(left, right), low, CLIP_MAX_SECONDS)
            return [low, high]

        matcher = _SCRIPT_DURATION_VALUE_PATTERN.search(normalized)
        if matcher:
            value = self._clamp(
                self._safe_rounded_seconds(matcher.group("value")),
                CLIP_MIN_SECONDS,
                CLIP_MAX_SECONDS,
            )
            return [value, value]

        matcher = _PLAIN_DURATION_RANGE_PATTERN.match(normalized)
        if matcher:
            left = self._safe_rounded_seconds(matcher.group("left"))
            right = self._safe_rounded_seconds(matcher.group("right"))
            low = self._clamp(min(left, right), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
            high = self._clamp(max(left, right), low, CLIP_MAX_SECONDS)
            return [low, high]

        matcher = _PLAIN_DURATION_VALUE_PATTERN.match(normalized)
        if matcher:
            value = self._clamp(
                self._safe_rounded_seconds(matcher.group("value")),
                CLIP_MIN_SECONDS,
                CLIP_MAX_SECONDS,
            )
            return [value, value]

        return None

    def _safe_rounded_seconds(self, value: str) -> int:
        """Safely parse a string to seconds, clamped [1, 120]."""
        try:
            return max(1, min(120, round(float(string_value(value)))))
        except (ValueError, TypeError):
            return 1

    def _normalize_clip_duration_range(
        self,
        supported_durations: list[int],
        target_duration_seconds: int,
        min_duration_seconds: int,
        max_duration_seconds: int,
    ) -> list[int]:
        """Normalize a single clip duration range against supported durations."""
        normalized_target = self._clamp(target_duration_seconds, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
        normalized_min = self._clamp(
            min(min_duration_seconds, max_duration_seconds), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS
        )
        normalized_max = self._clamp(
            max(min_duration_seconds, max_duration_seconds), normalized_min, CLIP_MAX_SECONDS
        )

        in_range = [d for d in supported_durations if normalized_min <= d <= normalized_max]
        if in_range:
            return [
                self._closest_supported_duration(in_range, normalized_target),
                in_range[0],
                in_range[-1],
            ]

        resolved = self._closest_supported_duration(supported_durations, normalized_target)
        return [resolved, resolved, resolved]

    def _supported_video_durations(self, requested_video_model: str) -> list[int]:
        """Get supported video durations for a given model."""
        normalized_model = string_value(requested_video_model)
        if not normalized_model:
            return []

        if self._model_resolver is None:
            return []

        try:
            section = self._model_resolver.section(
                f'model.models."{normalized_model}"'
            )
        except (AttributeError, TypeError):
            return []

        raw = string_value(section.get("supported_durations")) if isinstance(section, dict) else ""
        if not raw:
            return []

        values: list[int] = []
        for token in raw.split(","):
            try:
                value = int(token.strip())
                if value > 0 and value not in values:
                    values.append(value)
            except (ValueError, TypeError):
                pass
        values.sort()
        return values

    def _closest_supported_duration(
        self, candidates: list[int], requested_duration_seconds: int
    ) -> int:
        """Find the closest supported duration to the requested value."""
        resolved = candidates[0]
        smallest_distance = abs(resolved - requested_duration_seconds)
        for candidate in candidates:
            distance = abs(candidate - requested_duration_seconds)
            if distance < smallest_distance or (distance == smallest_distance and candidate > resolved):
                resolved = candidate
                smallest_distance = distance
        return resolved

    # -----------------------------------------------------------------------
    # Internal: camera movement
    # -----------------------------------------------------------------------

    def _extract_camera_movement(self, value: str) -> str:
        """Extract camera movement keywords from content description."""
        normalized = _normalize_prompt_value(value)
        if not normalized:
            return ""
        for token in re.split(r"[/／+＋,，;；|｜]", normalized):
            trimmed = token.strip()
            if self._looks_like_camera_movement(trimmed):
                return trimmed
        return normalized if self._looks_like_camera_movement(normalized) else ""

    def _looks_like_camera_movement(self, value: str) -> bool:
        """Check if a value looks like a camera movement keyword."""
        normalized = _normalize_prompt_value(value).lower()
        if not normalized:
            return False
        keywords = [
            "推", "拉", "摇", "移", "跟", "甩", "升", "降",
            "环绕", "环拍", "手持",
            "dolly", "push", "pull", "pan", "tilt", "truck",
            "track", "orbit", "handheld", "whip",
        ]
        return any(k in normalized for k in keywords)

    # -----------------------------------------------------------------------
    # Internal: prompt construction
    # -----------------------------------------------------------------------

    def _build_continuous_clip_prompt(
        self,
        first_frame_prompt: str,
        last_frame_prompt: str,
        content_description: str,
        camera_movement: str,
        duration_hint: str,
    ) -> str:
        """Build a continuous clip prompt from shot components."""
        parts: list[str] = []
        if first_frame_prompt:
            parts.append("首帧：" + first_frame_prompt)
        if last_frame_prompt:
            parts.append("尾帧：" + last_frame_prompt)
        if content_description:
            parts.append("分镜内容：" + content_description)
        if camera_movement and camera_movement.lower() != "static":
            parts.append("运镜关键词：" + camera_movement)
        if duration_hint:
            parts.append("时长：" + duration_hint)
        return self._truncate_text("；".join(parts), 2200)

    def _truncate_text(self, value: str, max_length: int) -> str:
        """Truncate text to max_length with an ellipsis if needed."""
        normalized = string_value(value)
        if len(normalized) <= max_length:
            return normalized
        return normalized[: max(0, max_length - 1)].strip() + "…"

    # -----------------------------------------------------------------------
    # Internal: table parsing utilities
    # -----------------------------------------------------------------------

    def _split_table_row(self, row: str) -> list[str]:
        """Split a markdown table row into cells."""
        trimmed = row.strip()
        if not trimmed.startswith("|"):
            return []
        content = trimmed[1:-1] if trimmed.endswith("|") else trimmed[1:]
        return [part.strip() for part in content.split("|")]

    def _detect_storyboard_table_schema(
        self, lines: list[str]
    ) -> _StoryboardTableSchema:
        """Detect the storyboard table schema from markdown lines."""
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped.startswith("|"):
                continue
            cells = self._split_table_row(stripped)
            if not cells or self._is_divider_row(cells):
                continue
            if self._looks_like_header_row(cells):
                return _StoryboardTableSchema.from_header(cells)
        return _StoryboardTableSchema.empty()

    def _looks_like_header_row(self, cells: list[str]) -> bool:
        """Check if a row looks like a storyboard table header."""
        for cell in cells:
            norm = _normalize_storyboard_header(cell)
            if any(
                keyword in norm
                for keyword in [
                    "shot", "镜号",
                    "首帧", "尾帧",
                    "startframe", "endframe",
                    "分镜内容描述", "剧情画面与声音描述",
                    "合并长段描述", "画面叙述",
                    "storydescription", "contentdescription",
                    "duration", "时长",
                ]
            ):
                return True
        return False

    def _is_divider_row(self, cells: list[str]) -> bool:
        """Check if a row is a markdown table divider (e.g., |---|---|---|)."""
        for cell in cells:
            if not re.match(r"^[:\\-\\s]*$", cell):
                return False
        return True

    def _clamp(self, value: int, min_value: int, max_value: int) -> int:
        """Clamp a value between min and max."""
        return max(min_value, min(max_value, value))

    def first_non_blank(self, *values: str) -> str:
        """Return the first non-blank value."""
        for v in values:
            if v and v.strip():
                return v
        return ""
