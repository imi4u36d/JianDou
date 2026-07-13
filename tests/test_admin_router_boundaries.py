from __future__ import annotations

import pytest

from backend.routers.admin import router
from backend.routers.admin_task_routes import _terminate_tasks


def test_admin_task_routes_remain_registered_on_public_prefix() -> None:
    routes = {
        (method, route.path)
        for route in router.routes
        for method in (getattr(route, "methods", None) or set())
    }
    expected = {
        ("GET", "/api/v3/admin/tasks"),
        ("POST", "/api/v3/admin/tasks/batch-action"),
        ("POST", "/api/v3/admin/tasks/bulk-terminate"),
        ("POST", "/api/v3/admin/tasks/bulk-delete"),
        ("GET", "/api/v3/admin/tasks/{task_id}"),
        ("GET", "/api/v3/admin/tasks/{task_id}/trace"),
        ("GET", "/api/v3/admin/tasks/{task_id}/diagnosis"),
        ("POST", "/api/v3/admin/tasks/{task_id}/retry"),
        ("POST", "/api/v3/admin/tasks/{task_id}/terminate"),
        ("DELETE", "/api/v3/admin/tasks/{task_id}"),
    }
    assert expected <= routes


@pytest.mark.asyncio
async def test_bulk_termination_collects_partial_failures() -> None:
    class ApplicationService:
        async def admin_terminate_task(self, task_id: str) -> None:
            if task_id == "failed":
                raise ValueError("cannot terminate")

    succeeded, failed = await _terminate_tasks(ApplicationService(), ["done", "failed"])

    assert succeeded == ["done"]
    assert failed == [{"taskId": "failed", "error": "cannot terminate"}]
