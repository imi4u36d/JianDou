from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _random_id() -> str:
    return uuid.uuid4().hex


def _write_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


class WorkflowPersistenceRowFactory:
    """Create ORM rows for workflow-owned persistence records."""

    def __init__(
        self,
        *,
        now: Callable[[], str] = _now_iso,
        random_id: Callable[[], str] = _random_id,
    ) -> None:
        self._now = now
        self._random_id = random_id

    def create_material_asset(
        self,
        *,
        wf: BizStageWorkflow,
        stage_type: str,
        clip_index: int,
        version_no: int,
        media_type: str,
        title: str,
        public_url: str,
        mime_type: str = "",
        width: int = 0,
        height: int = 0,
        duration_seconds: float = 0,
        origin_provider: str = "",
        origin_model: str = "",
        remote_task_id: str = "",
        remote_url: str = "",
        thumbnail_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> BizMaterialAsset:
        now = self._now()
        return BizMaterialAsset(
            material_asset_id=f"mat_{self._random_id()[:16]}",
            remark="",
            owner_user_id=wf.owner_user_id,
            task_id="",
            workflow_id=wf.workflow_id,
            source_task_id="",
            source_material_id="",
            asset_role=stage_type,
            stage_type=stage_type,
            clip_index=clip_index,
            version_no=version_no,
            selected_for_next=1,
            media_type=media_type,
            title=title,
            user_rating=None,
            rating_note="",
            origin_provider=origin_provider,
            origin_model=origin_model,
            remote_task_id=remote_task_id,
            remote_asset_id="",
            original_file_name="",
            stored_file_name="",
            file_ext="",
            storage_provider="local",
            mime_type=mime_type,
            size_bytes=0,
            sha256="",
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            has_audio=1 if media_type == "video" else 0,
            local_storage_path="",
            local_file_path="",
            public_url=public_url,
            thumbnail_url=thumbnail_url,
            third_party_url="",
            remote_url="",
            metadata_json=_write_json(metadata or {}),
            captured_at=now,
            timezone_offset_minutes=0,
            create_time=now,
            update_time=now,
            is_deleted=0,
        )

    def create_stage_version(
        self,
        *,
        wf: BizStageWorkflow,
        stage_version_id: str,
        stage_type: str,
        clip_index: int,
        version_no: int,
        title: str,
        status: str,
        selected: int = 0,
        parent_version_id: str = "",
        source_material_asset_id: str = "",
        material_asset_id: str = "",
        preview_url: str = "",
        download_url: str = "",
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
        model_call_summary: dict[str, Any] | None = None,
    ) -> BizStageVersion:
        now = self._now()
        return BizStageVersion(
            stage_version_id=stage_version_id,
            workflow_id=wf.workflow_id,
            owner_user_id=wf.owner_user_id,
            stage_type=stage_type,
            clip_index=clip_index,
            version_no=version_no,
            title=title,
            status=status,
            selected=selected,
            rating_note="",
            parent_version_id=parent_version_id,
            source_material_asset_id=source_material_asset_id,
            material_asset_id=material_asset_id,
            preview_url=preview_url,
            download_url=download_url,
            input_summary_json=_write_json(input_summary or {}),
            output_summary_json=_write_json(output_summary or {}),
            model_call_summary_json=_write_json(model_call_summary or {}),
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )
