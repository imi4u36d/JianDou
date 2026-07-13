from __future__ import annotations

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository_mapping import (
    _biz_task_from_record,
    _light_request_snapshot,
    _light_url,
    _record_from_biz_task,
)


def test_light_url_rejects_embedded_and_oversized_payloads() -> None:
    assert _light_url("https://cdn.example.test/image.png") == "https://cdn.example.test/image.png"
    assert _light_url("data:image/png;base64,abc") == ""
    assert _light_url("https://example.test/" + "x" * 2100) == ""


def test_light_request_snapshot_keeps_only_bounded_detail_fields() -> None:
    snapshot = _light_request_snapshot(
        {
            "taskType": "image_generation",
            "title": "t" * 250,
            "creativePrompt": "p" * 2200,
            "referenceImageUrls": ["/one.png", "data:image/png;base64,abc", "/two.png"],
            "providerPayload": {"secret": "must-not-leak"},
        }
    )

    assert snapshot["taskType"] == "image_generation"
    assert len(snapshot["title"]) == 200
    assert len(snapshot["creativePrompt"]) == 2000
    assert snapshot["referenceImageUrls"] == ["/one.png", "/two.png"]
    assert "providerPayload" not in snapshot


def test_task_record_mapping_preserves_persisted_core_fields() -> None:
    record = TaskRecord(
        id="task-1",
        owner_user_id=7,
        task_type="video_generation",
        title="雨夜任务",
        aspect_ratio="16:9",
        status="RENDERING",
        progress=42,
        creative_prompt="雨夜追逐",
        request_snapshot={"transcriptText": "主角穿过雨幕"},
        execution_context={"completedOutputCount": 2},
    )

    restored = _record_from_biz_task(_biz_task_from_record(record))

    assert restored.id == "task-1"
    assert restored.owner_user_id == 7
    assert restored.title == "雨夜任务"
    assert restored.status == "RENDERING"
    assert restored.progress == 42
    assert restored.transcript_text == "主角穿过雨幕"
    assert restored.completed_output_count == 2
