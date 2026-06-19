"""
Workflow API router — delegates to WorkflowService.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.schemas.workflow import (
    AdjustStoryboardRequest,
    CreateWorkflowRequest,
    RateStageVersionRequest,
    RateWorkflowRequest,
    SelectCharacterSheetAssetRequest,
    UpdateWorkflowSettingsRequest,
    WorkflowDeleteResult,
)
from backend.services.generation_service import GenerationProviderException
from backend.services.workflow_service import WorkflowService

router = APIRouter(prefix="/api/v3/workflows", tags=["workflows"])


def _service(db: AsyncSession, request: Request | None = None) -> WorkflowService:
    generation_service = getattr(request.app.state, "generation_application_service", None) if request else None
    return WorkflowService(db, generation_service=generation_service)


async def _run_action(action):
    try:
        return await action()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GenerationProviderException as exc:
        detail = str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=502, detail=f"模型服务请求失败：{detail}") from exc


# ------------------------------------------------------------------
# Workflow CRUD
# ------------------------------------------------------------------


@router.get("")
async def list_workflows(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all workflows for the current user."""
    user = await require_user(request)
    svc = _service(db, request)
    return await svc.list_workflows(owner_user_id=user["id"])


@router.post("")
async def create_workflow(
    payload: CreateWorkflowRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new workflow."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(lambda: svc.create_workflow(payload.to_service_dict(), owner_user_id=user["id"]))
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to create workflow")
    return result


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get workflow detail."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.get_workflow(workflow_id, owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.delete("/{workflow_id}", response_model=WorkflowDeleteResult)
async def delete_workflow(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkflowDeleteResult:
    """Delete a workflow."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.delete_workflow(workflow_id, owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return WorkflowDeleteResult(deleted=result.get("deleted", True), workflow_id=workflow_id)


@router.patch("/{workflow_id}/settings")
async def update_workflow_settings(
    workflow_id: str,
    payload: UpdateWorkflowSettingsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update workflow settings."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc.update_workflow_settings(workflow_id, payload.to_service_dict(), owner_user_id=user["id"])
    )
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


# ------------------------------------------------------------------
# Storyboard endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/storyboards/generate")
async def generate_storyboard(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a storyboard version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(lambda: svc.generate_storyboard(workflow_id, owner_user_id=user["id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.post("/{workflow_id}/storyboards/{version_id}/select")
async def select_storyboard(
    workflow_id: str,
    version_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Select a storyboard version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.select_storyboard(workflow_id, version_id, owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result


@router.post("/{workflow_id}/storyboards/{version_id}/adjust")
async def adjust_storyboard(
    workflow_id: str,
    version_id: str,
    payload: AdjustStoryboardRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Adjust a storyboard version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.adjust_storyboard(workflow_id, version_id, payload.prompt or "", owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result


# ------------------------------------------------------------------
# Keyframe endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/generate")
async def generate_keyframe(
    workflow_id: str,
    clip_index: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate keyframe for a clip."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(lambda: svc.generate_keyframe(workflow_id, clip_index, owner_user_id=user["id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/{frame_role}/generate")
async def generate_keyframe_frame(
    workflow_id: str,
    clip_index: int,
    frame_role: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate single keyframe frame."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc.generate_keyframe_frame(workflow_id, clip_index, frame_role, owner_user_id=user["id"])
    )
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/{version_id}/select")
async def select_keyframe(
    workflow_id: str,
    clip_index: int,
    version_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Select a keyframe version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.select_keyframe(workflow_id, clip_index, version_id, owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/{version_id}/frames/{frame_role}/select")
async def select_keyframe_frame(
    workflow_id: str,
    clip_index: int,
    version_id: str,
    frame_role: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Select a keyframe frame version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.select_keyframe_frame(
        workflow_id,
        clip_index,
        version_id,
        frame_role,
        owner_user_id=user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result


# ------------------------------------------------------------------
# Character sheet endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/character-sheets/{clip_index}/select-asset")
async def select_character_sheet_asset(
    workflow_id: str,
    clip_index: int,
    payload: SelectCharacterSheetAssetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Select a character sheet asset."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.select_character_sheet_asset(
        workflow_id,
        clip_index,
        payload.asset_id,
        owner_user_id=user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


# ------------------------------------------------------------------
# Video endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/clips/{clip_index}/videos/generate")
async def generate_video(
    workflow_id: str,
    clip_index: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate video for a clip."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(lambda: svc.generate_video(workflow_id, clip_index, owner_user_id=user["id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/videos/{version_id}/select")
async def select_video(
    workflow_id: str,
    clip_index: int,
    version_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Select a video version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.select_video(workflow_id, clip_index, version_id, owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result


# ------------------------------------------------------------------
# Finalize & Rating endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/finalize")
async def finalize_workflow(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Finalize a workflow."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(lambda: svc.finalize_workflow(workflow_id, owner_user_id=user["id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.post("/{workflow_id}/rating")
async def rate_workflow(
    workflow_id: str,
    payload: RateWorkflowRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Rate a workflow."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.rate_workflow(
        workflow_id,
        payload.effect_rating,
        payload.effect_rating_note or "",
        owner_user_id=user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return result


@router.patch("/{workflow_id}/versions/{version_id}/rating")
async def rate_stage_version(
    workflow_id: str,
    version_id: str,
    payload: RateStageVersionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Rate a stage version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.rate_stage_version(
        workflow_id,
        version_id,
        payload.effect_rating,
        payload.effect_rating_note or "",
        owner_user_id=user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result


@router.delete("/{workflow_id}/versions/{version_id}")
async def delete_stage_version(
    workflow_id: str,
    version_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a stage version."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.delete_stage_version(workflow_id, version_id, owner_user_id=user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="workflow_or_version_not_found")
    return result
