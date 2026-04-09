from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ai_cut_shared.schemas import (
    GenerationRunRequest,
    GenerationRunResponse,
    ModelCatalog,
    VideoModelUsageResponse,
)

router = APIRouter(prefix="/api/v2/generation", tags=["generation"])


def _service(request: Request):
    return request.app.state.runtime.service


@router.get("/catalog", response_model=ModelCatalog)
def get_catalog(request: Request):
    return _service(request).list_generation_catalog()


@router.post("/runs", response_model=GenerationRunResponse)
def create_run(request: Request, payload: GenerationRunRequest):
    try:
        return _service(request).create_generation_run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=GenerationRunResponse)
def get_run(request: Request, run_id: str):
    try:
        return _service(request).get_generation_run(run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/usage", response_model=VideoModelUsageResponse)
def get_usage(request: Request):
    return _service(request).list_generation_usage()
