from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend_core.schemas import (
    CreateTaskRequest,
    GenerateCreativePromptRequest,
    GenerateCreativePromptResponse,
    SeeddanceTaskQueryResponse,
    TaskDeleteResult,
    TaskDetail,
    TaskDraft,
    TaskListItem,
    TaskStatus,
    TaskTraceEvent,
)


router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskDetail)
def create_task(request: Request, payload: CreateTaskRequest) -> TaskDetail:
    runtime = request.app.state.runtime
    try:
        return runtime.service.create_task(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/generate-prompt", response_model=GenerateCreativePromptResponse)
def generate_creative_prompt(request: Request, payload: GenerateCreativePromptRequest) -> GenerateCreativePromptResponse:
    try:
        return request.app.state.runtime.service.generate_creative_prompt(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks", response_model=list[TaskListItem])
def list_tasks(
    request: Request,
    q: str | None = Query(default=None),
    status: TaskStatus | None = Query(default=None),
    platform: str | None = Query(default=None),
) -> list[TaskListItem]:
    normalized_q = q.strip() if q else None
    normalized_platform = platform.strip() if platform else None
    normalized_status = status.value if status is not None else None
    return request.app.state.runtime.service.list_tasks(
        q=normalized_q,
        status=normalized_status,
        platform=normalized_platform,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.get_task_detail(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/trace", response_model=list[TaskTraceEvent])
def get_task_trace(
    request: Request,
    task_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[TaskTraceEvent]:
    try:
        return request.app.state.runtime.service.get_task_trace(task_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/seeddance/{remote_task_id}", response_model=SeeddanceTaskQueryResponse)
def query_seeddance_task_result(request: Request, remote_task_id: str) -> SeeddanceTaskQueryResponse:
    try:
        return request.app.state.runtime.service.query_seeddance_task_result(remote_task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/clone", response_model=TaskDraft)
def clone_task(request: Request, task_id: str) -> TaskDraft:
    try:
        return request.app.state.runtime.service.clone_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=TaskDetail)
def retry_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.retry_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/tasks/{task_id}", response_model=TaskDeleteResult)
def delete_task(request: Request, task_id: str) -> TaskDeleteResult:
    try:
        return request.app.state.runtime.service.delete_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
