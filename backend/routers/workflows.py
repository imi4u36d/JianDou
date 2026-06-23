"""
Workflow API router — delegates to WorkflowService.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.errors import bad_gateway, bad_request, not_found
from backend.exceptions import GenerationProviderError
from backend.schemas.workflow import (
    AdjustStoryboardRequest,
    CreateWorkflowRequest,
    RateStageVersionRequest,
    RateWorkflowRequest,
    SelectCharacterSheetAssetRequest,
    UpdateWorkflowSettingsRequest,
    WorkflowActionResponse,
    WorkflowDeleteResult,
    WorkflowDetailResponse,
    WorkflowListResponse,
    WorkflowSummaryResponse,
)
from backend.services.workflow_service import WorkflowService, now_iso

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/workflows", tags=["workflows"])


def _service(db: AsyncSession, request: Request | None = None) -> WorkflowService:
    generation_service = getattr(request.app.state, "generation_application_service", None) if request else None
    return WorkflowService(db, generation_service=generation_service)


async def _run_action(action):
    try:
        return await action()
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    except GenerationProviderError as exc:
        raise bad_gateway(str(exc) or exc.__class__.__name__) from exc


# ------------------------------------------------------------------
# Workflow CRUD
# ------------------------------------------------------------------


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all workflows for the current user."""
    user = await require_user(request)
    svc = _service(db, request)
    return await svc.list_workflows(owner_user_id=user["id"])


@router.post("", response_model=WorkflowDetailResponse)
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
        raise bad_request("Failed to create workflow")
    return result


@router.post("/{workflow_id}/auto-pilot/start", response_model=WorkflowDetailResponse)
async def start_auto_pilot(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start auto-pilot for a workflow (sets mode to auto, state to running)."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc._update_auto_pilot_fields(
            workflow_id,
            owner_user_id=user["id"],
            execution_mode="auto",
            auto_pilot_state="running",
            auto_pilot_started_at=now_iso(),
        )
    )
    if result is None:
        raise not_found("workflow")
    # Enqueue for processing if in auto mode
    runner = getattr(request.app.state, "auto_pilot_runner", None)
    if runner is not None:
        runner.enqueue(workflow_id, user["id"])
    return result


@router.post("/{workflow_id}/auto-pilot/pause", response_model=WorkflowDetailResponse)
async def pause_auto_pilot(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Pause auto-pilot for a workflow."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc._update_auto_pilot_fields(
            workflow_id,
            owner_user_id=user["id"],
            auto_pilot_state="paused",
            auto_pilot_paused_at=now_iso(),
        )
    )
    if result is None:
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/auto-pilot/resume", response_model=WorkflowDetailResponse)
async def resume_auto_pilot(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resume auto-pilot for a workflow."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc._update_auto_pilot_fields(
            workflow_id,
            owner_user_id=user["id"],
            execution_mode="auto",
            auto_pilot_state="running",
        )
    )
    if result is None:
        raise not_found("workflow")
    # Enqueue for processing
    runner = getattr(request.app.state, "auto_pilot_runner", None)
    if runner is not None:
        runner.enqueue(workflow_id, user["id"])
    return result


@router.post("/{workflow_id}/auto-pilot/terminate", response_model=WorkflowDetailResponse)
async def terminate_auto_pilot(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Terminate auto-pilot for a workflow (sets mode back to manual)."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc._update_auto_pilot_fields(
            workflow_id,
            owner_user_id=user["id"],
            execution_mode="manual",
            auto_pilot_state="idle",
        )
    )
    if result is None:
        raise not_found("workflow")
    return result


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
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
        raise not_found("workflow")
    return WorkflowDeleteResult(deleted=result.get("deleted", True), workflow_id=workflow_id)


@router.patch("/{workflow_id}/settings", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


# ------------------------------------------------------------------
# Storyboard endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/storyboards/generate", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/storyboards/{version_id}/select", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow_or_version")
    return result


@router.post("/{workflow_id}/storyboards/{version_id}/adjust", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow_or_version")
    return result


# ------------------------------------------------------------------
# Keyframe endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/generate", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/{frame_role}/generate", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/{version_id}/select", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow_or_version")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/{version_id}/frames/{frame_role}/select", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow_or_version")
    return result


# ------------------------------------------------------------------
# Character sheet endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/character-sheets/{clip_index}/select-asset", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


# ------------------------------------------------------------------
# Video endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/clips/{clip_index}/videos/generate", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/videos/{version_id}/select", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow_or_version")
    return result


# ------------------------------------------------------------------
# Finalize & Rating endpoints
# ------------------------------------------------------------------


@router.post("/{workflow_id}/finalize", response_model=WorkflowDetailResponse)
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
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/rating", response_model=WorkflowActionResponse)
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
        raise not_found("workflow")
    return result


@router.patch("/{workflow_id}/versions/{version_id}/rating", response_model=WorkflowActionResponse)
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
        raise not_found("workflow_or_version")
    return result


@router.delete("/{workflow_id}/versions/{version_id}", response_model=WorkflowActionResponse)
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
        raise not_found("workflow_or_version")
    return result
