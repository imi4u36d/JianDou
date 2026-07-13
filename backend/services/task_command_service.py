"""Task command service - handles task lifecycle commands.

Translates the Java TaskCommandService. All methods use async SQLAlchemy sessions
via the TaskRepository.
"""

from __future__ import annotations

from typing import Any

from backend.domain.enums import AttemptStatus, AttemptTriggerType, TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_command_inputs import (
    build_retry_payload,
    normalize_effect_rating,
    normalize_effect_rating_note,
    normalize_optional_seed,
    require_selected_model,
)
from backend.services.task_command_mutations import merge_task_mutation
from backend.services.task_creation_service import TaskCreationService
from backend.services.task_execution_coordinator import (
    TaskExecutionCoordinator,
    TaskStateTransition,
)


class TaskCommandService:
    """Handles command-type operations on tasks: create, retry, pause, etc."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
    ) -> None:
        self._task_repository: TaskRepository | None = task_repository
        self._execution_coordinator: TaskExecutionCoordinator = (
            execution_coordinator or TaskExecutionCoordinator()
        )
        self._creation_service = TaskCreationService(
            lambda: self.task_repository,
            self._execution_coordinator,
        )

    # ------------------------------------------------------------------
    # Properties for DI-friendly access
    # ------------------------------------------------------------------

    @property
    def task_repository(self) -> TaskRepository:
        if self._task_repository is None:
            raise RuntimeError("TaskRepository not configured")
        return self._task_repository

    @task_repository.setter
    def task_repository(self, repo: TaskRepository) -> None:
        self._task_repository = repo

    @property
    def execution_coordinator(self) -> TaskExecutionCoordinator:
        return self._execution_coordinator

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_generation_task(
        self,
        owner_user_id: int,
        title: str = "",
        task_type: str | None = None,
        aspect_ratio: str | None = None,
        min_duration_seconds: int | None = None,
        max_duration_seconds: int | None = None,
        creative_prompt: str | None = None,
        seed: int | None = None,
        transcript_text: str | None = None,
        image_model: str | None = None,
        video_model: str | None = None,
        text_analysis_model: str | None = None,
        image_size: str | None = None,
        reference_image_urls: list[str] | None = None,
        reference_asset_ids: list[str] | None = None,
        asset_type: str | None = None,
        **kwargs: Any,
    ) -> TaskRecord:
        return await self._creation_service.create_generation_task(
            owner_user_id=owner_user_id,
            title=title,
            task_type=task_type,
            aspect_ratio=aspect_ratio,
            min_duration_seconds=min_duration_seconds,
            max_duration_seconds=max_duration_seconds,
            creative_prompt=creative_prompt,
            seed=seed,
            transcript_text=transcript_text,
            image_model=image_model,
            video_model=video_model,
            text_analysis_model=text_analysis_model,
            image_size=image_size,
            reference_image_urls=reference_image_urls,
            reference_asset_ids=reference_asset_ids,
            asset_type=asset_type,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    async def retry(self, task: TaskRecord) -> TaskRecord:
        """Retry a failed task."""
        task.retry_count += 1
        task.error_message = ""
        task.started_at = None
        task.finished_at = None
        retry_payload = self._build_retry_payload(task, AttemptTriggerType.RETRY)
        mutation = TaskPersistenceMutation().set_task(task)
        mutation = self._merge_mutation(
            mutation,
            self.execution_coordinator.create_attempt(
                task, AttemptTriggerType.RETRY, retry_payload
            ),
        )
        mutation = self._merge_mutation(
            mutation,
            self.execution_coordinator.enqueue(
                task,
                "dispatch",
                "task.retry_requested",
                "Task re-enqueued.",
            ),
        )
        await self.task_repository.save_mutation(mutation)
        return task

    # ------------------------------------------------------------------
    # Pause
    # ------------------------------------------------------------------

    async def pause(self, task: TaskRecord) -> TaskRecord:
        """Pause an active task."""
        mutation = TaskPersistenceMutation().set_task(task)
        mutation = self._merge_mutation(mutation, self.execution_coordinator.dequeue(task))
        task.is_queued = False
        task.queue_position = None
        mutation = self._merge_mutation(
            mutation,
            self.execution_coordinator.transition_task(
                task,
                TaskStateTransition.info(
                    TaskStatus.PAUSED.value,
                    task.progress,
                    "api",
                    "task.paused",
                    "Task paused.",
                    {"reason": "manual"},
                ).with_attempt(AttemptStatus.PAUSED, ""),
            ),
        )
        await self.task_repository.save_mutation(mutation)
        return task

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------

    async def resume(self, task: TaskRecord) -> TaskRecord:
        """Resume a paused task."""
        task.started_at = None
        task.finished_at = None
        retry_payload = self._build_retry_payload(task, AttemptTriggerType.CONTINUE)
        mutation = TaskPersistenceMutation().set_task(task)
        mutation = self._merge_mutation(
            mutation,
            self.execution_coordinator.create_attempt(
                task, AttemptTriggerType.CONTINUE, retry_payload
            ),
        )
        mutation = self._merge_mutation(
            mutation,
            self.execution_coordinator.enqueue(
                task,
                "dispatch",
                "task.continue_requested",
                "Task resumed.",
            ),
        )
        await self.task_repository.save_mutation(mutation)
        return task

    _merge_mutation = staticmethod(merge_task_mutation)

    # ------------------------------------------------------------------
    # Terminate
    # ------------------------------------------------------------------

    async def terminate(self, task: TaskRecord) -> TaskRecord:
        """Terminate an active task."""
        mutation = TaskPersistenceMutation().set_task(task)
        mutation = self._merge_mutation(mutation, self.execution_coordinator.dequeue(task))
        task.is_queued = False
        task.queue_position = None
        error_message = "Task manually terminated."
        mutation = self._merge_mutation(
            mutation,
            self.execution_coordinator.transition_task(
                task,
                TaskStateTransition.warn(
                    TaskStatus.FAILED.value,
                    task.progress,
                    "api",
                    "task.terminated",
                    "Task terminated.",
                    {"reason": "manual"},
                ).with_attempt(AttemptStatus.TERMINATED, error_message),
                lambda t: setattr(t, "error_message", error_message)
                or setattr(t, "finished_at", TaskRecord.now_iso()),
            ),
        )
        await self.task_repository.save_mutation(mutation)
        return task

    # ------------------------------------------------------------------
    # Rate effect
    # ------------------------------------------------------------------

    async def rate_effect(
        self,
        task: TaskRecord,
        effect_rating: int,
        effect_rating_note: str | None = None,
    ) -> TaskRecord:
        """Rate the effect of a completed task."""
        normalized_note = self._normalize_effect_rating_note(effect_rating_note)
        task.effect_rating = self._normalize_effect_rating(effect_rating)
        task.effect_rating_note = normalized_note
        task.rated_at = TaskRecord.now_iso()
        task.mutable_execution_context()["effectRating"] = task.effect_rating
        task.mutable_execution_context()["effectRatingNote"] = normalized_note
        task.mutable_execution_context()["ratedAt"] = task.rated_at
        await self.task_repository.save(task)
        self.execution_coordinator.record_trace(
            task,
            "feedback",
            "task.effect_rated",
            "已更新任务效果评分。",
            "INFO",
            {
                "effectRating": task.effect_rating,
                "effectRatingNote": normalized_note,
                "taskSeed": task.task_seed if task.task_seed is not None else "",
            },
        )
        await self.task_repository.save(task)
        return task

    # ------------------------------------------------------------------
    # Delete (soft delete)
    # ------------------------------------------------------------------

    async def delete_task(self, task: TaskRecord) -> dict[str, Any]:
        """Soft delete a task."""
        self.execution_coordinator.dequeue(task)
        await self.task_repository.delete(task.id)
        return {"taskId": task.id, "deleted": True}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _require_selected_model = staticmethod(require_selected_model)
    _normalize_optional_seed = staticmethod(normalize_optional_seed)
    _normalize_effect_rating = staticmethod(normalize_effect_rating)
    _normalize_effect_rating_note = staticmethod(normalize_effect_rating_note)
    _build_retry_payload = staticmethod(build_retry_payload)
