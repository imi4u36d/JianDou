"""
Workflow API router — delegates to WorkflowService.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.errors import bad_request, not_found
from backend.routers.workflow_route_support import (
    run_workflow_action as _run_action,
)
from backend.routers.workflow_route_support import (
    save_aspect_ratio_preference as _save_aspect_ratio_preference,
)
from backend.routers.workflow_route_support import (
    workflow_service as _service,
)
from backend.routers.workflow_stage_routes import router as stage_router
from backend.schemas.workflow import (
    CreateWorkflowRequest,
    RateStageVersionRequest,
    RateWorkflowRequest,
    UpdateWorkflowSettingsRequest,
    WorkflowActionResponse,
    WorkflowDeleteResult,
    WorkflowDetailResponse,
    WorkflowListPageResponse,
    WorkflowListResponse,
)
from backend.shared import now_iso

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/workflows", tags=["workflows"])
router.include_router(stage_router)


# ------------------------------------------------------------------
# Workflow CRUD
# ------------------------------------------------------------------


@router.get("", response_model=WorkflowListResponse | WorkflowListPageResponse)
async def list_workflows(
    request: Request,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    offset: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]] | dict[str, Any]:
    """List all workflows for the current user."""
    user = await require_user(request)
    svc = _service(db, request)
    return await svc.list_workflows(owner_user_id=user["id"], q=q, status=status, sort=sort, offset=offset, limit=limit)


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
    await _save_aspect_ratio_preference(request, user["id"], result.get("aspectRatio"))
    if result.get("executionMode") == "auto":
        result = await _run_action(
            lambda: svc._update_auto_pilot_fields(
                result["id"],
                owner_user_id=user["id"],
                auto_pilot_state="queued",
            )
        )
        if result is None:
            raise bad_request("Failed to start auto workflow")
        runner = getattr(request.app.state, "auto_pilot_runner", None)
        if runner is not None:
            runner.enqueue(result["id"], user["id"])
            result["queuePosition"] = runner.queue_position_of(result["id"])
            result["queueSize"] = runner.queue_size()
    return result


@router.post("/{workflow_id}/auto-pilot/start", response_model=WorkflowDetailResponse)
async def start_auto_pilot(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start auto-pilot for a workflow (sets mode to auto, state to queued)."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await _run_action(
        lambda: svc._update_auto_pilot_fields(
            workflow_id,
            owner_user_id=user["id"],
            execution_mode="auto",
            auto_pilot_state="queued",
        )
    )
    if result is None:
        raise not_found("workflow")
    # Enqueue for processing if in auto mode
    runner = getattr(request.app.state, "auto_pilot_runner", None)
    if runner is not None:
        runner.enqueue(workflow_id, user["id"])
        if result.get("autoPilotState") == "queued":
            result["queuePosition"] = runner.queue_position_of(workflow_id)
            result["queueSize"] = runner.queue_size()
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
            auto_pilot_state="queued",
        )
    )
    if result is None:
        raise not_found("workflow")
    # Enqueue for processing
    runner = getattr(request.app.state, "auto_pilot_runner", None)
    if runner is not None:
        runner.enqueue(workflow_id, user["id"])
        if result.get("autoPilotState") == "queued":
            result["queuePosition"] = runner.queue_position_of(workflow_id)
            result["queueSize"] = runner.queue_size()
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
    # Enrich with queue info when workflow is queued
    if result.get("autoPilotState") == "queued":
        runner = getattr(request.app.state, "auto_pilot_runner", None)
        if runner is not None:
            result["queuePosition"] = runner.queue_position_of(workflow_id)
            result["queueSize"] = runner.queue_size()
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
    await _save_aspect_ratio_preference(request, user["id"], result.get("aspectRatio"))
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


@router.delete("/{workflow_id}/versions", response_model=WorkflowActionResponse)
async def delete_all_stage_versions(
    workflow_id: str,
    request: Request,
    stage_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete all non-deleted stage versions for a workflow, optionally filtered by stage type."""
    user = await require_user(request)
    svc = _service(db, request)
    result = await svc.delete_all_stage_versions(workflow_id, owner_user_id=user["id"], stage_type=stage_type)
    if result is None:
        raise not_found("workflow")
    return result
