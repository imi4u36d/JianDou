from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend_core.schemas import (
    AdminOverview,
    AdminTraceEvent,
    AdminTaskBatchRequest,
    AdminTaskBatchResult,
    TaskDetail,
    TaskDeleteResult,
    TaskListItem,
    TaskStatus,
    TaskTraceEvent,
)


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverview)
def get_admin_overview(request: Request) -> AdminOverview:
    return request.app.state.runtime.service.get_admin_overview()


@router.get("/tasks", response_model=list[TaskListItem])
def list_admin_tasks(
    request: Request,
    q: str | None = Query(default=None),
    status: TaskStatus | None = Query(default=None),
) -> list[TaskListItem]:
    normalized_q = q.strip() if q else None
    normalized_status = status.value if status is not None else None
    return request.app.state.runtime.service.list_tasks(
        q=normalized_q,
        status=normalized_status,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_admin_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.get_task_detail(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/trace", response_model=list[TaskTraceEvent])
def get_admin_task_trace(
    request: Request,
    task_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[TaskTraceEvent]:
    try:
        return request.app.state.runtime.service.get_task_trace(task_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/traces", response_model=list[AdminTraceEvent])
def list_admin_traces(
    request: Request,
    limit: int = Query(default=200, ge=1, le=2000),
    task_id: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    level: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[AdminTraceEvent]:
    return request.app.state.runtime.service.list_admin_traces(
        limit=limit,
        task_id=task_id.strip() if task_id else None,
        stage=stage.strip() if stage else None,
        level=level.strip() if level else None,
        q=q.strip() if q else None,
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskDetail)
def retry_admin_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.retry_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/terminate", response_model=TaskDetail)
def terminate_admin_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.terminate_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/tasks/{task_id}", response_model=TaskDeleteResult)
def delete_admin_task(request: Request, task_id: str) -> TaskDeleteResult:
    try:
        return request.app.state.runtime.service.delete_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/bulk-delete", response_model=AdminTaskBatchResult)
def bulk_delete_admin_tasks(request: Request, payload: AdminTaskBatchRequest) -> AdminTaskBatchResult:
    return request.app.state.runtime.service.bulk_delete_tasks(payload.taskIds)


@router.post("/tasks/bulk-retry", response_model=AdminTaskBatchResult)
def bulk_retry_admin_tasks(request: Request, payload: AdminTaskBatchRequest) -> AdminTaskBatchResult:
    return request.app.state.runtime.service.bulk_retry_tasks(payload.taskIds)
