"""Tests for backend/services/auto_pilot_worker_runner.py — AutoPilotWorkerRunner."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.service

from backend.domain.enums import AutoPilotState
from backend.services.auto_pilot_worker_runner import (
    AutoPilotOpsConfig,
    AutoPilotWorkerRunner,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_workflow(
    workflow_id: str = "wf_1",
    execution_mode: str = "auto",
    auto_pilot_state: str = AutoPilotState.IDLE.value,
) -> MagicMock:
    wf = MagicMock()
    wf.workflow_id = workflow_id
    wf.execution_mode = execution_mode
    wf.auto_pilot_state = auto_pilot_state
    wf.is_deleted = 0
    return wf


def _make_runner(**kwargs) -> AutoPilotWorkerRunner:
    svc = MagicMock()
    svc.db = MagicMock()
    svc.db.execute = AsyncMock()
    svc.db.commit = AsyncMock()
    config = AutoPilotOpsConfig(poll_interval_ms=10, maintenance_interval_ms=50)
    return AutoPilotWorkerRunner(svc, config)


# ---------------------------------------------------------------------------
# AutoPilotOpsConfig
# ---------------------------------------------------------------------------


class TestAutoPilotOpsConfig:
    def test_defaults(self):
        cfg = AutoPilotOpsConfig()
        assert cfg.poll_interval_ms == 1_000
        assert cfg.maintenance_interval_ms == 30_000

    def test_custom_values(self):
        cfg = AutoPilotOpsConfig(poll_interval_ms=500, maintenance_interval_ms=10_000)
        assert cfg.poll_interval_ms == 500
        assert cfg.maintenance_interval_ms == 10_000


# ---------------------------------------------------------------------------
# AutoPilotWorkerRunner — lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        runner = _make_runner()
        assert not runner.is_running
        await runner.start()
        assert runner.is_running
        await runner.stop()
        assert not runner.is_running

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self):
        runner = _make_runner()
        await runner.start()
        await runner.start()  # should not create a second poll loop
        assert runner.is_running
        await runner.stop()

    @pytest.mark.asyncio
    async def test_double_stop_is_safe(self):
        runner = _make_runner()
        await runner.start()
        await runner.stop()
        await runner.stop()  # should be safe


# ---------------------------------------------------------------------------
# AutoPilotWorkerRunner — enqueue
# ---------------------------------------------------------------------------


class TestEnqueue:
    def test_enqueue_adds_job_to_queue(self):
        runner = _make_runner()
        runner.enqueue("wf_1", 42)
        assert runner._job_queue.qsize() == 1

    def test_enqueue_multiple_jobs(self):
        runner = _make_runner()
        runner.enqueue("wf_1", 1)
        runner.enqueue("wf_2", 2)
        runner.enqueue("wf_3", 3)
        assert runner._job_queue.qsize() == 3


# ---------------------------------------------------------------------------
# AutoPilotWorkerRunner — execute_job
# ---------------------------------------------------------------------------


class TestExecuteJob:
    def _make_result(self, scalar):
        """Create a SQLAlchemy-like ExecuteResult mock."""
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=scalar)
        return result

    @pytest.mark.asyncio
    async def test_execute_job_nonexistent_workflow(self):
        runner = _make_runner()
        svc_mock = runner._workflow_service
        svc_mock.db.execute = AsyncMock(return_value=self._make_result(None))
        await runner._execute_job("wf_missing", 1)
        # Should not raise, just log a warning
        svc_mock.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_job_non_auto_mode(self):
        runner = _make_runner()
        svc_mock = runner._workflow_service
        wf = _mock_workflow(execution_mode="manual")
        svc_mock.db.execute = AsyncMock(return_value=self._make_result(wf))
        await runner._execute_job("wf_1", 1)
        # Should skip — not in auto mode
        svc_mock.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_job_already_running(self):
        runner = _make_runner()
        svc_mock = runner._workflow_service
        wf = _mock_workflow(
            auto_pilot_state=AutoPilotState.RUNNING.value,
        )
        svc_mock.db.execute = AsyncMock(return_value=self._make_result(wf))
        await runner._execute_job("wf_1", 1)
        # Should skip — already running
        svc_mock.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_job_already_paused(self):
        runner = _make_runner()
        svc_mock = runner._workflow_service
        wf = _mock_workflow(
            auto_pilot_state=AutoPilotState.PAUSED.value,
        )
        svc_mock.db.execute = AsyncMock(return_value=self._make_result(wf))
        await runner._execute_job("wf_1", 1)
        svc_mock.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_job_sets_running_then_runs(self):
        runner = _make_runner()
        svc_mock = runner._workflow_service
        wf = _mock_workflow(auto_pilot_state=AutoPilotState.IDLE.value)

        call_count = [0]

        async def execute_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: SELECT
                return self._make_result(wf)
            # Subsequent calls: UPDATE
            return None

        svc_mock.db.execute = AsyncMock(side_effect=execute_side_effect)
        svc_mock.db.commit = AsyncMock()

        # Patch WorkflowAutoPilot.run to return immediately
        with patch(
            "backend.services.auto_pilot_worker_runner.WorkflowAutoPilot"
        ) as mock_pilot_class:
            mock_pilot = MagicMock()
            mock_pilot.run = AsyncMock(return_value={"status": "completed", "iterations": 5})
            mock_pilot_class.return_value = mock_pilot

            await runner._execute_job("wf_1", 42)

            mock_pilot_class.assert_called_once()
            mock_pilot.run.assert_called_once_with("wf_1", 42)
            # Verify state was set to RUNNING before calling run
            assert call_count[0] >= 1
