"""Admin router — administrative API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_admin
from backend.database import get_db
from backend.errors import bad_request, not_found
from backend.schemas.admin import (
    AdminAdjustCreditRequest,
    AdminBulkTerminateTasksRequest,
    AdminCreateInviteRequest,
    AdminCreateUserRequest,
    AdminModelConfigKeysRequest,
    AdminOverviewResponse,
    AdminTaskBatchActionRequest,
    AdminTaskBatchResult,
    AdminUpdateCreditRuleRequest,
    AdminUpdateUserPasswordRequest,
    AdminUpdateUserRequest,
    AdminUpdateUserStatusRequest,
)
from backend.services.auth_service import AuthService
from backend.services.credit_service import CreditService
from backend.services.model_config_service import AdminModelConfigKeyUpdateRequest as ModelConfigKeyUpdateRequest

router = APIRouter(prefix="/api/v3/admin", tags=["admin"])



@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview(request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    model_resolver = request.app.state.model_resolver
    overview = await app_service.admin_overview()

    # Check model readiness
    try:
        primary_model_key = model_resolver.value("model", "primary_model", "") or "claude-sonnet"
        text_profile = model_resolver.resolve_text_profile(primary_model_key)
        overview["modelReady"] = text_profile.ready
        overview["primaryModel"] = text_profile.config.model if text_profile.ready else None
        overview["textModel"] = text_profile.config.model if text_profile.ready else None
    except Exception:
        overview["modelReady"] = False

    return overview


@router.get("/tasks")
async def admin_list_tasks(request: Request):
    await require_admin(request)
    q = request.query_params.get("q", "")
    status = request.query_params.get("status", "")
    sort = request.query_params.get("sort", "")
    offset_raw = request.query_params.get("offset", "0")
    limit_raw = request.query_params.get("limit", "20")
    try:
        offset = max(0, int(offset_raw))
    except (ValueError, TypeError):
        offset = 0
    try:
        limit = max(1, min(int(limit_raw), 200))
    except (ValueError, TypeError):
        limit = 20
    app_service = request.app.state.task_application_service
    return await app_service.admin_list_tasks(
        q=q or None,
        status=status or None,
        sort=sort or None,
        offset=offset,
        limit=limit,
    )


@router.post("/tasks/batch-action")
async def admin_batch_task_action(body: AdminTaskBatchActionRequest, request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in body.task_ids:
        try:
            await app_service.admin_terminate_task(task_id)
            succeeded.append(task_id)
        except Exception as exc:
            failed.append({"taskId": task_id, "error": str(exc)})
    return {
        "action": body.action,
        "requested_count": len(body.task_ids),
        "succeeded_task_ids": succeeded,
        "failed": failed,
    }


@router.get("/traces")
async def admin_list_traces(request: Request):
    await require_admin(request)
    task_id = request.query_params.get("taskId", "")
    stage = request.query_params.get("stage", "")
    level = request.query_params.get("level", "")
    q = request.query_params.get("q", "")
    limit_raw = request.query_params.get("limit", "50")
    try:
        limit = max(1, min(int(limit_raw), 200))
    except (ValueError, TypeError):
        limit = 50
    logger = request.app.state.structured_logger
    traces = logger.list_recent_traces(
        task_id=task_id or None,
        stage=stage or None,
        level=level or None,
        query_text=q or None,
        limit=limit,
    )
    return traces


@router.get("/model-config")
async def admin_get_model_config(request: Request):
    user = await require_admin(request)
    config_service = request.app.state.user_model_config_service
    result = config_service.read(user["id"])
    return result


@router.put("/model-config/keys")
async def admin_update_model_config_keys(body: AdminModelConfigKeysRequest, request: Request):
    user = await require_admin(request)
    config_service = request.app.state.user_model_config_service
    provider_inputs = [
        ModelConfigKeyUpdateRequest.ProviderKeyInput(
            key=provider.key,
            apiKey=provider.api_key,
        )
        for provider in body.providers
    ]
    update_request = ModelConfigKeyUpdateRequest(providers=provider_inputs)
    result = config_service.save_keys(user["id"], update_request)
    return result


@router.post("/model-config/validate")
async def admin_validate_model_config_keys(body: AdminModelConfigKeysRequest, request: Request):
    user = await require_admin(request)
    config_service = request.app.state.user_model_config_service
    provider_inputs = [
        ModelConfigKeyUpdateRequest.ProviderKeyInput(
            key=provider.key,
            apiKey=provider.api_key,
        )
        for provider in body.providers
    ]
    update_request = ModelConfigKeyUpdateRequest(providers=provider_inputs)
    return config_service.validate_keys(user["id"], update_request)


@router.get("/users")
async def admin_list_users(request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    q = request.query_params.get("q", "")
    role = request.query_params.get("role", "")
    status_param = request.query_params.get("status", "")
    offset_raw = request.query_params.get("offset", "0")
    limit_raw = request.query_params.get("limit", "20")
    try:
        offset = max(0, int(offset_raw))
    except (ValueError, TypeError):
        offset = 0
    try:
        limit = max(1, min(int(limit_raw), 200))
    except (ValueError, TypeError):
        limit = 20
    auth_service = AuthService(db)
    return await auth_service.list_users(q, role, status_param, offset=offset, limit=limit)


@router.post("/users")
async def admin_create_user(body: AdminCreateUserRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        user = await auth_service.create_user(
            username=body.username,
            password=body.password,
            role=body.role,
            status=body.status,
            task_concurrency_limit=body.task_concurrency_limit,
        )
    except ValueError as exc:
        raise bad_request(exc)
    return user


@router.get("/users/{user_id}/model-config")
async def admin_get_user_model_config(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Get model config for a specific user (admin only)."""
    await require_admin(request)
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise not_found("user_not_found")
    if user.get("role") != "ADMIN":
        raise bad_request("普通用户不支持配置模型 Key")
    config_service = request.app.state.user_model_config_service
    return config_service.read(user_id)


@router.put("/users/{user_id}/model-config/keys")
async def admin_update_user_model_config_keys(
    user_id: int,
    body: AdminModelConfigKeysRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update model API keys for a specific user (admin only)."""
    await require_admin(request)
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise not_found("user_not_found")
    if user.get("role") != "ADMIN":
        raise bad_request("普通用户不支持配置模型 Key")
    config_service = request.app.state.user_model_config_service
    provider_inputs = [
        ModelConfigKeyUpdateRequest.ProviderKeyInput(
            key=provider.key,
            apiKey=provider.api_key,
        )
        for provider in body.providers
    ]
    update_request = ModelConfigKeyUpdateRequest(providers=provider_inputs)
    return config_service.save_keys(user_id, update_request)


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: int,
    body: AdminUpdateUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await require_admin(request)
    updates = body.model_dump(exclude_none=True)
    auth_service = AuthService(db)
    try:
        user = await auth_service.update_user(user_id, updates)
    except ValueError as exc:
        raise bad_request(exc)
    if not user:
        raise not_found("user_not_found")
    return user


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        result = await auth_service.delete_user(user_id)
    except ValueError as exc:
        raise bad_request(exc)
    return {"success": result}


@router.patch("/users/{user_id}/password")
async def admin_update_user_password(
    user_id: int,
    body: AdminUpdateUserPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        user = await auth_service.update_password(user_id, body.password)
    except ValueError as exc:
        raise bad_request(exc)
    if not user:
        raise not_found("user_not_found")
    return user


@router.post("/users/{user_id}/enable")
async def admin_enable_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        user = await auth_service.enable_user(user_id)
    except ValueError as exc:
        raise bad_request(exc)
    if not user:
        raise not_found("user_not_found")
    return user


@router.post("/users/{user_id}/disable")
async def admin_disable_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        user = await auth_service.disable_user(user_id)
    except ValueError as exc:
        raise bad_request(exc)
    if not user:
        raise not_found("user_not_found")
    return user


@router.patch("/users/{user_id}/status")
async def admin_update_user_status_legacy(
    user_id: int,
    body: AdminUpdateUserStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        if body.action == "enable":
            user = await auth_service.enable_user(user_id)
        elif body.action == "disable":
            user = await auth_service.disable_user(user_id)
        else:
            raise bad_request("invalid_action")
    except ValueError as exc:
        raise bad_request(exc)
    return user


@router.get("/credits/users")
async def admin_list_credit_users(request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    q = request.query_params.get("q", "")
    credit_service = CreditService(db)
    users = await credit_service.list_users(q)
    return users


@router.post("/credits/users/{user_id}/adjust")
async def admin_adjust_user_credit(
    user_id: int,
    body: AdminAdjustCreditRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await require_admin(request)
    credit_service = CreditService(db)
    try:
        result = await credit_service.adjust(user_id, body.amount, body.reason)
    except ValueError as exc:
        raise bad_request(exc)
    return result


@router.get("/credits/rules")
async def admin_list_credit_rules(request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    credit_service = CreditService(db)
    rules = await credit_service.list_rules()
    return rules


@router.patch("/credits/rules/{rule_code}", response_model=dict)
async def admin_update_credit_rule(
    rule_code: str,
    body: AdminUpdateCreditRuleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await require_admin(request)
    credit_service = CreditService(db)
    try:
        result = await credit_service.update_rule(rule_code, body.cost)
    except ValueError as exc:
        raise bad_request(exc)
    return result


@router.get("/invites")
async def admin_list_invites(request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    auth_service = AuthService(db)
    invites = await auth_service.list_invites()
    return invites


@router.get("/credits/users/{user_id}/transactions")
async def admin_list_credit_transactions(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    credit_service = CreditService(db)
    transactions = await credit_service.list_transactions(user_id)
    return transactions


@router.post("/invites/{invite_id}/revoke")
async def admin_revoke_invite(invite_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request)
    auth_service = AuthService(db)
    try:
        invite = await auth_service.revoke_invite(invite_id)
    except ValueError as exc:
        if str(exc) == "invite_not_found":
            raise not_found("invite_not_found")
        raise bad_request(exc)
    if not invite:
        raise not_found("invite_not_found")
    return invite


@router.post("/tasks/{task_id}/terminate")
async def admin_terminate_single_task(task_id: str, request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        await app_service.admin_terminate_task(task_id)
    except Exception as exc:
        raise bad_request(exc)
    return {"success": True, "taskId": task_id}


@router.post("/tasks/bulk-terminate", response_model=AdminTaskBatchResult)
async def admin_bulk_terminate_tasks(body: AdminBulkTerminateTasksRequest, request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in body.task_ids:
        try:
            await app_service.admin_terminate_task(task_id)
            succeeded.append(task_id)
        except Exception as exc:
            failed.append({"taskId": task_id, "error": str(exc)})
    return {
        "action": "terminate",
        "requestedCount": len(body.task_ids),
        "succeededTaskIds": succeeded,
        "failed": failed,
    }


@router.post("/tasks/bulk-delete")
async def admin_bulk_delete_tasks(body: AdminBulkTerminateTasksRequest, request: Request):
    await require_admin(request)
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


@router.post("/invites")
async def admin_create_invite(
    body: AdminCreateInviteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    admin_user = await require_admin(request)
    auth_service = AuthService(db)
    try:
        invite = await auth_service.create_invite(body.role, admin_user["id"], body.expires_at)
    except (ValueError, RuntimeError) as exc:
        raise bad_request(exc)
    return invite


@router.get("/tasks/{task_id}")
async def admin_get_task(task_id: str, request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        task = await app_service.admin_get_task(task_id)
    except Exception as exc:
        raise not_found(str(exc))
    return task


@router.get("/tasks/{task_id}/trace")
async def admin_get_task_trace(task_id: str, request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    limit_raw = request.query_params.get("limit", "50")
    try:
        limit = max(1, min(int(limit_raw), 500))
    except (ValueError, TypeError):
        limit = 50
    try:
        task = await app_service.admin_get_task(task_id)
        trace = task.get("trace", [])[-limit:]
    except Exception as exc:
        raise not_found(str(exc))
    return trace


@router.get("/tasks/{task_id}/diagnosis")
async def admin_get_task_diagnosis(task_id: str, request: Request):
    await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        task = await app_service.admin_get_task(task_id)
    except Exception as exc:
        raise not_found(str(exc))
    severity = "info"
    if task.get("status") == "FAILED":
        severity = "high"
    elif task.get("progress", 0) < 50 and task.get("status") in ("ANALYZING", "PLANNING", "RENDERING"):
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
    app_service = request.app.state.task_application_service
    try:
        result = await app_service.retry_task(task_id, admin_user["id"])
    except Exception as exc:
        raise bad_request(exc)
    return result


@router.delete("/tasks/{task_id}")
async def admin_delete_task(task_id: str, request: Request):
    admin_user = await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        await app_service.delete_task(task_id, admin_user["id"])
    except Exception as exc:
        raise bad_request(exc)
    return {"success": True, "taskId": task_id}
