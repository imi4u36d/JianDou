from __future__ import annotations

import pytest

from backend.domain.json_payloads import read_json_object
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.services.workflow_video_refresh_service import WorkflowVideoRefreshService


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


class _FakeGenerationService:
    def __init__(self, run: dict) -> None:
        self.run = run
        self.requested_run_ids: list[str] = []

    async def get_run(self, run_id: str) -> dict:
        self.requested_run_ids.append(run_id)
        return self.run


def _workflow() -> BizStageWorkflow:
    return BizStageWorkflow(
        workflow_id="wf-refresh",
        owner_user_id=9,
        title="Refresh workflow",
        current_stage="video",
        status="READY",
        update_time="2026-01-01T00:00:00Z",
    )


def _video(version_id: str, *, status: str, selected: int, download_url: str = "") -> BizStageVersion:
    return BizStageVersion(
        stage_version_id=version_id,
        workflow_id="wf-refresh",
        owner_user_id=9,
        stage_type="video",
        clip_index=1,
        version_no=2 if version_id == "video-new" else 1,
        title="Clip 1",
        status=status,
        selected=selected,
        material_asset_id="",
        preview_url=download_url,
        download_url=download_url,
        output_summary_json='{"runId":"run-video","durationSeconds":6}',
        model_call_summary_json="{}",
        is_deleted=0,
        update_time="2026-01-01T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_refresh_completed_video_creates_asset_and_selects_version() -> None:
    db = _FakeDb()
    generation = _FakeGenerationService(
        {
            "status": "completed",
            "result": {
                "metadata": {
                    "fileUrl": "https://cdn.example/new.mp4",
                    "taskStatus": "FINISHED",
                    "taskId": "remote-video",
                    "provider": "fake",
                    "providerModel": "video-model",
                },
                "width": 1280,
                "height": 720,
                "durationSeconds": 6,
            },
        }
    )
    service = WorkflowVideoRefreshService(
        db,  # type: ignore[arg-type]
        generation_service=lambda: generation,
        result_parser=WorkflowGenerationResultParser(),
        row_factory=WorkflowPersistenceRowFactory(
            now=lambda: "2026-07-10T00:00:00Z",
            random_id=lambda: "refresh-asset-id",
        ),
        thumbnail_resolver=lambda _media_type, _url: "https://cdn.example/thumb.webp",
    )
    workflow = _workflow()
    old_version = _video(
        "video-old",
        status="COMPLETED",
        selected=1,
        download_url="https://cdn.example/old.mp4",
    )
    new_version = _video("video-new", status="RUNNING", selected=0)

    changed = await service.refresh(workflow, [old_version, new_version])

    assert changed is True
    assert generation.requested_run_ids == ["run-video"]
    assert new_version.status == "COMPLETED"
    assert new_version.selected == 1
    assert old_version.selected == 0
    assert new_version.download_url == "https://cdn.example/new.mp4"
    assert read_json_object(new_version.output_summary_json)["taskStatus"] == "FINISHED"
    assert workflow.current_stage == "joined"
    assert workflow.status == "READY"
    assert len(db.added) == 1
    assert db.commits == 1


@pytest.mark.asyncio
async def test_refresh_failed_video_records_failure() -> None:
    db = _FakeDb()
    generation = _FakeGenerationService(
        {
            "status": "failed",
            "resultVideo": {"metadata": {"taskMessage": "provider failed"}},
        }
    )
    service = WorkflowVideoRefreshService(
        db,  # type: ignore[arg-type]
        generation_service=lambda: generation,
        result_parser=WorkflowGenerationResultParser(),
        row_factory=WorkflowPersistenceRowFactory(),
        thumbnail_resolver=lambda _media_type, _url: "",
    )
    version = _video("video-new", status="RUNNING", selected=0)

    changed = await service.refresh(_workflow(), [version])

    assert changed is True
    assert version.status == "FAILED"
    assert read_json_object(version.output_summary_json)["error"] == "provider failed"
    assert db.added == []
    assert db.commits == 1
