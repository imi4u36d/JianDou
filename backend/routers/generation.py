from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend.auth import get_current_user
from backend.schemas.generation import GenerationRunRequest
from backend.services.generation_service import GenerationRunNotFoundException, UnsupportedGenerationKindException

router = APIRouter(prefix="/api/v3/generation", tags=["generation"])


@router.get("/options")
async def generation_options(request: Request):
    return request.app.state.generation_catalog_service.catalog()


@router.get("/catalog")
async def generation_catalog(request: Request):
    return request.app.state.generation_catalog_service.catalog()


@router.post("/runs")
async def create_generation_run(payload: GenerationRunRequest, request: Request):
    user = await get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    request_data = payload.model_dump()
    auth_value = request_data.get("auth")
    auth = auth_value if isinstance(auth_value, dict) else {}
    auth["userId"] = user["id"]
    request_data["auth"] = auth
    service = request.app.state.generation_application_service
    try:
        return await service.create_run(request_data)
    except UnsupportedGenerationKindException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs")
async def list_generation_runs(request: Request, limit: int = Query(100, ge=1, le=200)):
    service = request.app.state.generation_application_service
    return await service.list_runs(limit)


@router.get("/runs/{run_id}")
async def get_generation_run(run_id: str, request: Request):
    service = request.app.state.generation_application_service
    try:
        return await service.get_run(run_id)
    except GenerationRunNotFoundException:
        raise HTTPException(status_code=404, detail="generation_run_not_found")


@router.get("/usage")
async def generation_usage(request: Request):
    service = request.app.state.generation_application_service
    return await service.usage()
