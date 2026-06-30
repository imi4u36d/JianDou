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


def test_view_mapper_prefers_material_thumbnail_for_list_item() -> None:
    task = TaskRecord(
        id="task_thumb",
        title="Thumb task",
        status="COMPLETED",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:05:00+00:00",
        materials=[
            {
                "kind": "source",
                "mediaType": "image",
                "fileUrl": "/storage/tasks/task_thumb/source.png",
                "thumbnailUrl": "/storage/thumbs/tasks/task_thumb/source.jpg",
            },
            {
                "kind": "clip",
                "mediaType": "image",
                "fileUrl": "/storage/tasks/task_thumb/original.png",
                "thumbnailUrl": "/storage/thumbs/tasks/task_thumb/original.jpg",
            }
        ],
        outputs=[
            {
                "resultType": "image",
                "clipIndex": 1,
                "downloadUrl": "/storage/tasks/task_thumb/original.png",
            }
        ],
    )

    item = TaskViewMapper().to_list_item(task)

    assert item["thumbnailUrl"] == "/storage/thumbs/tasks/task_thumb/original.jpg"


def test_view_mapper_does_not_use_video_preview_as_image_thumbnail() -> None:
    task = TaskRecord(
        id="task_video_preview",
        title="Video preview task",
        status="COMPLETED",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:05:00+00:00",
        outputs=[
            {
                "resultType": "video",
                "clipIndex": 1,
                "previewUrl": "/storage/tasks/task_video_preview/clip.mp4",
                "extra": {"thumbnailUrl": "/storage/thumbs/tasks/task_video_preview/clip.jpg"},
            }
        ],
    )

    item = TaskViewMapper().to_list_item(task)

    assert item["thumbnailUrl"] == "/storage/thumbs/tasks/task_video_preview/clip.jpg"
