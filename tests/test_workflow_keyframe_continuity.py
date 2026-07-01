from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.service

from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_service import WorkflowService


def _version(**overrides) -> BizStageVersion:
    values = {
        "stage_version_id": "kv_default",
        "workflow_id": "wf_continuity",
        "owner_user_id": 1,
        "stage_type": "keyframe",
        "clip_index": 1,
        "version_no": 1,
        "title": "Keyframe",
        "status": "COMPLETED",
        "selected": 0,
        "rating": None,
        "rating_note": "",
        "rated_at": None,
        "parent_version_id": "",
        "source_material_asset_id": "",
        "material_asset_id": "",
        "preview_url": "",
        "download_url": "",
        "input_summary_json": '{"variantKind": "keyframe"}',
        "output_summary_json": "{}",
        "model_call_summary_json": "{}",
        "timezone_offset_minutes": 0,
        "is_deleted": 0,
        "create_time": "2026-01-01T00:00:00Z",
        "update_time": "2026-01-01T00:00:00Z",
        "remark": "",
    }
    values.update(overrides)
    return BizStageVersion(**values)


def _workflow(**overrides) -> BizStageWorkflow:
    values = {
        "workflow_id": "wf_continuity",
        "owner_user_id": 1,
        "title": "Continuity Workflow",
        "transcript_text": "story",
        "aspect_ratio": "16:9",
        "text_analysis_model": "text-model",
        "image_model": "image-model",
        "video_model": "video-model",
        "video_size": "1280*720",
        "keyframe_seed": 11,
        "video_seed": 22,
        "duration_mode": "auto",
        "execution_mode": "manual",
        "auto_pilot_state": "idle",
        "auto_pilot_next_stage": "",
        "auto_pilot_error_message": "",
        "auto_pilot_started_at": "",
        "auto_pilot_paused_at": "",
        "auto_pilot_current_task": "",
        "task_seed": None,
        "min_duration_seconds": 5,
        "max_duration_seconds": 12,
        "status": "READY",
        "current_stage": "keyframe",
        "selected_storyboard_version_id": "sv_story",
        "final_join_asset_id": "",
        "effect_rating": None,
        "effect_rating_note": "",
        "metadata_json": "{}",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00Z",
        "update_time": "2026-01-01T00:00:00Z",
        "is_deleted": 0,
        "remark": "",
    }
    values.update(overrides)
    return BizStageWorkflow(**values)


class _FakeGenerationService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_run(self, request: dict) -> dict:
        self.calls.append(request)
        return {
            "id": f"run_{len(self.calls)}",
            "status": "succeeded",
            "resultImage": {
                "outputUrl": f"https://cdn.example/generated-{len(self.calls)}.png",
                "mimeType": "image/png",
                "width": 1824,
                "height": 1024,
                "runId": f"run_{len(self.calls)}",
                "metadata": {
                    "remoteSourceUrl": f"https://remote.example/generated-{len(self.calls)}.png",
                    "provider": "fake",
                    "providerModel": "fake-image",
                },
                "modelInfo": {"provider": "fake"},
            },
        }


def test_find_keyframe_frame_url_prefers_explicit_selected_last_frame() -> None:
    versions = [
        _version(
            stage_version_id="kv_full",
            selected=1,
            output_summary_json='{"endFrameRemoteUrl": "https://cdn.example/old-last.png"}',
        ),
        _version(
            stage_version_id="kv_last",
            version_no=2,
            selected=0,
            output_summary_json='{"frameRole": "last", "remoteSourceUrl": "https://cdn.example/new-last.png", "selectedLastFrame": true}',
        ),
    ]

    assert (
        WorkflowService._find_keyframe_frame_url(WorkflowService(None), versions, 1, "last")
        == "https://cdn.example/new-last.png"
    )


def test_find_keyframe_frame_url_ignores_character_sheet_versions() -> None:
    versions = [
        _version(
            stage_version_id="kv_character",
            selected=1,
            input_summary_json='{"variantKind": "character_sheet"}',
            output_summary_json='{"endFrameRemoteUrl": "https://cdn.example/sheet.png", "selectedLastFrame": true}',
        ),
        _version(
            stage_version_id="kv_full",
            selected=1,
            output_summary_json='{"endFrameUrl": "https://cdn.example/clip-last.png"}',
        ),
    ]

    assert (
        WorkflowService._find_keyframe_frame_url(WorkflowService(None), versions, 1, "last")
        == "https://cdn.example/clip-last.png"
    )


async def test_generate_keyframe_reuses_previous_tail_as_start_without_generating_start(db_session) -> None:
    script = (
        "## 分镜脚本\n"
        "| 序号 | 首帧 | 尾帧 | 场景 | 时长 |\n"
        "|------|------|------|------|------|\n"
        "| 1 | 英雄站在门口 | 英雄推开门 | 门口 | 5s |\n"
        "| 2 | 英雄推开门 | 英雄进入房间 | 房间 | 5s |\n"
    )
    db_session.add(_workflow())
    db_session.add(
        _version(
            stage_version_id="sv_story",
            stage_type="storyboard",
            clip_index=0,
            selected=1,
            input_summary_json="{}",
            output_summary_json=json.dumps({"scriptMarkdown": script}),
        )
    )
    db_session.add(
        _version(
            stage_version_id="kv_clip_1",
            clip_index=1,
            selected=1,
            output_summary_json='{"endFrameRemoteUrl": "https://cdn.example/clip-1-last.png"}',
        )
    )
    await db_session.commit()

    fake_generation = _FakeGenerationService()
    service = WorkflowService(db_session, generation_service=fake_generation)

    await service.generate_keyframe("wf_continuity", 2, owner_user_id=1)

    assert len(fake_generation.calls) == 1
    request = fake_generation.calls[0]
    assert request["input"]["frameRole"] == "last"
    assert request["input"]["referenceImageUrl"] == "https://cdn.example/clip-1-last.png"


async def test_generate_character_sheet_does_not_generate_end_frame(db_session) -> None:
    script = (
        "## 角色定义\n"
        "| 角色 | 外观 |\n"
        "|------|------|\n"
        "| 阿宁 | red coat |\n"
        "\n"
        "## 分镜脚本\n"
        "| 序号 | 首帧 | 尾帧 | 场景 | 时长 |\n"
        "|------|------|------|------|------|\n"
        "| 1 | 阿宁站在门口 | 阿宁推开门 | 门口 | 5s |\n"
    )
    db_session.add(_workflow())
    db_session.add(
        _version(
            stage_version_id="sv_story",
            stage_type="storyboard",
            clip_index=0,
            selected=1,
            input_summary_json="{}",
            output_summary_json=json.dumps({"scriptMarkdown": script}),
        )
    )
    await db_session.commit()

    fake_generation = _FakeGenerationService()
    service = WorkflowService(db_session, generation_service=fake_generation)

    await service.generate_character_sheet("wf_continuity", 1, owner_user_id=1)

    assert len(fake_generation.calls) == 1
    request = fake_generation.calls[0]
    assert request["input"]["frameRole"] == "sheet"
    assert request["metadata"]["variantKind"] == "character_sheet"


async def test_generate_keyframe_rejects_character_sheet_clip_index(db_session) -> None:
    db_session.add(_workflow())
    await db_session.commit()

    service = WorkflowService(db_session, generation_service=_FakeGenerationService())

    with pytest.raises(ValueError, match="角色设定图请使用"):
        await service.generate_keyframe("wf_continuity", 1001, owner_user_id=1)
