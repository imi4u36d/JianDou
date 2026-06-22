"""Task resume helpers for completed clip detection.

The worker, command, and diagnosis services all need the same answer: which
video clips already have durable outputs, and where should a resumed render
continue from? Keeping the logic here prevents drift between retry commands and
worker recovery.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from backend.domain.task_result_types import is_primary_video
from backend.shared import first_non_blank, safe_int, string_value


def existing_video_clip_indices(outputs: Iterable[dict[str, Any]] | None) -> list[int]:
    """Return sorted positive clip indexes for primary video outputs only."""
    indices: set[int] = set()
    for output in outputs or []:
        if not isinstance(output, dict):
            continue
        if not is_primary_video(output.get("resultType")):
            continue
        clip_index = safe_int(output.get("clipIndex"), 0)
        if clip_index > 0:
            indices.add(clip_index)
    return sorted(indices)

def last_contiguous_completed_clip_index(clip_indices: Iterable[int] | None) -> int:
    """Return the last completed clip index before the first gap."""
    expected = 1
    for clip_index in sorted({idx for idx in clip_indices or [] if isinstance(idx, int) and idx > 0}):
        if clip_index != expected:
            break
        expected += 1
    return expected - 1

def resolve_resume_last_frame_url(
    outputs: Iterable[dict[str, Any]] | None,
    completed_clip_count: int,
    execution_context: dict[str, Any] | None = None,
) -> str:
    """Resolve the best last-frame URL to seed the next resumed clip."""
    stored = string_value((execution_context or {}).get("lastFrameUrl"))
    if stored:
        return stored
    if completed_clip_count <= 0:
        return ""
    for output in outputs or []:
        if not isinstance(output, dict):
            continue
        if not is_primary_video(output.get("resultType")):
            continue
        if safe_int(output.get("clipIndex"), 0) != completed_clip_count:
            continue
        extra = output.get("extra") if isinstance(output.get("extra"), dict) else {}
        return first_non_blank(
            string_value(extra.get("lastFrameUrl")),
            string_value(extra.get("firstFrameUrl")),
        )
    return ""

