"""Admin task list, lifecycle, trace, and diagnosis routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.auth import require_admin
from backend.errors import bad_request, not_found
from backend.schemas.admin import (
    AdminBulkTerminateTasksRequest,
    AdminTaskBatchActionRequest,
    AdminTaskBatchResult,
)

router = APIRouter()


def _bounded_query_int(request: Request, key: str, default: int, maximum: int) -> int:
    try:
        return max(1, min(int(request.query_params.get(key, str(default))), maximum))
    except (ValueError, TypeError):
        return default


@router.get("/tasks")
async def admin_list_tasks(request: Request):
    await require_admin(request)
    params = request.query_params
    app_service = request.app.state.task_application_service
    try:
        offset = max(0, int(params.get("offset", "0")))
    except (ValueError, TypeError):
        offset = 0
    return await app_service.admin_list_tasks(
        q=params.get("q") or None,
        status=params.get("status") or None,
        sort=params.get("sort") or None,
        offset=offset,
        limit=_bounded_query_int(request, "limit", 20, 200),
    )


async def _terminate_tasks(app_service, task_ids: list[str]) -> tuple[list[str], list[dict]]:  # noqa: ANN001
    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in task_ids:
        try:
            await app_service.admin_terminate_task(task_id)
            succeeded.append(task_id)
        except Exception as exc:
            failed.append({"taskId": task_id, "error": str(exc)})
    return succeeded, failed


@router.post("/tasks/batch-action")
async def admin_batch_task_action(body: AdminTaskBatchActionRequest, request: Request):
    await require_admin(request)
    succeeded, failed = await _terminate_tasks(
        request.app.state.task_application_service, body.task_ids
    )
    return {
        "action": body.action,
        "requested_count": len(body.task_ids),
        "succeeded_task_ids": succeeded,
        "failed": failed,
    }


@router.post("/tasks/{task_id}/terminate")
async def admin_terminate_single_task(task_id: str, request: Request):
    await require_admin(request)
    try:
        await request.app.state.task_application_service.admin_terminate_task(task_id)
    except Exception as exc:
        raise bad_request(exc)
    return {"success": True, "taskId": task_id}


@router.post("/tasks/bulk-terminate", response_model=AdminTaskBatchResult)
async def admin_bulk_terminate_tasks(body: AdminBulkTerminateTasksRequest, request: Request):
    await require_admin(request)
    succeeded, failed = await _terminate_tasks(
        request.app.state.task_application_service, body.task_ids
    )
    return {
        "action": "terminate",
        "requestedCount": len(body.task_ids),
        "succeededTaskIds": succeeded,
        "failed": failed,
    }


@router.post("/tasks/bulk-delete")
async def admin_bulk_delete_tasks(body: AdminBulkTerminateTasksRequest, request: Request):
    admin_user = await require_admin(request)
    app_service = request.app.state.task_application_service
    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in body.task_ids:
        try:
            await app_service.delete_task(task_id, admin_user["id"])
            succeeded.append(task_id)
        except Exception as exc:
            failed.append({"taskId": task_id, "error": str(exc)})
    return {
        "action": "delete",
        "requestedCount": len(body.task_ids),
        "succeededTaskIds": succeeded,
        "failed": failed,
    }


@router.get("/tasks/{task_id}")
async def admin_get_task(task_id: str, request: Request):
    await require_admin(request)
    try:
        return await request.app.state.task_application_service.admin_get_task(task_id)
    except Exception as exc:
        raise not_found(str(exc))


@router.get("/tasks/{task_id}/trace")
async def admin_get_task_trace(task_id: str, request: Request):
    await require_admin(request)
    try:
        task = await request.app.state.task_application_service.admin_get_task(task_id)
        return task.get("trace", [])[-_bounded_query_int(request, "limit", 50, 500) :]
    except Exception as exc:
        raise not_found(str(exc))


@router.get("/tasks/{task_id}/diagnosis")
async def admin_get_task_diagnosis(task_id: str, request: Request):
    await require_admin(request)
    try:
        task = await request.app.state.task_application_service.admin_get_task(task_id)
    except Exception as exc:
        raise not_found(str(exc))
    severity = "info"
    if task.get("status") == "FAILED":
        severity = "high"
    elif task.get("progress", 0) < 50 and task.get("status") in (
        "ANALYZING",
        "PLANNING",
        "RENDERING",
    ):
        severity = "medium"
    return {
        "taskId": task_id,
        "title": task.get("title", ""),
        "status": task.get("status", ""),
        "severity": severity,
        "summary": task.get("failureReason", ""),
        "findings": [],
        "recovery": {},
        "continuity": {},
        "outputs": {},
        "queue": {},
    }


@router.post("/tasks/{task_id}/retry")
async def admin_retry_task(task_id: str, request: Request):
    admin_user = await require_admin(request)
    try:
        return await request.app.state.task_application_service.retry_task(task_id, admin_user["id"])
    except Exception as exc:
        raise bad_request(exc)


@router.delete("/tasks/{task_id}")
async def admin_delete_task(task_id: str, request: Request):
    admin_user = await require_admin(request)
    try:
        await request.app.state.task_application_service.delete_task(task_id, admin_user["id"])
    except Exception as exc:
        raise bad_request(exc)
    return {"success": True, "taskId": task_id}
