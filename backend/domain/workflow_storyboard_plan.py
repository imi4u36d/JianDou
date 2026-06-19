from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _trim(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = str(value).strip()
    return stripped if stripped else fallback.strip()


def _safe_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _strip_markdown_cell(value: str) -> str:
    return re.sub(r"<br\s*/?>", " ", _trim(value), flags=re.IGNORECASE).replace("\\|", "|").strip()


def _split_markdown_row(line: str) -> list[str]:
    stripped = _trim(line)
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped[1:-1]:
        if escaped:
            current.append("\\" + char if char != "|" else char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append(_strip_markdown_cell("".join(current)))
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append(_strip_markdown_cell("".join(current)))
    return cells


def _is_markdown_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell or "") for cell in cells)


@dataclass(frozen=True)
class WorkflowCharacterPlan:
    name: str
    appearance: str
    summary: str

    def to_view(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "appearance": self.appearance,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class WorkflowStoryboardClipPlan:
    clip_index: int
    shot_label: str
    start_frame: str
    end_frame: str
    scene: str
    duration_hint: str
    target_duration_seconds: int

    def to_view(self) -> dict[str, Any]:
        return {
            "clipIndex": self.clip_index,
            "shotLabel": self.shot_label,
            "startFrame": self.start_frame,
            "endFrame": self.end_frame,
            "scene": self.scene,
            "durationHint": self.duration_hint,
            "targetDurationSeconds": self.target_duration_seconds,
        }


@dataclass(frozen=True)
class WorkflowStoryboardPlan:
    characters: list[WorkflowCharacterPlan]
    clips: list[WorkflowStoryboardClipPlan]

    def to_view(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return [character.to_view() for character in self.characters], [clip.to_view() for clip in self.clips]


def parse_workflow_storyboard_markdown(markdown: str) -> WorkflowStoryboardPlan:
    """Parse workflow storyboard markdown tables into character and clip plans."""
    characters: list[WorkflowCharacterPlan] = []
    clips: list[WorkflowStoryboardClipPlan] = []
    section = ""
    table_headers: list[str] = []
    for line in markdown.splitlines():
        text = _trim(line)
        if not text:
            continue
        if "角色定义" in text:
            section = "characters"
            table_headers = []
            continue
        if "分镜脚本" in text:
            section = "clips"
            table_headers = []
            continue
        cells = _split_markdown_row(text)
        if not cells or _is_markdown_separator(cells):
            continue
        if not table_headers:
            table_headers = cells
            continue
        if section == "characters":
            character = _character_from_cells(table_headers, cells)
            if character is not None:
                characters.append(character)
        elif section == "clips":
            clips.append(_clip_from_cells(cells, len(clips) + 1))
    return WorkflowStoryboardPlan(characters=characters, clips=clips)


def _character_from_cells(headers: list[str], cells: list[str]) -> WorkflowCharacterPlan | None:
    name = cells[0] if cells else ""
    if not name or name == "角色":
        return None
    details = []
    for header, cell in zip(headers[1:], cells[1:], strict=False):
        if cell:
            details.append(f"{header}: {cell}")
    appearance = "；".join(details)
    return WorkflowCharacterPlan(
        name=name,
        appearance=appearance,
        summary="；".join(details[:4]) or name,
    )


def _clip_from_cells(cells: list[str], fallback_index: int) -> WorkflowStoryboardClipPlan:
    clip_no = _safe_int(cells[0] if cells else None, fallback_index)
    duration_text = cells[4] if len(cells) > 4 else ""
    duration_match = re.search(r"\d+", duration_text)
    duration_seconds = _safe_int(duration_match.group(0), 8) if duration_match else 8
    return WorkflowStoryboardClipPlan(
        clip_index=clip_no if clip_no > 0 else fallback_index,
        shot_label=f"镜头 {cells[0]}" if cells else f"镜头 {fallback_index}",
        start_frame=cells[1] if len(cells) > 1 else "",
        end_frame=cells[2] if len(cells) > 2 else "",
        scene=cells[3] if len(cells) > 3 else "",
        duration_hint=duration_text,
        target_duration_seconds=duration_seconds,
    )
