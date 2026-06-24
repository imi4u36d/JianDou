"""Auto-pilot worker runner: lifecycle-managed polling loop for auto-pilot jobs.

Polls a simple in-memory queue for auto-pilot job requests and drives the
workflow through its stages using ``WorkflowAutoPilot``.

Mirrors the TaskWorkerRunner pattern but is simplified for the auto-pilot
use case — no distributed queue, no worker instances, just a single
async loop.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from backend.domain.enums import AutoPilotState, WorkerStatus
from backend.services.workflow_auto_pilot import WorkflowAutoPilot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class AutoPilotOpsConfig:
    """Configuration for the auto-pilot worker runner."""

    def __init__(
        self,
        poll_interval_ms: int = 1_000,
        maintenance_interval_ms: int = 30_000,
    ) -> None:
        self.poll_interval_ms = poll_interval_ms
        self.maintenance_interval_ms = maintenance_interval_ms


# ---------------------------------------------------------------------------
# AutoPilotWorkerRunner
# ---------------------------------------------------------------------------


class AutoPilotWorkerRunner:
    """Polls for auto-pilot jobs and executes them via WorkflowAutoPilot.

    Usage::

        runner = AutoPilotWorkerRunner(workflow_service)
        await runner.start()
        # ... later ...
        await runner.stop()

        # Enqueue a job from a router:
        runner.enqueue(workflow_id, owner_user_id)
    """

    def __init__(self, workflow_service: Any, ops_config: AutoPilotOpsConfig | None = None) -> None:  # noqa: ANN001
        self._workflow_service = workflow_service
        self._ops_config = ops_config or AutoPilotOpsConfig()
        self._running = False
        self._poll_task: asyncio.Task | None = None
        self._maintenance_task: asyncio.Task | None = None
        self._job_queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self._job_locks: dict[str, asyncio.Lock] = {}  # workflow_id -> Lock

    @property
    def is_running(self) -> bool:
        return self._running

    # -- Public API ---------------------------------------------------------

    def enqueue(self, workflow_id: str, owner_user_id: int) -> None:
        """Enqueue an auto-pilot job for a workflow."""
        self._job_queue.put_nowait((workflow_id, owner_user_id))
        logger.info("Auto-pilot job enqueued: workflowId=%s", workflow_id)

    def queue_size(self) -> int:
        """Return the current number of jobs waiting in the queue."""
        return self._job_queue.qsize()

    def queue_position_of(self, workflow_id: str) -> int | None:
        """Return the 1-based position of a workflow in the queue, or None if not queued."""
        for idx, (wid, _) in enumerate(self._job_queue._queue):
            if wid == workflow_id:
                return idx + 1
        return None

    def is_queued(self, workflow_id: str) -> bool:
        """Return whether a given workflow is currently waiting in the queue."""
        return any(wid == workflow_id for wid, _ in self._job_queue._queue)

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the auto-pilot worker."""
        if self._running:
            return

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info("AutoPilotWorkerRunner started")

    async def stop(self) -> None:
        """Stop the auto-pilot worker gracefully."""
        if not self._running:
            return

        self._running = False

        for task in (self._poll_task, self._maintenance_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._poll_task = None
        self._maintenance_task = None
        logger.info("AutoPilotWorkerRunner stopped")

    # -- Internal loops -----------------------------------------------------

    async def _poll_loop(self) -> None:
        """Main polling loop: dequeue and execute auto-pilot jobs."""
        while self._running:
            try:
                workflow_id, owner_user_id = await self._job_queue.get()
                await self._execute_job(workflow_id, owner_user_id)
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.warning("Auto-pilot poll failed", exc_info=ex)
            await asyncio.sleep(self._ops_config.poll_interval_ms / 1000.0)

    async def _execute_job(self, workflow_id: str, owner_user_id: int) -> None:
        """Execute a single auto-pilot job, ensuring only one runner per workflow."""
        lock = self._job_locks.get(workflow_id)
        if lock is None:
            lock = asyncio.Lock()
            self._job_locks[workflow_id] = lock

        async with lock:
            # Verify the workflow is in a state that allows auto-pilot
            from backend.models.workflow import BizStageWorkflow
            from sqlalchemy import select

            stmt = select(BizStageWorkflow).where(
                BizStageWorkflow.workflow_id == workflow_id,
                BizStageWorkflow.is_deleted == 0,
            )
            result = await self._workflow_service.db.execute(stmt)
            wf = result.scalar_one_or_none()

            if wf is None:
                logger.warning("Workflow not found for auto-pilot: %s", workflow_id)
                return

            # Only allow auto mode
            if wf.execution_mode != "auto":
                logger.info("Workflow %s is not in auto mode, skipping", workflow_id)
                return

            # If already in an active or terminal state (other than queued), skip
            if wf.auto_pilot_state in (
                AutoPilotState.RUNNING.value,
                AutoPilotState.PAUSED.value,
                AutoPilotState.FAILED.value,
                AutoPilotState.COMPLETED.value,
            ):
                logger.info(
                    "Workflow %s already in state %s, skipping",
                    workflow_id, wf.auto_pilot_state,
                )
                return

            # Set state to running
            from sqlalchemy import update
            from backend.shared import now_iso

            now = now_iso()
            stmt = (
                update(BizStageWorkflow)
                .where(BizStageWorkflow.workflow_id == workflow_id)
                .values(
                    auto_pilot_state=AutoPilotState.RUNNING.value,
                    auto_pilot_started_at=now,
                    update_time=now,
                )
            )
            await self._workflow_service.db.execute(stmt)
            await self._workflow_service.db.commit()

            # Run the auto-pilot
            auto_pilot = WorkflowAutoPilot(
                db=self._workflow_service.db,
                workflow_service=self._workflow_service,
            )
            result = await auto_pilot.run(workflow_id, owner_user_id)

            logger.info(
                "Auto-pilot completed for %s: status=%s iterations=%s",
                workflow_id,
                result.get("status"),
                result.get("iterations"),
            )

    async def _maintenance_loop(self) -> None:
        """Periodic maintenance: log worker status."""
        await asyncio.sleep(self._ops_config.maintenance_interval_ms / 1000.0)

        while self._running:
            try:
                active_jobs = self._job_queue.qsize()
                logger.debug(
                    "AutoPilotWorkerRunner maintenance: running=%s, queue_size=%s",
                    self._running, active_jobs,
                )
            except Exception as ex:
                logger.warning("Auto-pilot maintenance failed", exc_info=ex)
            await asyncio.sleep(self._ops_config.maintenance_interval_ms / 1000.0)
