"""Task diagnosis adapter and temporary queue compatibility exports."""

from __future__ import annotations

from typing import Any

from backend.domain import task_queue_fairness
from backend.domain.task_diagnosis import TaskDiagnosisRules, TaskDiagnosisSnapshot
from backend.domain.task_monitoring import task_monitoring_snapshot, task_outputs
from backend.domain.task_resume import existing_video_clip_indices
from backend.services.task_queue_coordinator import TaskQueueCoordinator
from backend.services.task_request_snapshot_factory import TaskRequestSnapshotFactory
from backend.shared import string_value

OwnerResolver = task_queue_fairness.OwnerResolver
TaskQueueFairScheduler = task_queue_fairness.TaskQueueFairScheduler

__all__ = [
    "OwnerResolver",
    "TaskDiagnosisService",
    "TaskQueueCoordinator",
    "TaskQueueFairScheduler",
    "TaskRequestSnapshotFactory",
]


class TaskDiagnosisService:
    """Adapt task aggregates into snapshots consumed by pure diagnosis rules."""

    def __init__(self, rules: TaskDiagnosisRules | None = None) -> None:
        self._rules = rules or TaskDiagnosisRules()

    def diagnose(self, task: Any) -> dict[str, Any]:
        return self._rules.diagnose(self._snapshot(task))

    def severity(self, task: Any) -> str:
        return self._rules.severity(self._snapshot(task))

    @staticmethod
    def _snapshot(task: Any) -> TaskDiagnosisSnapshot:
        outputs = task_outputs(task)
        monitoring = task_monitoring_snapshot(task)
        legacy_monitoring = getattr(task, "monitoring", None)
        if isinstance(legacy_monitoring, dict):
            monitoring.update(
                {
                    key: value
                    for key, value in legacy_monitoring.items()
                    if value not in (None, "", [])
                }
            )
        return TaskDiagnosisSnapshot(
            task_id=getattr(task, "id", ""),
            title=getattr(task, "title", ""),
            status=string_value(getattr(task, "status", "")),
            error_message=getattr(task, "error_message", None),
            is_queued=bool(getattr(task, "is_queued", False)),
            queue_position=getattr(task, "queue_position", None),
            monitoring=monitoring,
            outputs=outputs,
            rendered_clip_indices=existing_video_clip_indices(outputs),
        )
