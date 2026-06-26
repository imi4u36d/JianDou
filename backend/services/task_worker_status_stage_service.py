from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from backend.domain.enums import AttemptStatus, TaskStatus, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import TaskQueuePort
from backend.infrastructure.task_repository import TaskRepository
from backend.services.generation_service import GenerationProviderException
from backend.services.task_execution_coordinator import TaskExecutionCoordinator, TaskStateTransition
from backend.shared import first_non_blank, now_iso, string_value

_ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def map_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable_id(prefix: str, *parts: str) -> str:
    seed = prefix + ":" + ":".join(parts)
    return prefix + "_" + uuid.uuid5(uuid.NAMESPACE_OID, seed).hex


def _duration_millis(started_at: str, finished_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(finished_at)
        return max(0, int((end - start).total_seconds() * 1000))
    except (ValueError, TypeError):
        return 0


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
        now = now_iso()
        row: dict[str, Any] = {
            "stageRunId": _stable_id("stgrun", task.id, stage_name, str(clip_index)),
            "attemptId": task.active_attempt_id,
            "stageName": stage_name,
            "stageSeq": seq,
            "clipIndex": clip_index,
            "status": "COMPLETED",
            "workerInstanceId": run_context.worker_instance_id,
            "startedAt": now,
            "finishedAt": now,
            "durationMs": 0,
            "inputSummary": input_summary,
            "outputSummary": output_summary,
            "errorCode": "",
            "errorMessage": "",
        }
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
        now = now_iso()
        model_section = map_value(request_payload.get("model"))
        provider_model = first_non_blank(
            string_value(model_section.get("providerModel")),
            string_value(model_section.get("textAnalysisModel")),
        )
        return {
            "modelCallId": _stable_id("mdlcall", task.id, stage, kind, str(clip_index)),
            "requestLogId": "reqlog_" + _stable_id("mdlcall", task.id, stage, kind, str(clip_index)),
            "callKind": stage,
            "stage": stage,
            "operation": operation,
            "provider": "generation",
            "providerModel": provider_model,
            "requestedModel": provider_model,
            "resolvedModel": "",
            "modelName": "",
            "modelAlias": provider_model,
            "endpointHost": "",
            "requestId": "",
            "requestPayload": request_payload,
            "responsePayload": {},
            "httpStatus": 0,
            "responseCode": 0,
            "success": False,
            "status": "pending",
            "errorCode": "",
            "errorMessage": "",
            "latencyMs": 0,
            "durationMs": 0,
            "inputTokens": 0,
            "outputTokens": 0,
            "startedAt": now,
            "finishedAt": now,
        }

    def complete_model_call(
        self, pending_model_call: dict[str, Any], run: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        row = dict(pending_model_call or {})
        model_info = map_value(result.get("modelInfo"))
        started_at = string_value(row.get("startedAt"))
        finished_at = string_value(run.get("updatedAt", now_iso()))
        row["provider"] = string_value(model_info.get("provider", row.get("provider")))
        row["providerModel"] = first_non_blank(
            string_value(model_info.get("providerModel")), string_value(row.get("providerModel"))
        )
        row["requestedModel"] = first_non_blank(
            string_value(model_info.get("requestedModel")), string_value(row.get("requestedModel"))
        )
        row["resolvedModel"] = string_value(model_info.get("resolvedModel"))
        row["modelName"] = string_value(model_info.get("modelName", model_info.get("resolvedModel")))
        row["modelAlias"] = string_value(model_info.get("modelName", model_info.get("resolvedModel")))
        row["endpointHost"] = string_value(model_info.get("endpointHost"))
        row["requestId"] = string_value(run.get("id"))
        row["responsePayload"] = {"runId": string_value(run.get("id")), "result": result}
        row["httpStatus"] = 200
        row["responseCode"] = 200
        row["success"] = True
        row["status"] = "success"
        row["errorCode"] = ""
        row["errorMessage"] = ""
        row["latencyMs"] = 0
        row["durationMs"] = _duration_millis(started_at, finished_at)
        row["finishedAt"] = finished_at
        return row

    def fail_model_call(self, pending_model_call: dict[str, Any], error: Exception) -> dict[str, Any]:
        row = dict(pending_model_call or {})
        started_at = string_value(row.get("startedAt"))
        finished_at = now_iso()
        http_status = error.http_status if isinstance(error, GenerationProviderException) else 0
        response_payload: dict[str, Any] = {
            "errorType": error.__class__.__name__ if error else "",
            "errorMessage": first_non_blank(str(error) if error else "", "unknown"),
        }
        if isinstance(error, GenerationProviderException):
            response_payload["providerRequest"] = error.provider_request
            response_payload["providerResponse"] = error.provider_response
            response_payload["httpStatus"] = error.http_status
        row["responsePayload"] = response_payload
        row["httpStatus"] = max(0, http_status)
        row["responseCode"] = max(0, http_status)
        row["success"] = False
        row["status"] = "failed"
        row["errorCode"] = error.__class__.__name__ if error else ""
        row["errorMessage"] = first_non_blank(str(error) if error else "", "unknown")
        row["durationMs"] = _duration_millis(started_at, finished_at)
        row["finishedAt"] = finished_at
        return row

    def record_run_call_chain(
        self, task: TaskRecord, fallback_stage: str, run: dict[str, Any], result: dict[str, Any]
    ) -> None:
        raw = result.get("callChain")
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, dict):
                continue
            stage = string_value(item.get("stage"))
            event = string_value(item.get("event"))
            message = string_value(item.get("message"))
            status = string_value(item.get("status"))
            level = "INFO" if status.lower() == "success" else "WARN"
            self._execution_coordinator.record_trace(
                task,
                stage if stage else fallback_stage,
                event if event else "generation.call",
                message if message else "generation run completed",
                level,
                {"runId": string_value(run.get("id")), "status": status, "details": map_value(item.get("details"))},
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
