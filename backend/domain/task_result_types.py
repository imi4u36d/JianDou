"""Task result type constants and predicates.

Mirrors the Java TaskResultTypes domain class.
"""

from __future__ import annotations

TEXT = "text"
IMAGE = "image"
VIDEO = "video"
VIDEO_GENERATION = "video_generation"
VIDEO_CLIP = "video_clip"
VIDEO_JOIN = "video_join"
JOIN_VIDEO = "join_video"
JOINED_VIDEO = "joined_video"

_PRIMARY_VIDEO_TYPES = frozenset({VIDEO, VIDEO_GENERATION, VIDEO_CLIP})
_VIDEO_TYPES = frozenset({VIDEO, VIDEO_GENERATION, VIDEO_CLIP, VIDEO_JOIN})
_JOIN_TYPES = frozenset({VIDEO_JOIN, JOIN_VIDEO, JOINED_VIDEO})


def is_video(raw: object) -> bool:
    """Check if the result type is a primary video type (video or video_clip)."""
    return _normalize(raw) in _VIDEO_TYPES


def is_join(raw: object) -> bool:
    """Check if the result type is a join type (video_join, join_video, joined_video)."""
    return _normalize(raw) in _JOIN_TYPES


def is_primary_video(raw: object) -> bool:
    """Check if the result type is a clip-level video output."""
    return _normalize(raw) in _PRIMARY_VIDEO_TYPES


def _normalize(raw: object) -> str:
    if raw is None:
        return ""
    return str(raw).strip().lower()
