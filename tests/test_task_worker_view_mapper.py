from __future__ import annotations

import pytest
pytestmark = pytest.mark.service
from backend.domain.task_record import TaskRecord
from backend.services.task_worker_view_mapper import TaskViewMapper


def test_view_mapper_uses_domain_result_type_predicates_for_monitoring() -> None:
    task = TaskRecord(
        id="task_view",
        title="View task",
        status="COMPLETED",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:05:00+00:00",
        execution_context={"plannedClipCount": 3},
        outputs=[
            {"resultType": "image", "clipIndex": 1, "downloadUrl": "ignored.png"},
            {"resultType": "video_clip", "clipIndex": 1, "downloadUrl": "clip-1.mp4"},
            {"resultType": "video_generation", "clipIndex": 2, "previewUrl": "clip-2-preview.mp4"},
            {
                "resultType": "video_join",
                "clipIndex": 10002,
                "downloadUrl": "joined.mp4",
                "extra": {"joinName": "join-2"},
            },
        ],
    )

    detail = TaskViewMapper().to_detail(task)

    monitoring = detail["monitoring"]
    assert monitoring["plannedClipCount"] == 3
    assert monitoring["renderedClipCount"] == 2
    assert monitoring["latestVideoOutputUrl"] == "clip-2-preview.mp4"
    assert monitoring["latestJoinName"] == "join-2"
    assert monitoring["latestJoinOutputUrl"] == "joined.mp4"
