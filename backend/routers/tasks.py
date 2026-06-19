"""任务管理路由。

接入 TaskApplicationService 真实服务层，替换原有的内存 stub。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend.auth import get_current_user
from backend.schemas.task import (
    CreateGenerationTaskRequest,
    GenerateCreativePromptRequest,
    RateTaskEffectRequest,
)

router = APIRouter(prefix="/api/v3/tasks", tags=["tasks"])


# ── helpers ──────────────────────────────────────────────────────────────

def _svc(request: Request):
    """从 app.state 获取 TaskApplicationService 实例。"""
    svc = request.app.state.task_application_service
    if svc is None:
        raise HTTPException(status_code=500, detail="task service not configured")
    return svc


async def _uid(request: Request) -> int:
    """获取当前登录用户 ID，未登录则返回 401。"""
    user = await get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return user["id"]


# ── 公开接口（无需登录） ─────────────────────────────────────────────────

@router.get("/showcase")
async def list_showcase_tasks(request: Request):
    return await _svc(request).showcase_cases()


@router.get("/seedance/{remote_task_id}")
async def get_seedance_task_result(remote_task_id: str, request: Request):
    return await _svc(request).get_seedance_task_result(remote_task_id)


# ── 任务 CRUD ────────────────────────────────────────────────────────────

@router.get("")
async def list_tasks(
    request: Request,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort: str | None = Query(default=None),
):
    user_id = await _uid(request)
    return await _svc(request).list_tasks(user_id, q=q, status=status, sort=sort)


@router.post("/generation")
async def create_generation_task(body: CreateGenerationTaskRequest, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).create_generation_task_for_user(user_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/generate-prompt")
async def generate_creative_prompt(body: GenerateCreativePromptRequest, request: Request):
    """生成创意提示词。"""
    await _uid(request)
    title = (body.title or "").strip() or "Unnamed Task"
    prompt = (
        f"Short drama style, emotional progression, facial expressions "
        f"fitting the context, realistic cinematography, dialogue and "
        f"voiceover matching plot: {title}"
    )
    return {"prompt": prompt, "source": "default"}


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_task(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── 子集合 ───────────────────────────────────────────────────────────────

@router.get("/{task_id}/trace")
async def get_task_trace(
    task_id: str,
    request: Request,
    limit: int = Query(default=500, ge=1, le=2000),
):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_trace(task_id, user_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    request: Request,
    limit: int = Query(default=500, ge=1, le=2000),
):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_logs(task_id, user_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{task_id}/status-history")
async def get_task_status_history(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_status_history(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{task_id}/model-calls")
async def get_task_model_calls(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_model_calls(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{task_id}/results")
async def get_task_results(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_results(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{task_id}/materials")
async def get_task_materials(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).get_materials(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── 生命周期操作 ─────────────────────────────────────────────────────────

@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        result = await _svc(request).delete_task(task_id, user_id)
        return {"success": True, "task_id": result.get("taskId", task_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{task_id}/retry")
async def retry_task(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).retry_task(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{task_id}/pause")
async def pause_task(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).pause_task(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{task_id}/continue")
async def continue_task(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).continue_task(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{task_id}/terminate")
async def terminate_task(task_id: str, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).terminate_task(task_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{task_id}/effect-rating")
async def rate_task_effect(task_id: str, body: RateTaskEffectRequest, request: Request):
    user_id = await _uid(request)
    try:
        return await _svc(request).rate_task_effect(task_id, user_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
