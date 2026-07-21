"""Persist material-library choices as workflow public-asset versions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage
from backend.domain.json_payloads import write_json_object
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_stage_mutation_store import WorkflowStageMutationStore
from backend.shared import now_iso, random_id, trim


async def persist_visual_asset_selection(
    db: AsyncSession,
    store: WorkflowStageMutationStore,
    workflow: BizStageWorkflow,
    clip_index: int,
    asset_id: str,
    owner_user_id: int | None,
) -> None:
    asset = await store.find_asset(asset_id, owner_user_id)
    if asset is None:
        raise ValueError("所选公共素材不存在或无权访问。")
    if clip_index < 1000:
        raise ValueError("公共素材虚拟镜头编号无效。")
    versions = [
        version
        for version in await store.list_stage_versions(workflow.workflow_id)
        if version.stage_type == WorkflowStage.KEYFRAME.value and version.clip_index == clip_index
    ]
    version_no = max((version.version_no or 0 for version in versions), default=0) + 1
    asset_type = trim(asset.asset_role, "other")
    if asset_type == "character_sheet":
        asset_type = "character"
    variant_kind = "character_sheet" if asset_type == "character" else "visual_asset"
    public_url = trim(asset.public_url) or trim(asset.remote_url) or trim(asset.third_party_url)
    timestamp = now_iso()
    version = BizStageVersion(
        stage_version_id=f"kv_{random_id()[:12]}",
        workflow_id=workflow.workflow_id,
        owner_user_id=workflow.owner_user_id,
        stage_type=WorkflowStage.KEYFRAME.value,
        clip_index=clip_index,
        version_no=version_no,
        title=asset.title or "公共素材",
        status="COMPLETED",
        selected=1,
        rating_note="",
        parent_version_id="",
        source_material_asset_id=asset.material_asset_id,
        material_asset_id=asset.material_asset_id,
        preview_url=public_url,
        download_url=public_url,
        input_summary_json=write_json_object({
            "variantKind": variant_kind,
            "assetType": asset_type,
            "source": "material_library",
        }),
        output_summary_json=write_json_object({
            "fileUrl": public_url,
            "previewUrl": public_url,
            "sheetUrl": public_url,
            "remoteSourceUrl": public_url,
        }),
        model_call_summary_json="{}",
        timezone_offset_minutes=0,
        remark="",
        create_time=timestamp,
        update_time=timestamp,
        is_deleted=0,
    )
    for candidate in versions:
        candidate.selected = 0
        candidate.update_time = timestamp
    db.add(version)
