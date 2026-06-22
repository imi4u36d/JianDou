from __future__ import annotations

import pytest

pytestmark = pytest.mark.domain
from backend.domain.task_resume import (
    existing_video_clip_indices,
    last_contiguous_completed_clip_index,
    resolve_resume_last_frame_url,
)


def test_existing_video_clip_indices_ignores_non_video_outputs() -> None:
    outputs = [
        {"resultType": "image", "clipIndex": 1},
        {"resultType": "video", "clipIndex": 2},
        {"resultType": "video_clip", "clipIndex": 1},
        {"resultType": "video_generation", "clipIndex": 3},
        {"resultType": "video_join", "clipIndex": 10002},
        {"resultType": "video", "clipIndex": 2},
        {"resultType": "video", "clipIndex": 0},
    ]

    assert existing_video_clip_indices(outputs) == [1, 2, 3]


def test_last_contiguous_completed_clip_index_stops_at_first_gap() -> None:
    assert last_contiguous_completed_clip_index([1, 2, 4, 5]) == 2
    assert last_contiguous_completed_clip_index([2, 3]) == 0
    assert last_contiguous_completed_clip_index([3, 1, 2]) == 3


def test_resolve_resume_last_frame_url_prefers_execution_context() -> None:
    outputs = [
        {
            "resultType": "video",
            "clipIndex": 2,
            "extra": {"lastFrameUrl": "https://example.test/clip-2-last.png"},
        }
    ]

    assert (
        resolve_resume_last_frame_url(outputs, 2, {"lastFrameUrl": "https://example.test/context-last.png"})
        == "https://example.test/context-last.png"
    )


def test_resolve_resume_last_frame_url_uses_completed_clip_extra() -> None:
    outputs = [
        {
            "resultType": "video",
            "clipIndex": 1,
            "extra": {"firstFrameUrl": "https://example.test/clip-1-first.png"},
        },
        {
            "resultType": "video",
            "clipIndex": 2,
            "extra": {"lastFrameUrl": "https://example.test/clip-2-last.png"},
        },
    ]

    assert resolve_resume_last_frame_url(outputs, 2) == "https://example.test/clip-2-last.png"
    assert resolve_resume_last_frame_url(outputs, 1) == "https://example.test/clip-1-first.png"
