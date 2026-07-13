"""Workflow storyboard, character, keyframe, and video routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.errors import not_found
from backend.routers.workflow_route_support import run_workflow_action, workflow_service
from backend.schemas.workflow import (
    AdjustStoryboardRequest,
    SelectCharacterSheetAssetRequest,
    WorkflowDetailResponse,
)

router = APIRouter()


@router.post("/{workflow_id}/storyboards/generate", response_model=WorkflowDetailResponse)
async def generate_storyboard(workflow_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    user = await require_user(request)
    service = workflow_service(db, request)
    result = await run_workflow_action(
        lambda: service.generate_storyboard(workflow_id, owner_user_id=user["id"])
    )
    if result is None:
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/storyboards/{version_id}/select", response_model=WorkflowDetailResponse)
async def select_storyboard(
    workflow_id: str, version_id: str, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    user = await require_user(request)
    result = await workflow_service(db, request).select_storyboard(
        workflow_id, version_id, owner_user_id=user["id"]
    )
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
    user = await require_user(request)
    result = await workflow_service(db, request).adjust_storyboard(
        workflow_id, version_id, payload.prompt or "", owner_user_id=user["id"]
    )
    if result is None:
        raise not_found("workflow_or_version")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/keyframes/generate", response_model=WorkflowDetailResponse)
async def generate_keyframe(
    workflow_id: str, clip_index: int, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    user = await require_user(request)
    service = workflow_service(db, request)
    result = await run_workflow_action(
        lambda: service.generate_keyframe(workflow_id, clip_index, owner_user_id=user["id"])
    )
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
    user = await require_user(request)
    service = workflow_service(db, request)
    result = await run_workflow_action(
        lambda: service.generate_keyframe_frame(
            workflow_id, clip_index, frame_role, owner_user_id=user["id"]
        )
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
    user = await require_user(request)
    result = await workflow_service(db, request).select_keyframe(
        workflow_id, clip_index, version_id, owner_user_id=user["id"]
    )
    if result is None:
        raise not_found("workflow_or_version")
    return result


@router.post(
    "/{workflow_id}/clips/{clip_index}/keyframes/{version_id}/frames/{frame_role}/select",
    response_model=WorkflowDetailResponse,
)
async def select_keyframe_frame(
    workflow_id: str,
    clip_index: int,
    version_id: str,
    frame_role: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    user = await require_user(request)
    result = await workflow_service(db, request).select_keyframe_frame(
        workflow_id, clip_index, version_id, frame_role, owner_user_id=user["id"]
    )
    if result is None:
        raise not_found("workflow_or_version")
    return result


@router.post("/{workflow_id}/character-sheets/{character_index}/generate", response_model=WorkflowDetailResponse)
async def generate_character_sheet(
    workflow_id: str, character_index: int, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    user = await require_user(request)
    service = workflow_service(db, request)
    result = await run_workflow_action(
        lambda: service.generate_character_sheet(
            workflow_id, character_index, owner_user_id=user["id"]
        )
    )
    if result is None:
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/character-sheets/{clip_index}/select-asset", response_model=WorkflowDetailResponse)
async def select_character_sheet_asset(
    workflow_id: str,
    clip_index: int,
    payload: SelectCharacterSheetAssetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    user = await require_user(request)
    result = await workflow_service(db, request).select_character_sheet_asset(
        workflow_id, clip_index, payload.asset_id, owner_user_id=user["id"]
    )
    if result is None:
        raise not_found("workflow")
    return result


@router.post("/{workflow_id}/clips/{clip_index}/videos/generate", response_model=WorkflowDetailResponse)
async def generate_video(
    workflow_id: str, clip_index: int, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    user = await require_user(request)
    service = workflow_service(db, request)
    result = await run_workflow_action(
        lambda: service.generate_video(workflow_id, clip_index, owner_user_id=user["id"])
    )
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
    user = await require_user(request)
    result = await workflow_service(db, request).select_video(
        workflow_id, clip_index, version_id, owner_user_id=user["id"]
    )
    if result is None:
        raise not_found("workflow_or_version")
    return result
