from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.domain.json_payloads import read_json_object
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_finalization_service import WorkflowFinalizationService
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


class _FakeMediaService:
    def __init__(self) -> None:
        self.materialized: list[str] = []
        self.concatenated: list[str] = []

    def materialize_artifact(self, source_url: str, _relative_dir: str, _file_name: str):
        self.materialized.append(source_url)
        return SimpleNamespace(public_url=f"local:{source_url}")

    def concat_videos(self, _relative_dir: str, _file_name: str, segment_urls: list[str]):
        self.concatenated = segment_urls
        return SimpleNamespace(public_url="https://cdn.example/joined.mp4")


def _workflow() -> BizStageWorkflow:
    return BizStageWorkflow(
        workflow_id="wf-final",
        owner_user_id=7,
        title="Final workflow",
        final_join_asset_id="",
        current_stage="video",
        status="READY",
        update_time="2026-01-01T00:00:00Z",
    )


def _video(clip_index: int, duration: float) -> BizStageVersion:
    return BizStageVersion(
        stage_version_id=f"video-{clip_index}",
        stage_type="video",
        clip_index=clip_index,
        selected=1,
        preview_url=f"https://cdn.example/{clip_index}.mp4",
        download_url=f"https://cdn.example/{clip_index}.mp4",
        output_summary_json=f'{{"durationSeconds": {duration}}}',
        is_deleted=0,
    )


@pytest.mark.asyncio
async def test_finalize_concatenates_clips_in_storyboard_order() -> None:
    db = _FakeDb()
    media = _FakeMediaService()
    service = WorkflowFinalizationService(
        db,  # type: ignore[arg-type]
        media_service=media,
        row_factory=WorkflowPersistenceRowFactory(
            now=lambda: "2026-07-10T00:00:00Z",
            random_id=lambda: "asset-identifier",
        ),
        thumbnail_resolver=lambda _media_type, _url: "https://cdn.example/thumb.webp",
    )
    workflow = _workflow()

    asset = await service.finalize(workflow, [_video(2, 6.5), _video(1, 5.0)])

    assert media.concatenated == [
        "local:https://cdn.example/1.mp4",
        "local:https://cdn.example/2.mp4",
    ]
    assert asset.public_url == "https://cdn.example/joined.mp4"
    assert asset.duration_seconds == 11.5
    assert read_json_object(asset.metadata_json)["sourceVideoVersionIds"] == ["video-1", "video-2"]
    assert workflow.final_join_asset_id == asset.material_asset_id
    assert workflow.current_stage == "joined"
    assert workflow.status == "COMPLETED"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_finalize_requires_a_selected_video() -> None:
    service = WorkflowFinalizationService(
        _FakeDb(),  # type: ignore[arg-type]
        media_service=None,
        row_factory=WorkflowPersistenceRowFactory(),
        thumbnail_resolver=lambda _media_type, _url: "",
    )

    with pytest.raises(ValueError, match="请先为每个镜头选中视频版本"):
        await service.finalize(_workflow(), [])
