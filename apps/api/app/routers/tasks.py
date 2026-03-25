from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend_core.schemas import CreateTaskRequest, TaskDetail, TaskListItem


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


@router.get("/tasks", response_model=list[TaskListItem])
def list_tasks(request: Request) -> list[TaskListItem]:
    return request.app.state.runtime.service.list_tasks()


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.get_task_detail(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=TaskDetail)
def retry_task(request: Request, task_id: str) -> TaskDetail:
    try:
        return request.app.state.runtime.service.retry_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
