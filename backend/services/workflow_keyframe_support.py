"""Shared keyframe selection and URL resolution helpers."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import WorkflowStage
from backend.domain.json_payloads import read_json_object
from backend.models.workflow import BizStageVersion
from backend.shared import first_non_blank, trim

VARIANT_KIND_CHARACTER_SHEET = "character_sheet"
VARIANT_KIND_VISUAL_ASSET = "visual_asset"


def is_character_sheet_version(version: BizStageVersion) -> bool:
    # Compatibility name: callers use this predicate to exclude all synthetic
    # public-material versions from ordinary keyframe operations.
    return trim(read_json_object(version.input_summary_json).get("variantKind")) in {
        VARIANT_KIND_CHARACTER_SHEET,
        VARIANT_KIND_VISUAL_ASSET,
    }


def keyframe_frame_url(output: dict[str, Any], frame_role: str) -> str:
    normalized_role = trim(frame_role).lower()
    stored_role = trim(output.get("frameRole")).lower()
    if normalized_role in ("last", "end", "尾帧"):
        return first_non_blank(
            trim(output.get("endFrameRemoteUrl")),
            trim(output.get("lastFrameRemoteUrl")),
            trim(output.get("endFrameUrl")),
            trim(output.get("lastFrameUrl")),
            trim(output.get("remoteSourceUrl")) if stored_role in ("last", "end", "尾帧") else "",
            trim(output.get("fileUrl")) if stored_role in ("last", "end", "尾帧") else "",
        )
    return first_non_blank(
        trim(output.get("startFrameRemoteUrl")),
        trim(output.get("firstFrameRemoteUrl")),
        trim(output.get("startFrameUrl")),
        trim(output.get("firstFrameUrl")),
        trim(output.get("remoteSourceUrl")) if stored_role in ("first", "start", "首帧") else "",
        trim(output.get("fileUrl")) if stored_role in ("first", "start", "首帧") else "",
    )


def find_first_frame_remote_url(versions: list[BizStageVersion], clip_index: int) -> str:
    candidates = [
        version
        for version in versions
        if version.stage_type == WorkflowStage.KEYFRAME.value and version.clip_index == clip_index
    ]
    for version in sorted(candidates, key=lambda item: 0 if item.selected else 1):
        output = read_json_object(version.output_summary_json)
        url = first_non_blank(
            trim(output.get("startFrameRemoteUrl")),
            trim(output.get("remoteSourceUrl")),
        )
        if url:
            return url
    return ""


def find_keyframe_frame_url(
    versions: list[BizStageVersion],
    clip_index: int,
    frame_role: str,
) -> str:
    normalized_role = trim(frame_role).lower()
    selection_key = "selectedLastFrame" if normalized_role in ("last", "end", "尾帧") else "selectedFirstFrame"
    candidates = [
        version
        for version in versions
        if version.stage_type == WorkflowStage.KEYFRAME.value
        and version.clip_index == clip_index
        and not is_character_sheet_version(version)
    ]
    for version in candidates:
        output = read_json_object(version.output_summary_json)
        if output.get(selection_key) is True:
            url = keyframe_frame_url(output, frame_role)
            if url:
                return url
    for version in candidates:
        if version.selected != 1:
            continue
        url = keyframe_frame_url(read_json_object(version.output_summary_json), frame_role)
        if url:
            return url
    for version in candidates:
        url = keyframe_frame_url(read_json_object(version.output_summary_json), frame_role)
        if url:
            return url
    return ""
