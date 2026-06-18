"""Admin router — administrative API endpoints."""

from __future__ import annotations
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.routers.auth import get_current_user, require_admin
from backend.services.auth_service import AuthService
from backend.services.credit_service import CreditService

router = APIRouter(prefix="/api/v3/admin", tags=["admin"])


@router.get("/overview")
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
    app_service = request.app.state.task_application_service
    tasks = await app_service.admin_list_tasks(
        q=q or None,
        status=status or None,
        sort=sort or None,
    )
    return tasks


@router.post("/tasks/batch-action")
async def admin_batch_task_action(request: Request):
    admin_user = await require_admin(request)
    body = await request.json()
    action = body.get("action", "")
    task_ids = body.get("taskIds", [])
    app_service = request.app.state.task_application_service
    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in (task_ids or []):
        try:
            await app_service.admin_terminate_task(task_id)
            succeeded.append(task_id)
        except Exception as exc:
            failed.append({"taskId": task_id, "error": str(exc)})
    return {
        "action": action,
        "requested_count": len(task_ids),
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
    await require_admin(request)
    config_service = request.app.state.admin_model_config_service
    result = config_service.read()
    return result


@router.put("/model-config/keys")
async def admin_update_model_config_keys(request: Request):
    await require_admin(request)
    body = await request.json()
    config_service = request.app.state.admin_model_config_service
    from backend.services.model_config_service import AdminModelConfigKeyUpdateRequest
    providers_raw = body.get("providers", [])
    provider_inputs = [
        AdminModelConfigKeyUpdateRequest.ProviderKeyInput(
            key=p.get("key", ""),
            apiKey=p.get("apiKey", ""),
        )
        for p in providers_raw
    ]
    update_request = AdminModelConfigKeyUpdateRequest(providers=provider_inputs)
    result = config_service.save_keys(update_request)
    return result


@router.post("/model-config/validate")
async def admin_validate_model_config_keys(request: Request):
    await require_admin(request)
    body = await request.json()
    config_service = request.app.state.admin_model_config_service
    from backend.services.model_config_service import AdminModelConfigKeyUpdateRequest
    providers_raw = body.get("providers", [])
    provider_inputs = [
        AdminModelConfigKeyUpdateRequest.ProviderKeyInput(
            key=p.get("key", ""),
            apiKey=p.get("apiKey", ""),
        )
        for p in providers_raw
    ]
    update_request = AdminModelConfigKeyUpdateRequest(providers=provider_inputs)
    return config_service.validate_keys(update_request)


@router.get("/users")
async def admin_list_users(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    q = request.query_params.get("q", "")
    role = request.query_params.get("role", "")
    status_param = request.query_params.get("status", "")
    auth_service = AuthService(db)
    users = await auth_service.list_users(q, role, status_param)
    return users


@router.post("/users")
async def admin_create_user(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    auth_service = AuthService(db)
    try:
        user = await auth_service.create_user(
            username=body.get("username", ""),
            password=body.get("password", ""),
            display_name=body.get("displayName", body.get("display_name", "")),
            role=body.get("role", "USER"),
            status=body.get("status", "ACTIVE"),
            task_concurrency_limit=body.get("taskConcurrencyLimit", body.get("task_concurrency_limit", 1)),
        )
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return user


@router.patch("/users/{user_id}")
async def admin_update_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    # Accept both camelCase and snake_case
    updates = {
        "display_name": body.get("displayName", body.get("display_name")),
        "role": body.get("role"),
        "status": body.get("status"),
        "task_concurrency_limit": body.get("taskConcurrencyLimit", body.get("task_concurrency_limit")),
    }
    # Remove None values so only provided fields get updated
    updates = {k: v for k, v in updates.items() if v is not None}
    auth_service = AuthService(db)
    try:
        user = await auth_service.update_user(user_id, updates)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    if not user:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail="user_not_found")
    return user


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    auth_service = AuthService(db)
    try:
        result = await auth_service.delete_user(user_id)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return {"success": result}


@router.patch("/users/{user_id}/password")
async def admin_update_user_password(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    password = body.get("password", "")
    auth_service = AuthService(db)
    try:
        user = await auth_service.update_password(user_id, password)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    if not user:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail="user_not_found")
    return user


@router.post("/users/{user_id}/enable")
async def admin_enable_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    auth_service = AuthService(db)
    try:
        user = await auth_service.enable_user(user_id)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    if not user:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail="user_not_found")
    return user


@router.post("/users/{user_id}/disable")
async def admin_disable_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    auth_service = AuthService(db)
    try:
        user = await auth_service.disable_user(user_id)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    if not user:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail="user_not_found")
    return user


@router.patch("/users/{user_id}/status")
async def admin_update_user_status_legacy(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    action = body.get("action", "")
    auth_service = AuthService(db)
    try:
        if action == "enable":
            user = await auth_service.enable_user(user_id)
        elif action == "disable":
            user = await auth_service.disable_user(user_id)
        else:
            from fastapi import HTTPException as FastAPIHTTPException
            raise FastAPIHTTPException(status_code=400, detail="invalid_action")
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return user


@router.get("/credits/users")
async def admin_list_credit_users(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    q = request.query_params.get("q", "")
    credit_service = CreditService(db)
    users = await credit_service.list_users(q)
    return users


@router.post("/credits/users/{user_id}/adjust")
async def admin_adjust_user_credit(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    amount = body.get("amount", 0)
    reason = body.get("reason", "")
    credit_service = CreditService(db)
    try:
        result = await credit_service.adjust(user_id, amount, reason)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return result


@router.get("/credits/rules")
async def admin_list_credit_rules(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    credit_service = CreditService(db)
    rules = await credit_service.list_rules()
    return rules


@router.patch("/credits/rules/{rule_code}")
async def admin_update_credit_rule(rule_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    cost = body.get("cost", 0)
    credit_service = CreditService(db)
    try:
        result = await credit_service.update_rule(rule_code, cost)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return result


@router.get("/invites")
async def admin_list_invites(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    auth_service = AuthService(db)
    invites = await auth_service.list_invites()
    return invites


@router.get("/credits/users/{user_id}/transactions")
async def admin_list_credit_transactions(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    credit_service = CreditService(db)
    transactions = await credit_service.list_transactions(user_id)
    return transactions


@router.post("/invites/{invite_id}/revoke")
async def admin_revoke_invite(invite_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    auth_service = AuthService(db)
    try:
        invite = await auth_service.revoke_invite(invite_id)
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    if not invite:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail="invite_not_found")
    return invite


@router.post("/tasks/{task_id}/terminate")
async def admin_terminate_single_task(task_id: str, request: Request):
    admin_user = await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        result = await app_service.admin_terminate_task(task_id)
    except Exception as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return {"success": True, "taskId": task_id}


@router.post("/tasks/bulk-terminate")
async def admin_bulk_terminate_tasks(request: Request):
    admin_user = await require_admin(request)
    body = await request.json()
    task_ids = body.get("taskIds", [])
    app_service = request.app.state.task_application_service
    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in (task_ids or []):
        try:
            await app_service.admin_terminate_task(task_id)
            succeeded.append(task_id)
        except Exception as exc:
            failed.append({"taskId": task_id, "error": str(exc)})
    return {
        "action": "terminate",
        "requestedCount": len(task_ids),
        "succeededTaskIds": succeeded,
        "failed": failed,
    }


@router.post("/invites")
async def admin_create_invite(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    role = body.get("role", "USER")
    expires_at = body.get("expiresAt", body.get("expires_at"))
    auth_service = AuthService(db)
    try:
        invite = await auth_service.create_invite(role, admin_user["id"], expires_at)
    except (ValueError, RuntimeError) as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return invite


@router.get("/tasks/{task_id}")
async def admin_get_task(task_id: str, request: Request):
    admin_user = await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        task = await app_service.admin_get_task(task_id)
    except Exception as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail=str(exc))
    return task


@router.get("/tasks/{task_id}/trace")
async def admin_get_task_trace(task_id: str, request: Request):
    admin_user = await require_admin(request)
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
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail=str(exc))
    return trace


@router.get("/tasks/{task_id}/diagnosis")
async def admin_get_task_diagnosis(task_id: str, request: Request):
    admin_user = await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        task = await app_service.admin_get_task(task_id)
    except Exception as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=404, detail=str(exc))
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
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return result


@router.delete("/tasks/{task_id}")
async def admin_delete_task(task_id: str, request: Request):
    admin_user = await require_admin(request)
    app_service = request.app.state.task_application_service
    try:
        await app_service.delete_task(task_id, admin_user["id"])
    except Exception as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return {"success": True, "taskId": task_id}
