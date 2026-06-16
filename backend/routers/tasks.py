from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from backend.config import settings
from backend.routers.auth import get_current_user
from backend.schemas.task import (
    TaskListItemResponse,
    TaskDetailResponse,
    CreateGenerationTaskRequest,
    GenerateCreativePromptRequest,
    RateTaskEffectRequest,
    TaskDeleteResult,
)

router = APIRouter(prefix="/api/v3/tasks", tags=["tasks"])

# In-memory task store (skeleton)
_tasks: dict[str, dict] = {}
_next_id = 1


@router.get("")
async def list_tasks(request: Request):
    return []


@router.get("/showcase")
async def list_showcase_tasks(request: Request):
    return []


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return task


@router.post("/generation")
async def create_generation_task(request: Request):
    global _next_id
    body = await request.json()
    tid = str(_next_id)
    _next_id += 1
    task = {
        "id": tid,
        "task_type": "generation",
        "title": body.get("title", ""),
        "status": "QUEUED",
        "progress": 0,
        "created_at": "2026-06-14T00:00:00Z",
        "updated_at": "2026-06-14T00:00:00Z",
        "source_file_name": settings.source_file_name,
        "aspect_ratio": body.get("aspect_ratio", settings.default_aspect_ratio),
        "min_duration_seconds": body.get("min_duration_seconds", settings.default_duration_seconds),
        "max_duration_seconds": body.get("max_duration_seconds", settings.default_duration_seconds),
        "retry_count": 0,
        "is_queued": True,
        "current_stage": "initializing",
        "editing_mode": settings.editing_mode,
        "source_assets": [],
    }
    _tasks[tid] = task
    return task


@router.post("/generation/creative-prompt")
async def generate_creative_prompt(request: Request):
    body = await request.json()
    return {
        "creative_prompt": body.get("title", ""),
        "aspect_ratio": body.get("aspect_ratio", settings.default_aspect_ratio),
        "min_duration_seconds": body.get("min_duration_seconds", settings.default_duration_seconds),
        "max_duration_seconds": body.get("max_duration_seconds", settings.default_duration_seconds),
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="task_not_found")
    del _tasks[task_id]
    return {"success": True, "task_id": task_id}


@router.get("/{task_id}/trace")
async def get_task_trace(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return []


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return []


@router.get("/{task_id}/status-history")
async def get_task_status_history(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return []


@router.get("/{task_id}/model-calls")
async def get_task_model_calls(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return []


@router.get("/{task_id}/results")
async def get_task_results(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return []


@router.get("/{task_id}/materials")
async def get_task_materials(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return []


@router.post("/{task_id}/retry")
async def retry_task(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    task["status"] = "QUEUED"
    task["retry_count"] = task.get("retry_count", 0) + 1
    return task


@router.post("/{task_id}/pause")
async def pause_task(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    task["status"] = "PAUSED"
    return task


@router.post("/{task_id}/continue")
async def continue_task(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    task["status"] = "QUEUED"
    return task


@router.post("/{task_id}/terminate")
async def terminate_task(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    task["status"] = "TERMINATED"
    return task


@router.post("/{task_id}/effect-rating")
async def rate_task_effect(task_id: str, request: Request):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    body = await request.json()
    task["effect_rating"] = body.get("effect_rating")
    task["effect_rating_note"] = body.get("effect_rating_note", "")
    return task
