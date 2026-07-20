from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.shared import safe_int, trim


def _strip_markdown_cell(value: str) -> str:
    return re.sub(r"<br\s*/?>", " ", trim(value), flags=re.IGNORECASE).replace("\\|", "|").strip()

def _split_markdown_row(line: str) -> list[str]:
    stripped = trim(line)
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
class WorkflowVisualAssetPlan:
    asset_type: str
    name: str
    description: str
    summary: str

    def to_view(self) -> dict[str, Any]:
        return {
            "assetType": self.asset_type,
            "name": self.name,
            "description": self.description,
            "summary": self.summary,
            # Character consumers historically read these two fields.
            "appearance": self.description,
            "appearanceSummary": self.summary,
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
    visual_assets: list[WorkflowVisualAssetPlan]

    def to_view(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return [character.to_view() for character in self.characters], [clip.to_view() for clip in self.clips]

    def visual_assets_view(self) -> list[dict[str, Any]]:
        return [asset.to_view() for asset in self.visual_assets]

def parse_workflow_storyboard_markdown(markdown: str) -> WorkflowStoryboardPlan:
    """Parse workflow storyboard markdown tables into character and clip plans."""
    characters: list[WorkflowCharacterPlan] = []
    visual_assets: list[WorkflowVisualAssetPlan] = []
    clips: list[WorkflowStoryboardClipPlan] = []
    section = ""
    table_headers: list[str] = []
    for line in markdown.splitlines():
        text = trim(line)
        if not text:
            continue
        if "公共素材定义" in text or "视觉素材定义" in text:
            section = "visual_assets"
            table_headers = []
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
                visual_assets.append(
                    WorkflowVisualAssetPlan(
                        asset_type="character",
                        name=character.name,
                        description=character.appearance,
                        summary=character.summary,
                    )
                )
        elif section == "visual_assets":
            asset = _visual_asset_from_cells(table_headers, cells)
            if asset is not None:
                visual_assets.append(asset)
                if asset.asset_type == "character":
                    characters.append(
                        WorkflowCharacterPlan(
                            name=asset.name,
                            appearance=asset.description,
                            summary=asset.summary,
                        )
                    )
        elif section == "clips":
            clips.append(_clip_from_cells(cells, len(clips) + 1))
    visual_assets = _deduplicate_visual_assets(visual_assets)
    characters = _deduplicate_characters(characters)
    # Stable ordering preserves the historical 1000 + character index mapping.
    priority = {"character": 0, "prop": 1, "building": 2, "scene": 3, "vehicle": 4, "other": 5}
    visual_assets.sort(key=lambda item: priority.get(item.asset_type, 5))
    return WorkflowStoryboardPlan(characters=characters, clips=clips, visual_assets=visual_assets)

def _visual_asset_from_cells(headers: list[str], cells: list[str]) -> WorkflowVisualAssetPlan | None:
    normalized_headers = [re.sub(r"[\s()（）:_-]+", "", header).lower() for header in headers]

    def value(*aliases: str) -> str:
        index = next(
            (i for i, header in enumerate(normalized_headers) if any(alias in header for alias in aliases)),
            None,
        )
        return cells[index] if index is not None and index < len(cells) else ""

    raw_type = value("素材类型", "类型", "assettype") or (cells[0] if cells else "")
    name = value("素材名称", "名称", "名字", "name") or (cells[1] if len(cells) > 1 else "")
    description = value("稳定视觉锚点", "视觉描述", "视觉定义", "外观", "description")
    consistency = value("一致性锚点", "补充说明", "备注", "consistency")
    if not name or name in {"名称", "素材名称"}:
        return None
    asset_type = _normalize_asset_type(raw_type)
    details = "；".join(part for part in (description, consistency) if part and part not in {"未明确", "无"})
    return WorkflowVisualAssetPlan(
        asset_type=asset_type,
        name=name,
        description=details or name,
        summary=details or name,
    )

def _normalize_asset_type(value: str) -> str:
    normalized = re.sub(r"[\s_-]+", "", value).lower()
    if normalized in {"角色", "人物", "character", "person"}:
        return "character"
    if normalized in {"道具", "物件", "prop", "object"}:
        return "prop"
    if normalized in {"建筑", "building", "architecture"}:
        return "building"
    if normalized in {"场景", "地点", "scene", "location"}:
        return "scene"
    if normalized in {"载具", "车辆", "vehicle"}:
        return "vehicle"
    return "other"

def _deduplicate_visual_assets(items: list[WorkflowVisualAssetPlan]) -> list[WorkflowVisualAssetPlan]:
    result: list[WorkflowVisualAssetPlan] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item.asset_type, item.name)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

def _deduplicate_characters(items: list[WorkflowCharacterPlan]) -> list[WorkflowCharacterPlan]:
    result: list[WorkflowCharacterPlan] = []
    seen: set[str] = set()
    for item in items:
        if item.name not in seen:
            seen.add(item.name)
            result.append(item)
    return result

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
    clip_no = safe_int(cells[0] if cells else None, fallback_index)
    duration_text = cells[4] if len(cells) > 4 else ""
    duration_match = re.search(r"\d+", duration_text)
    duration_seconds = safe_int(duration_match.group(0), 8) if duration_match else 8
    return WorkflowStoryboardClipPlan(
        clip_index=clip_no if clip_no > 0 else fallback_index,
        shot_label=f"镜头 {cells[0]}" if cells else f"镜头 {fallback_index}",
        start_frame=cells[1] if len(cells) > 1 else "",
        end_frame=cells[2] if len(cells) > 2 else "",
        scene=cells[3] if len(cells) > 3 else "",
        duration_hint=duration_text,
        target_duration_seconds=duration_seconds,
    )
