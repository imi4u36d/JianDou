from __future__ import annotations

from typing import Any

from backend.domain.enums import AttemptStatus, TaskStatus, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import TaskQueuePort
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_execution_coordinator import TaskExecutionCoordinator, TaskStateTransition
from backend.services.task_worker_record_factory import TaskWorkerRecordFactory
from backend.shared import first_non_blank, string_value


class TaskWorkerExecutionContext:
    """Execution context for a single worker run."""

    def __init__(
        self,
        worker_instance_id: str,
        worker_type: str,
        execution_mode: str,
    ) -> None:
        self._worker_instance_id = worker_instance_id
        self._worker_type = worker_type
        self._execution_mode = execution_mode

    @property
    def worker_instance_id(self) -> str:
        return self._worker_instance_id

    @property
    def worker_type(self) -> str:
        return self._worker_type

    @property
    def execution_mode(self) -> str:
        return self._execution_mode


class TaskExecutionAbortedException(Exception):
    """Raised when task execution is aborted (paused, cancelled, etc.)."""

    def __init__(self, task_status: str, message: str = "") -> None:
        super().__init__(message)
        self._task_status = task_status

    @property
    def task_status(self) -> str:
        return self._task_status


class TaskStage:
    ANALYSIS = "analysis"
    PLANNING = "planning"
    RENDER = "render"
    PIPELINE = "pipeline"
    DISPATCH = "dispatch"
    PAUSED = "paused"


class TaskWorkerStatusStageService:
    """Service for tracking status, model calls, stage runs, and lifecycle events."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        task_queue_port: TaskQueuePort | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._task_queue_port = task_queue_port
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        self._record_factory = TaskWorkerRecordFactory()

    def update_status(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
    ) -> dict[str, Any]:
        self._assert_task_still_active(task)
        return self._execution_coordinator.transition_task(
            task,
            TaskStateTransition.info(
                next_status,
                progress,
                stage,
                event,
                message,
                {"workerInstanceId": run_context.worker_instance_id},
            ),
        )

    def record_stage_run(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        seq: int,
        stage_name: str,
        clip_index: int,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
    ) -> dict[str, Any]:
        row = self._record_factory.stage_run(
            task, run_context.worker_instance_id, seq, stage_name, clip_index, input_summary, output_summary
        )
        return self._execution_coordinator.record_stage_run(task, row)

    def create_pending_model_call(
        self,
        task: TaskRecord,
        stage: str,
        operation: str,
        request_payload: dict[str, Any],
        clip_index: int,
        kind: str,
    ) -> dict[str, Any]:
        return self._record_factory.pending_model_call(task, stage, operation, request_payload, clip_index, kind)

    def complete_model_call(
        self, pending_model_call: dict[str, Any], run: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        return self._record_factory.complete_model_call(pending_model_call, run, result)

    def fail_model_call(self, pending_model_call: dict[str, Any], error: Exception) -> dict[str, Any]:
        return self._record_factory.fail_model_call(pending_model_call, error)

    def record_run_call_chain(
        self, task: TaskRecord, fallback_stage: str, run: dict[str, Any], result: dict[str, Any]
    ) -> None:
        for trace in self._record_factory.run_call_chain(fallback_stage, run, result):
            self._execution_coordinator.record_trace(
                task,
                trace["stage"],
                trace["event"],
                trace["message"],
                trace["level"],
                trace["payload"],
            )

    def complete_task(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        script_run: dict[str, Any],
        image_run_ids: list[str],
        video_run_ids: list[str],
        clip_count: int,
        latest_video_output_url: str,
    ) -> dict[str, Any]:
        self._assert_task_still_active(task)
        result = self._execution_coordinator.transition_task(
            task,
            TaskStateTransition.info(
                "COMPLETED",
                100,
                TaskStage.PIPELINE,
                "task.completed",
                "任务生成流程已完成。",
                {
                    "scriptRunId": string_value(script_run.get("id")),
                    "imageRunIds": image_run_ids,
                    "videoRunIds": video_run_ids,
                    "clipCount": clip_count,
                    "outputUrl": latest_video_output_url,
                },
            ).with_attempt(AttemptStatus.FINISHED.value, ""),
        )
        self._execution_coordinator.touch_worker_instance(
            run_context.worker_instance_id,
            run_context.worker_type,
            WorkerStatus.RUNNING.value,
            {"lastTaskId": task.id, "lastTaskStatus": "COMPLETED"},
        )
        return result

    def complete_workspace_image_task(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        image_run: dict[str, Any],
        output_url: str,
        output_count: int = 1,
        image_run_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        self._assert_task_still_active(task)
        task.completed_output_count = max(1, output_count)
        result = self._execution_coordinator.transition_task(
            task,
            TaskStateTransition.info(
                "COMPLETED",
                100,
                TaskStage.PIPELINE,
                "task.completed",
                "图片生成任务已完成。",
                {
                    "imageRunId": string_value(image_run.get("id")),
                    "imageRunIds": image_run_ids or [string_value(image_run.get("id"))],
                    "outputUrl": output_url,
                    "outputCount": output_count,
                    "taskType": task.task_type,
                },
            ).with_attempt(AttemptStatus.FINISHED.value, ""),
        )
        self._execution_coordinator.touch_worker_instance(
            run_context.worker_instance_id,
            run_context.worker_type,
            WorkerStatus.RUNNING.value,
            {"lastTaskId": task.id, "lastTaskStatus": "COMPLETED"},
        )
        return result

    def handle_abort(
        self, task: TaskRecord, run_context: TaskWorkerExecutionContext, task_status: str
    ) -> dict[str, Any]:
        return self._execution_coordinator.touch_worker_instance(
            run_context.worker_instance_id,
            run_context.worker_type,
            WorkerStatus.RUNNING.value,
            {"lastTaskId": task.id, "lastTaskStatus": task_status},
        )

    def fail_task(self, task: TaskRecord, run_context: TaskWorkerExecutionContext, ex: Exception) -> dict[str, Any]:
        try:
            if self._task_queue_port:
                self._task_queue_port.remove(task.id)
            task.is_queued = False
            task.queue_position = None
            error_message = str(ex) if ex else "任务执行失败"
            result = self._execution_coordinator.transition_task(
                task,
                TaskStateTransition.error(
                    "FAILED",
                    task.progress,
                    TaskStage.PIPELINE,
                    "task.failed",
                    "任务执行异常，已标记为失败状态。",
                    {"error": error_message},
                ).with_attempt(AttemptStatus.FAILED.value, error_message),
            )
            worker_result = self._execution_coordinator.touch_worker_instance(
                run_context.worker_instance_id,
                run_context.worker_type,
                WorkerStatus.RUNNING.value,
                {"lastTaskId": task.id, "lastTaskStatus": "FAILED"},
            )
            mutation = result.get("mutation", TaskPersistenceMutation())
            worker_mutation = worker_result.get("mutation") if isinstance(worker_result, dict) else None
            if isinstance(worker_mutation, TaskPersistenceMutation):
                for row in worker_mutation.worker_instance_rows:
                    mutation = mutation.add_worker_instance(row)
            result["mutation"] = mutation
            return result
        except Exception:
            return self._execution_coordinator.touch_worker_instance(
                run_context.worker_instance_id,
                run_context.worker_type,
                WorkerStatus.FAILED.value,
                {"executionMode": run_context.execution_mode},
            )

    def _assert_task_still_active(self, task: TaskRecord) -> None:
        if self._task_repository is None:
            return
        if TaskStatus.is_execution_active(TaskStatus(task.status) if TaskStatus(task.status) else None):
            return
        raise TaskExecutionAbortedException(
            task.status,
            first_non_blank(task.error_message, "任务已停止执行。"),
        )
