"""Shared HTTP-boundary helpers for workflow subrouters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import bad_gateway, bad_request, payment_required
from backend.exceptions import GenerationProviderError
from backend.services.credit_service import InsufficientCreditsError
from backend.services.workflow_service import WorkflowService


def workflow_service(db: AsyncSession, request: Request | None = None) -> WorkflowService:
    generation = getattr(request.app.state, "generation_application_service", None) if request else None
    media = getattr(request.app.state, "media_artifact_service", None) if request else None
    return WorkflowService(db, generation_service=generation, media_service=media)


async def run_workflow_action(action: Callable[[], Awaitable[Any]]) -> Any:
    try:
        return await action()
    except InsufficientCreditsError:
        raise payment_required()
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    except GenerationProviderError as exc:
        raise bad_gateway(str(exc) or exc.__class__.__name__) from exc


async def save_aspect_ratio_preference(
    request: Request,
    user_id: int,
    aspect_ratio: str | None,
) -> None:
    normalized = str(aspect_ratio or "").strip()
    if not normalized:
        return
    preferences = getattr(request.app.state, "user_generation_preferences", None)
    if preferences is not None:
        await preferences.set_default_aspect_ratio(user_id, normalized)
