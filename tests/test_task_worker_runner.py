from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from backend.config import Settings, validate_settings
from backend.services.task_worker_runner import TaskWorkerOpsConfig, TaskWorkerRunner

pytestmark = pytest.mark.service


def test_settings_default_worker_concurrency_is_five() -> None:
    settings = Settings(_env_file=None)

    assert settings.worker_concurrency == 5


def test_settings_rejects_worker_concurrency_above_five() -> None:
    settings = Settings(_env_file=None, worker_concurrency=6)

    errors = [issue for issue in validate_settings(settings) if issue.field == "worker_concurrency"]

    assert [issue.severity for issue in errors] == ["error"]
    assert "must not exceed 5" in str(errors[0])


def test_task_worker_ops_config_clamps_concurrency_to_one_through_five() -> None:
    assert TaskWorkerOpsConfig(worker_concurrency=0).worker_concurrency == 1
    assert TaskWorkerOpsConfig(worker_concurrency=8).worker_concurrency == 5
    assert TaskWorkerOpsConfig(worker_concurrency=3).worker_concurrency == 3


@pytest.mark.asyncio
async def test_task_worker_runner_starts_at_most_five_worker_slots() -> None:
    queue = _RecordingQueue()
    coordinator = _RecordingCoordinator()
    handler = _RecordingPipelineHandler()
    runner = TaskWorkerRunner(
        task_queue_port=queue,
        execution_coordinator=coordinator,
        pipeline_handler=handler,
        ops_config=TaskWorkerOpsConfig(
            worker_concurrency=9,
            worker_poll_initial_delay_ms=60_000,
            worker_maintenance_initial_delay_ms=60_000,
        ),
    )

    await runner.start()
    try:
        assert len(runner._worker_instance_ids) == 5
        assert len(coordinator.upserts) == 5
        assert {row["metadata"]["workerConcurrency"] for row in coordinator.upserts} == {5}
        assert {row["metadata"]["slotIndex"] for row in coordinator.upserts} == {0, 1, 2, 3, 4}
    finally:
        await runner.stop()


class _RecordingQueue:
    def claim_next(self, worker_instance_id: str) -> str | None:
        return None


class _RecordingCoordinator:
    def __init__(self) -> None:
        self.upserts: list[dict[str, Any]] = []
        self.touches: list[dict[str, Any]] = []

    def upsert_worker_instance(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        self.upserts.append({
            "workerInstanceId": worker_instance_id,
            "workerType": worker_type,
            "status": status,
            "metadata": metadata,
        })
        return {}

    def touch_worker_instance(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        self.touches.append({
            "workerInstanceId": worker_instance_id,
            "workerType": worker_type,
            "status": status,
            "metadata": metadata,
        })
        return {}

    async def recover_stale_claims(
        self,
        stale_threshold: datetime,
        limit: int,
        task_repository: Any,
    ) -> None:
        return None


class _RecordingPipelineHandler:
    def process_task(
        self,
        task_id: str,
        worker_instance_id: str,
        worker_type: str,
        execution_mode: str,
    ) -> None:
        return None
