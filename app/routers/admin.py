from __future__ import annotations
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.routers.auth import get_current_user, require_admin
from app.services.auth_service import AuthService
from app.services.credit_service import CreditService

router = APIRouter(prefix="/api/v3/admin", tags=["admin"])


@router.get("/overview")
async def admin_overview(request: Request):
    user = await get_current_user(request)
    is_admin = user and user.get("role") == "ADMIN"
    return {
        "total_tasks": 0,
        "queued_tasks": 0,
        "running_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
    }


@router.get("/tasks")
async def admin_list_tasks(request: Request):
    return []


@router.post("/tasks/batch-action")
async def admin_batch_task_action(request: Request):
    return {"action": "", "requested_count": 0, "succeeded_task_ids": [], "failed": []}


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
            display_name=body.get("display_name", ""),
            role=body.get("role", "USER"),
            status=body.get("status", "ACTIVE"),
            task_concurrency_limit=body.get("task_concurrency_limit", 1),
        )
    except ValueError as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return user


@router.patch("/users/{user_id}")
async def admin_update_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    auth_service = AuthService(db)
    try:
        user = await auth_service.update_user(user_id, body)
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


@router.patch("/users/{user_id}/status")
async def admin_update_user_status(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
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


@router.post("/invites")
async def admin_create_invite(request: Request, db: AsyncSession = Depends(get_db)):
    admin_user = await require_admin(request)
    body = await request.json()
    role = body.get("role", "USER")
    auth_service = AuthService(db)
    try:
        invite = await auth_service.create_invite(role, admin_user["id"])
    except (ValueError, RuntimeError) as exc:
        from fastapi import HTTPException as FastAPIHTTPException
        raise FastAPIHTTPException(status_code=400, detail=str(exc))
    return invite


@router.get("/model-config")
async def admin_get_model_config(request: Request):
    return {"providers": []}


@router.put("/model-config/keys")
async def admin_update_model_config_keys(request: Request):
    return {"providers": []}
