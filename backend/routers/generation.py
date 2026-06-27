from __future__ import annotations

import logging
from math import gcd
from typing import Any

from fastapi import APIRouter, Query, Request

from backend.auth import get_current_user
from backend.errors import bad_request, not_found, unauthorized
from backend.schemas.generation import (
    GenerationAspectRatioPreferenceRequest,
    GenerationAspectRatioPreferenceResponse,
    GenerationRunListResponse,
    GenerationRunRequest,
    GenerationRunResponse,
    GenerationUsageResponse,
)
from backend.services.generation_service import GenerationRunNotFoundException, UnsupportedGenerationKindException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/generation", tags=["generation"])


def _ratio_from_size(item: dict[str, Any]) -> str | None:
    width = item.get("width")
    height = item.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raw_value = str(item.get("value", "")).replace("*", "x").lower()
        parts = raw_value.split("x", 1)
        if len(parts) != 2:
            return None
        try:
            width = int(parts[0].strip())
            height = int(parts[1].strip())
        except ValueError:
            return None
    divisor = gcd(width, height)
    if divisor <= 0:
        return None
    return f"{width // divisor}:{height // divisor}"


def _supported_aspect_ratios(catalog: dict[str, Any]) -> set[str]:
    ratios: set[str] = {"智能"}
    for item in catalog.get("aspectRatios", []):
        if isinstance(item, dict):
            value = str(item.get("value", "")).strip()
            if value:
                ratios.add(value)
    for item in catalog.get("imageSizes", []):
        if isinstance(item, dict):
            ratio = _ratio_from_size(item)
            if ratio:
                ratios.add(ratio)
    return ratios


def _catalog_with_user_default(catalog: dict[str, Any], preferred_aspect_ratio: str | None) -> dict[str, Any]:
    preferred = str(preferred_aspect_ratio or "").strip()
    if not preferred or preferred not in _supported_aspect_ratios(catalog):
        return catalog
    return {
        **catalog,
        "defaultAspectRatio": preferred,
        "userDefaultAspectRatio": preferred,
    }


async def _catalog_for_request(request: Request) -> dict[str, Any]:
    catalog = request.app.state.generation_catalog_service.catalog()
    user = await get_current_user(request)
    if user is None:
        return catalog
    preference_service = getattr(request.app.state, "user_generation_preferences", None)
    if preference_service is None:
        return catalog
    preferred = await preference_service.default_aspect_ratio(user["id"])
    return _catalog_with_user_default(catalog, preferred)


@router.get("/options", response_model=dict)
async def generation_options(request: Request):
    return await _catalog_for_request(request)


@router.get("/catalog", response_model=dict)
async def generation_catalog(request: Request):
    return await _catalog_for_request(request)


@router.post("/preferences/aspect-ratio", response_model=GenerationAspectRatioPreferenceResponse)
async def save_generation_aspect_ratio_preference(
    payload: GenerationAspectRatioPreferenceRequest,
    request: Request,
):
    user = await get_current_user(request)
    if user is None:
        raise unauthorized()
    aspect_ratio = payload.aspect_ratio.strip()
    catalog = request.app.state.generation_catalog_service.catalog()
    if aspect_ratio not in _supported_aspect_ratios(catalog):
        raise bad_request("unsupported aspect ratio")
    preference_service = getattr(request.app.state, "user_generation_preferences", None)
    if preference_service is not None:
        await preference_service.set_default_aspect_ratio(user["id"], aspect_ratio)
    return GenerationAspectRatioPreferenceResponse(aspect_ratio=aspect_ratio)


@router.post("/runs", response_model=GenerationRunResponse)
async def create_generation_run(payload: GenerationRunRequest, request: Request):
    user = await get_current_user(request)
    if user is None:
        raise unauthorized()
    request_data = payload.model_dump()
    auth_value = request_data.get("auth")
    auth = auth_value if isinstance(auth_value, dict) else {}
    auth["userId"] = user["id"]
    request_data["auth"] = auth
    service = request.app.state.generation_application_service
    try:
        return await service.create_run(request_data)
    except UnsupportedGenerationKindException as exc:
        raise bad_request(str(exc))
    except ValueError as exc:
        raise bad_request(str(exc))


@router.get("/runs", response_model=GenerationRunListResponse)
async def list_generation_runs(request: Request, limit: int = Query(100, ge=1, le=200)):
    service = request.app.state.generation_application_service
    return await service.list_runs(limit)


@router.get("/runs/{run_id}", response_model=GenerationRunResponse)
async def get_generation_run(run_id: str, request: Request):
    service = request.app.state.generation_application_service
    try:
        return await service.get_run(run_id)
    except GenerationRunNotFoundException:
        raise not_found("generation_run")


@router.get("/usage", response_model=GenerationUsageResponse)
async def generation_usage(request: Request):
    service = request.app.state.generation_application_service
    return await service.usage()
