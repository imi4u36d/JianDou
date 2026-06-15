"""Task worker runner: lifecycle-managed polling loop for queue-mode execution.

Mirrors the Java TaskWorkerRunner (task/runtime).  Manages a pool of worker
slots, each polling the queue for tasks, plus a maintenance tick that
heartbeats worker instances and recovers stale claims.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional, Protocol

from app.domain.enums import WorkerStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Minimal port interfaces (satisfied by TaskQueueCoordinator and
# TaskExecutionCoordinator in the real app)
# ---------------------------------------------------------------------------

class TaskQueuePortLike(Protocol):
    """Subset of TaskQueuePort needed by the runner."""

    def claim_next(self, worker_instance_id: str) -> str | None: ...


class ExecutionCoordinatorLike(Protocol):
    """Subset of TaskExecutionCoordinator needed by the runner."""

    def upsert_worker_instance(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any],
    ) -> None: ...

    def touch_worker_instance(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any],
    ) -> None: ...

    def recover_stale_claims(
        self,
        stale_threshold: datetime,
        limit: int,
    ) -> None: ...


class PipelineHandlerLike(Protocol):
    """Subset of TaskWorkerPipelineHandler needed by the runner."""

    def process_task(
        self,
        task_id: str,
        worker_instance_id: str,
        worker_type: str,
        execution_mode: str,
    ) -> None: ...


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

class TaskWorkerOpsConfig:
    """Configuration for the task worker runner.

    Maps to JiandouTaskOpsProperties in Java.
    """

    def __init__(
        self,
        worker_concurrency: int = 2,
        worker_poll_initial_delay_ms: int = 5_000,
        worker_poll_interval_ms: int = 2_000,
        worker_maintenance_initial_delay_ms: int = 10_000,
        worker_maintenance_interval_ms: int = 30_000,
        worker_stale_timeout_seconds: int = 300,
    ) -> None:
        self.worker_concurrency = worker_concurrency
        self.worker_poll_initial_delay_ms = worker_poll_initial_delay_ms
        self.worker_poll_interval_ms = worker_poll_interval_ms
        self.worker_maintenance_initial_delay_ms = worker_maintenance_initial_delay_ms
        self.worker_maintenance_interval_ms = worker_maintenance_interval_ms
        self.worker_stale_timeout_seconds = worker_stale_timeout_seconds


# ---------------------------------------------------------------------------
# TaskWorkerRunner
# ---------------------------------------------------------------------------

class TaskWorkerRunner:
    """Manages a pool of async worker tasks that poll for queued tasks.

    Mirrors the Java TaskWorkerRunner (SmartLifecycle).  Call ``start()``
    to begin polling and ``stop()`` to shut down cleanly.

    Usage::

        runner = TaskWorkerRunner(
            task_queue_port=coordinator,
            execution_coordinator=coordinator,
            pipeline_handler=handler,
            execution_mode="queue",
            ops_config=TaskWorkerOpsConfig(),
        )
        await runner.start()
        # ... later ...
        await runner.stop()
    """

    WORKER_TYPE = "python_queue_worker"

    def __init__(
        self,
        task_queue_port: TaskQueuePortLike,
        execution_coordinator: ExecutionCoordinatorLike,
        pipeline_handler: PipelineHandlerLike,
        execution_mode: str = "queue",
        ops_config: TaskWorkerOpsConfig | None = None,
    ) -> None:
        self._task_queue_port = task_queue_port
        self._execution_coordinator = execution_coordinator
        self._pipeline_handler = pipeline_handler
        self._execution_mode = execution_mode.strip().lower() if isinstance(execution_mode, str) else str(execution_mode).lower()
        self._ops_config = ops_config or TaskWorkerOpsConfig()
        self._worker_instance_ids: list[str] = []
        self._running = False
        self._poll_tasks: list[asyncio.Task] = []
        self._maintenance_task: asyncio.Task | None = None

    # -- Lifecycle ----------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return
        if self._execution_mode != "queue":
            return

        self._running = True
        concurrency = self._ops_config.worker_concurrency
        self._worker_instance_ids.clear()

        for index in range(concurrency):
            worker_id = f"python_worker_{index}_{uuid.uuid4().hex}"
            self._worker_instance_ids.append(worker_id)
            self._execution_coordinator.upsert_worker_instance(
                worker_id,
                self.WORKER_TYPE,
                WorkerStatus.RUNNING.value,
                {"executionMode": self._execution_mode, "slotIndex": index, "workerConcurrency": concurrency},
            )

        # Start poll tasks
        for worker_id in self._worker_instance_ids:
            task = asyncio.create_task(self._poll_loop(worker_id))
            self._poll_tasks.append(task)

        # Start maintenance task
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info(
            "TaskWorkerRunner started: concurrency=%d, mode=%s",
            concurrency, self._execution_mode,
        )

    async def stop(self) -> None:
        """Stop the worker pool gracefully."""
        if not self._running:
            return

        self._running = False

        # Mark workers as stopped
        for worker_id in self._worker_instance_ids:
            try:
                self._execution_coordinator.touch_worker_instance(
                    worker_id,
                    self.WORKER_TYPE,
                    WorkerStatus.STOPPED.value,
                    {"executionMode": self._execution_mode},
                )
            except Exception as ex:
                logger.warning("Failed to mark worker stopped: %s", worker_id, exc_info=ex)

        # Cancel poll tasks
        for task in self._poll_tasks:
            task.cancel()
        if self._poll_tasks:
            await asyncio.gather(*self._poll_tasks, return_exceptions=True)
        self._poll_tasks.clear()

        # Cancel maintenance
        if self._maintenance_task is not None:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
            self._maintenance_task = None

        self._worker_instance_ids.clear()
        logger.info("TaskWorkerRunner stopped")

    # -- Internal loops -----------------------------------------------------

    async def _poll_loop(self, worker_instance_id: str) -> None:
        """Poll loop for a single worker slot."""
        # Initial delay
        await asyncio.sleep(self._ops_config.worker_poll_initial_delay_ms / 1000.0)

        while self._running:
            try:
                await self._poll_once(worker_instance_id)
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.warning("worker poll failed: workerInstanceId=%s", worker_instance_id, exc_info=ex)
            await asyncio.sleep(self._ops_config.worker_poll_interval_ms / 1000.0)

    async def _poll_once(self, worker_instance_id: str) -> None:
        """Claim and process a single task."""
        claimed_task_id = self._task_queue_port.claim_next(worker_instance_id)
        if not claimed_task_id:
            return
        self._pipeline_handler.process_task(
            claimed_task_id,
            worker_instance_id,
            self.WORKER_TYPE,
            self._execution_mode,
        )

    async def _maintenance_loop(self) -> None:
        """Periodic maintenance: heartbeat workers and recover stale claims."""
        await asyncio.sleep(self._ops_config.worker_maintenance_initial_delay_ms / 1000.0)

        while self._running:
            try:
                self._maintenance_tick()
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.warning("worker maintenance failed", exc_info=ex)
            await asyncio.sleep(self._ops_config.worker_maintenance_interval_ms / 1000.0)

    def _maintenance_tick(self) -> None:
        """Heartbeat all worker instances and recover stale claims."""
        for index, worker_id in enumerate(self._worker_instance_ids):
            self._execution_coordinator.touch_worker_instance(
                worker_id,
                self.WORKER_TYPE,
                WorkerStatus.RUNNING.value,
                {
                    "executionMode": self._execution_mode,
                    "slotIndex": index,
                    "workerConcurrency": len(self._worker_instance_ids),
                },
            )

        stale_threshold = datetime.now(timezone.utc) - timedelta(
            seconds=self._ops_config.worker_stale_timeout_seconds,
        )
        self._execution_coordinator.recover_stale_claims(stale_threshold, 20)
