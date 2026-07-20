from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.routers.workflow_route_support import run_workflow_action
from backend.routers.workflows import router


def test_workflow_stage_routes_remain_on_public_router() -> None:
    routes = {
        (method, route.path)
        for route in router.routes
        for method in (getattr(route, "methods", None) or set())
    }
    expected = {
        ("POST", "/api/v3/workflows/{workflow_id}/storyboards/generate"),
        ("POST", "/api/v3/workflows/{workflow_id}/storyboards/{version_id}/select"),
        ("POST", "/api/v3/workflows/{workflow_id}/storyboards/{version_id}/adjust"),
        ("POST", "/api/v3/workflows/{workflow_id}/clips/{clip_index}/keyframes/generate"),
        ("POST", "/api/v3/workflows/{workflow_id}/character-sheets/{character_index}/generate"),
        ("POST", "/api/v3/workflows/{workflow_id}/visual-assets/{asset_index}/generate"),
        ("POST", "/api/v3/workflows/{workflow_id}/visual-assets/{clip_index}/select-asset"),
        ("POST", "/api/v3/workflows/{workflow_id}/clips/{clip_index}/videos/generate"),
    }
    assert expected <= routes
    assert len(router.routes) == 27


@pytest.mark.asyncio
async def test_workflow_action_translates_validation_errors() -> None:
    async def invalid_action() -> None:
        raise ValueError("invalid workflow")

    with pytest.raises(HTTPException) as raised:
        await run_workflow_action(invalid_action)

    assert raised.value.status_code == 400
    assert raised.value.detail == "invalid workflow"
