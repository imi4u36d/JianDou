from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.domain.json_payloads import write_json_object
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository_entity_upserts import TaskRepositoryEntityUpserts
from backend.models.task import (
    BizTaskQueueEvent,
    BizTaskStatusHistory,
)
from backend.shared import now_iso, safe_int, string_value

if TYPE_CHECKING:
    from backend.infrastructure.task_repository import TaskRepository


class TaskRepositoryMutationService(TaskRepositoryEntityUpserts):
    """Atomic task aggregate writes delegated by :class:`TaskRepository`."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)

    async def save(self, task_record: TaskRecord) -> None:
        """Upsert the main task row."""
        async with self._lock:
            try:
                await self._save_without_lock(task_record)
                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        """Persist a full mutation atomically (task + sub-entities)."""
        async with self._lock:
            try:
                # 1. Task main row
                if mutation.task:
                    await self._save_without_lock(mutation.task)

                task_id = mutation.task_id or (mutation.task.id if mutation.task else "")

                # 2. Attempts (upsert by task_attempt_id)
                for row in mutation.attempts:
                    await self._upsert_attempt(task_id, row)

                # 3. Status history
                for row in mutation.status_history_rows:
                    self.session.add(
                        BizTaskStatusHistory(
                            task_status_history_id=string_value(row.get("statusHistoryId", row.get("id", ""))),
                            task_id=task_id,
                            previous_status=string_value(row.get("previousStatus", "")),
                            current_status=string_value(row.get("nextStatus", "")),
                            progress=safe_int(row.get("progress")),
                            stage=string_value(row.get("stage")),
                            event=string_value(row.get("event")),
                            message=string_value(row.get("reason", row.get("message", ""))),
                            payload_json=write_json_object(row.get("payload", {})),
                            change_time=string_value(row.get("changedAt", row.get("timestamp", now_iso()))),
                            operator_type="system",
                            operator_id="",
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 4. Trace rows -> store as BizTaskStatusHistory with special event prefix
                for row in mutation.trace_rows:
                    self.session.add(
                        BizTaskStatusHistory(
                            task_status_history_id=string_value(row.get("traceId", row.get("id", ""))),
                            task_id=task_id,
                            previous_status="",
                            current_status="",
                            progress=0,
                            stage=string_value(row.get("stage")),
                            event=string_value(row.get("event")),
                            message=string_value(row.get("message")),
                            payload_json=write_json_object(row.get("payload", {})),
                            change_time=string_value(row.get("timestamp", now_iso())),
                            operator_type="trace",
                            operator_id="",
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 5. Stage runs
                for row in mutation.stage_run_rows:
                    await self._upsert_stage_run(task_id, row)

                # 6. Model calls
                for row in mutation.model_call_rows:
                    await self._upsert_model_call(task_id, row)

                # 7. Materials
                for row in mutation.material_rows:
                    await self._upsert_material_asset(task_id, mutation.task, row)

                # 8. Results
                for row in mutation.result_rows:
                    await self._upsert_task_result(task_id, row)

                # 9. Queue events
                for row in mutation.queue_event_rows:
                    self.session.add(
                        BizTaskQueueEvent(
                            task_queue_event_id=string_value(row.get("taskQueueEventId", row.get("id", ""))),
                            task_id=task_id,
                            attempt_id=string_value(row.get("attemptId", "")),
                            queue_name=string_value(row.get("queueName", "default")),
                            event_type=string_value(row.get("eventType", "")),
                            worker_instance_id=string_value(row.get("workerInstanceId", "")),
                            queue_position_hint=safe_int(row.get("queuePositionHint"), 0),
                            payload_json=write_json_object(row.get("payload", {})),
                            event_time=string_value(row.get("eventTime", now_iso())),
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 10. Worker instances (upsert)
                for row in mutation.worker_instance_rows:
                    await self._upsert_worker_instance(row)

                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise
