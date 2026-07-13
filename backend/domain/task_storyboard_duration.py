"""Storyboard clip-duration parsing, distribution, and model normalization."""

from __future__ import annotations

import re
from typing import Any

CLIP_MIN_SECONDS = 5
CLIP_MAX_SECONDS = 12

_SCRIPT_DURATION_RANGE_PATTERN = re.compile(
    r"(?P<left>\d{1,3}(?:\.\d+)?)\s*(?:-|~|～|—|到)\s*(?P<right>\d{1,3}(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|秒)",
    re.IGNORECASE,
)
_SCRIPT_DURATION_VALUE_PATTERN = re.compile(
    r"(?<![.\d])(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|秒)(?![a-zA-Z])",
    re.IGNORECASE,
)
_PLAIN_DURATION_RANGE_PATTERN = re.compile(
    r"^\s*(?P<left>\d{1,3}(?:\.\d+)?)\s*(?:-|~|～|—|到)\s*(?P<right>\d{1,3}(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)
_PLAIN_DURATION_VALUE_PATTERN = re.compile(r"^\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*$", re.IGNORECASE)


class StoryboardDurationPlanner:
    """Own clip-duration policy while reusing the facade's table parser."""

    def __init__(self, owner: Any, model_resolver: Any = None) -> None:
        self._owner = owner
        self._model_resolver = model_resolver

    def build_clip_duration_plan_context(
        self,
        clip_duration_plan: list[list[int]],
        storyboard_duration_ranges: list[list[int]],
    ) -> list[dict[str, Any]]:
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
                row.update(
                    durationSource="storyboard",
                    scriptMinDurationSeconds=scripted[0],
                    scriptMaxDurationSeconds=scripted[1],
                )
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
        scripted_min_sum = sum(max(1, ranges[index][0]) for index in range(scripted_clip_count))
        scripted_max_sum = sum(
            max(max(1, ranges[index][0]), ranges[index][1]) for index in range(scripted_clip_count)
        )
        unresolved_count = max(0, normalized_clip_count - scripted_clip_count)
        if unresolved_count == 0:
            global_min = CLIP_MIN_SECONDS
            global_max = global_min
        else:
            global_min = max(1, round(max(unresolved_count, total_min - scripted_min_sum) / unresolved_count))
            global_max = max(
                global_min,
                round(max(unresolved_count, total_max - scripted_max_sum) / unresolved_count),
            )
        global_min = self._clamp(global_min, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
        global_max = self._clamp(global_max, global_min, CLIP_MAX_SECONDS)

        plan: list[list[int]] = []
        for index in range(normalized_clip_count):
            scripted = index < len(ranges)
            clip_min = ranges[index][0] if scripted else global_min
            clip_max = max(clip_min, ranges[index][1]) if scripted else global_max
            clip_min = self._clamp(clip_min, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
            clip_max = self._clamp(clip_max, clip_min, CLIP_MAX_SECONDS)
            clip_target = clip_min if scripted else max(clip_min, min(clip_max, round((clip_min + clip_max) / 2)))
            plan.append([self._clamp(clip_target, clip_min, clip_max), clip_min, clip_max])
        return plan

    def normalize_clip_duration_plan(
        self,
        requested_video_model: str,
        clip_duration_plan: list[list[int]],
    ) -> list[list[int]]:
        if not clip_duration_plan:
            return []
        supported = self._supported_video_durations(requested_video_model)
        if "agnes" in self._string_value(requested_video_model).lower():
            supported = [duration for duration in supported if duration <= 6]
        if not supported:
            return clip_duration_plan
        return [
            self._normalize_clip_duration_range(supported, item[0], item[1], item[2])
            for item in clip_duration_plan
            if item is not None and len(item) >= 3
        ]

    def extract_storyboard_shot_duration_ranges(self, storyboard_markdown: str) -> list[list[int]]:
        normalized = self._owner._storyboard_section(self._string_value(storyboard_markdown))
        if not normalized:
            return []
        lines = normalized.splitlines()
        schema = self._owner._detect_storyboard_table_schema(lines)
        if not schema.header_cells or schema.missing_structured_required_columns():
            return []
        ranges: list[list[int]] = []
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped.startswith("|"):
                continue
            cells = self._owner._split_table_row(stripped)
            if len(cells) < 2 or self._owner._is_divider_row(cells) or schema.is_header_row(cells):
                continue
            first = schema.cell(cells, schema.shot_no_index, 0)
            if not first or "镜号" in first or "shot" in first.lower():
                continue
            parsed = self._parse_duration_range_hint(schema.cell(cells, schema.duration_index, -1))
            if parsed is not None:
                ranges.append(parsed)
        return ranges

    def _parse_duration_range_hint(self, text: str) -> list[int] | None:
        normalized = self._string_value(text)
        if not normalized:
            return None
        for pattern, is_range in (
            (_SCRIPT_DURATION_RANGE_PATTERN, True),
            (_SCRIPT_DURATION_VALUE_PATTERN, False),
            (_PLAIN_DURATION_RANGE_PATTERN, True),
            (_PLAIN_DURATION_VALUE_PATTERN, False),
        ):
            matcher = pattern.search(normalized) if pattern in (_SCRIPT_DURATION_RANGE_PATTERN, _SCRIPT_DURATION_VALUE_PATTERN) else pattern.match(normalized)
            if not matcher:
                continue
            left = self._safe_rounded_seconds(matcher.group("left" if is_range else "value"))
            right = self._safe_rounded_seconds(matcher.group("right")) if is_range else left
            low = self._clamp(min(left, right), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
            return [low, self._clamp(max(left, right), low, CLIP_MAX_SECONDS)]
        return None

    def _normalize_clip_duration_range(
        self,
        supported: list[int],
        target: int,
        minimum: int,
        maximum: int,
    ) -> list[int]:
        target = self._clamp(target, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
        minimum = self._clamp(min(minimum, maximum), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS)
        maximum = self._clamp(max(minimum, maximum), minimum, CLIP_MAX_SECONDS)
        in_range = [duration for duration in supported if minimum <= duration <= maximum]
        if in_range:
            return [self._closest_supported_duration(in_range, target), in_range[0], in_range[-1]]
        resolved = self._closest_supported_duration(supported, target)
        return [resolved, resolved, resolved]

    def _supported_video_durations(self, requested_video_model: str) -> list[int]:
        model = self._string_value(requested_video_model)
        if not model:
            return []
        if "agnes" in model.lower():
            return [4, 5, 6]
        if self._model_resolver is None:
            return []
        try:
            section = self._model_resolver.section(f'model.models."{model}"')
        except (AttributeError, TypeError):
            return []
        raw = self._string_value(section.get("supported_durations")) if isinstance(section, dict) else ""
        values: list[int] = []
        for token in raw.split(","):
            try:
                value = int(token.strip())
                if value > 0 and value not in values:
                    values.append(value)
            except (ValueError, TypeError):
                continue
        return sorted(values)

    @staticmethod
    def _closest_supported_duration(candidates: list[int], requested: int) -> int:
        return min(candidates, key=lambda candidate: (abs(candidate - requested), -candidate))

    @staticmethod
    def _safe_rounded_seconds(value: str) -> int:
        try:
            return max(1, min(120, round(float(StoryboardDurationPlanner._string_value(value)))))
        except (ValueError, TypeError):
            return 1

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _string_value(value: Any) -> str:
        return "" if value is None else str(value).strip()
