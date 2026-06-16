"""Task command service - handles task lifecycle commands.

Translates the Java TaskCommandService. All methods use async SQLAlchemy sessions
via the TaskRepository.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from backend.config import settings
from backend.domain.enums import AttemptStatus, AttemptTriggerType, TraceLevel, TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import InMemoryTaskQueue, TaskQueuePort
from backend.infrastructure.task_repository import TaskRepository
from backend.models.task import BizTask
from backend.services.task_execution_coordinator import (
    TaskExecutionCoordinator,
    TaskStateTransition,
)


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _trimmed(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    v = value.strip()
    return v if v else fallback


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
        """Create a new generation task. Mirrors Java createGenerationTask()."""
        # Validate required models
        self._require_selected_model(text_analysis_model, "text_analysis_model", "text_analysis_model")
        self._require_selected_model(image_model, "image_model", "image_model")
        task_type_normalized = self._normalize_task_type(task_type, reference_image_urls, asset_type)
        is_video = task_type_normalized == "video_generation"
        if is_video:
            self._require_selected_model(video_model, "video_model", "video_model")

        # Validate seed
        self._normalize_optional_seed(seed)

        default_duration = settings.default_duration_seconds

        task = TaskRecord()
        task.id = "task_" + uuid.uuid4().hex
        task.owner_user_id = owner_user_id
        task.task_type = task_type_normalized
        task.title = _trimmed(title, "Unnamed Task")
        task.status = TaskStatus.PENDING.value
        task.progress = 0
        task.created_at = TaskRecord.now_iso()
        task.updated_at = task.created_at
        task.source_file_name = settings.source_file_name
        task.aspect_ratio = _trimmed(aspect_ratio, settings.default_aspect_ratio)
        task.min_duration_seconds = min_duration_seconds if min_duration_seconds is not None else default_duration
        task.max_duration_seconds = max_duration_seconds if max_duration_seconds is not None else default_duration
        task.retry_count = 0
        task.completed_output_count = 0
        task.has_transcript = bool(transcript_text and transcript_text.strip())
        task.has_timed_transcript = False
        task.source_asset_count = 0
        task.editing_mode = settings.editing_mode
        task.intro_template = settings.intro_template
        task.outro_template = settings.outro_template
        task.creative_prompt = _trimmed(creative_prompt, "")
        task.task_seed = self._normalize_optional_seed(seed)
        task.effect_rating = None
        task.effect_rating_note = ""
        task.rated_at = None
        task.transcript_text = _trimmed(transcript_text, "")

        if task.task_seed is not None:
            task.mutable_execution_context()["taskSeed"] = task.task_seed
        task.mutable_execution_context()["assetType"] = self._normalized_asset_type(asset_type, task.task_type)
        task.mutable_execution_context()["imageSize"] = _trimmed(image_size, "")
        task.mutable_execution_context()["referenceImageUrls"] = self._normalize_string_list(reference_image_urls)
        task.mutable_execution_context()["referenceAssetIds"] = self._normalize_string_list(reference_asset_ids)

        # Request snapshot
        task.request_snapshot = {
            "title": task.title,
            "taskType": task.task_type,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "creativePrompt": task.creative_prompt,
            "seed": task.task_seed,
            "transcriptText": task.transcript_text,
            "imageModel": _trimmed(image_model, ""),
            "videoModel": _trimmed(video_model, ""),
            "textAnalysisModel": _trimmed(text_analysis_model, ""),
            "imageSize": _trimmed(image_size, ""),
            "referenceImageUrls": self._normalize_string_list(reference_image_urls),
            "referenceAssetIds": self._normalize_string_list(reference_asset_ids),
        }

        await self.task_repository.save(task)

        # Create attempt
        attempt_payload: dict[str, Any] = {
            "videoModel": _trimmed(video_model, ""),
            "imageModel": _trimmed(image_model, ""),
            "textAnalysisModel": _trimmed(text_analysis_model, ""),
        }
        self.execution_coordinator.create_attempt(task, AttemptTriggerType.CREATE, attempt_payload)

        # Record trace
        self.execution_coordinator.record_trace(
            task,
            "api",
            "task.created",
            "Task created.",
            "INFO",
            {
                "taskType": task.task_type,
                "taskSeed": task.task_seed if task.task_seed is not None else "",
            },
        )

        # Enqueue
        self.execution_coordinator.enqueue(task, "dispatch", "task.enqueued", "Task enqueued.")

        # Save all mutation data
        await self.task_repository.save(task)

        return task

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    async def retry(self, task: TaskRecord) -> TaskRecord:
        """Retry a failed task."""
        task.retry_count += 1
        task.error_message = ""
        retry_payload = self._build_retry_payload(task, AttemptTriggerType.RETRY)
        self.execution_coordinator.create_attempt(task, AttemptTriggerType.RETRY, retry_payload)
        self.execution_coordinator.enqueue(task, "dispatch", "task.retry_requested", "Task re-enqueued.")
        await self.task_repository.save(task)
        return task

    # ------------------------------------------------------------------
    # Pause
    # ------------------------------------------------------------------

    async def pause(self, task: TaskRecord) -> TaskRecord:
        """Pause an active task."""
        self.execution_coordinator.dequeue(task)
        task.is_queued = False
        task.queue_position = None
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
        )
        await self.task_repository.save(task)
        return task

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------

    async def resume(self, task: TaskRecord) -> TaskRecord:
        """Resume a paused task."""
        retry_payload = self._build_retry_payload(task, AttemptTriggerType.CONTINUE)
        self.execution_coordinator.create_attempt(task, AttemptTriggerType.CONTINUE, retry_payload)
        self.execution_coordinator.enqueue(task, "dispatch", "task.continue_requested", "Task resumed.")
        await self.task_repository.save(task)
        return task

    # ------------------------------------------------------------------
    # Terminate
    # ------------------------------------------------------------------

    async def terminate(self, task: TaskRecord) -> TaskRecord:
        """Terminate an active task."""
        self.execution_coordinator.dequeue(task)
        task.is_queued = False
        task.queue_position = None
        error_message = "Task manually terminated."
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
            lambda t: setattr(t, "error_message", error_message) or setattr(t, "finished_at", TaskRecord.now_iso()),
        )
        await self.task_repository.save(task)
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
            "Task effect rating updated.",
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

    @staticmethod
    def _require_selected_model(value: str | None, field_name: str, label: str) -> str:
        normalized = _trimmed(value, "")
        if normalized:
            return normalized
        raise ValueError(f"Please select {label} ({field_name})")

    @staticmethod
    def _normalize_task_type(
        value: str | None,
        reference_image_urls: list[str] | None,
        asset_type: str | None,
    ) -> str:
        normalized = _trimmed(value, "")
        if not normalized or normalized == "generation":
            if TaskCommandService._normalized_asset_type(asset_type, "") == "character_sheet":
                return "character_sheet"
            urls = TaskCommandService._normalize_string_list(reference_image_urls)
            return "image_to_image" if urls else "video_generation"
        valid_types = {"image_generation", "image_to_image", "character_sheet", "video_generation"}
        return normalized if normalized in valid_types else normalized

    @staticmethod
    def _normalized_asset_type(asset_type: str | None, task_type: str) -> str:
        normalized = _trimmed(asset_type, "")
        if normalized:
            return normalized
        return "character_sheet" if task_type == "character_sheet" else "free"

    @staticmethod
    def _normalize_string_list(values: list[str] | None) -> list[str]:
        if not values:
            return []
        result: list[str] = []
        for v in values:
            n = _trimmed(v, "")
            if n and n not in result:
                result.append(n)
        return result

    @staticmethod
    def _normalize_optional_seed(seed: int | None) -> int | None:
        if seed is None:
            return None
        if seed < 0:
            raise ValueError("seed must be >= 0")
        return seed

    @staticmethod
    def _normalize_effect_rating(rating: int | None) -> int:
        if rating is None:
            raise ValueError("effectRating must not be None")
        if rating < 1 or rating > 5:
            raise ValueError("effectRating must be between 1 and 5")
        return rating

    @staticmethod
    def _normalize_effect_rating_note(note: str | None) -> str:
        normalized = _trimmed(note, "")
        if len(normalized) > 1000:
            raise ValueError("effectRatingNote must not exceed 1000 characters")
        return normalized

    @staticmethod
    def _build_retry_payload(
        task: TaskRecord,
        trigger_type: AttemptTriggerType,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "triggerType": trigger_type.value,
            "retryCount": task.retry_count,
        }
        clip_indices: list[int] = []
        for output in task.outputs_view:
            clip_index = output.get("clipIndex")
            if isinstance(clip_index, int) and clip_index > 0:
                clip_indices.append(clip_index)
        clip_indices.sort()
        completed_clip_count = TaskCommandService._last_contiguous_completed_clip_index(clip_indices)
        if task.storyboard_script:
            payload["resumeFromStage"] = "render" if completed_clip_count > 0 else "planning"
            payload["resumeFromClipIndex"] = max(1, completed_clip_count + 1)
            payload["completedClipCount"] = completed_clip_count
            payload["existingClipIndices"] = clip_indices
            payload["reuseStoryboard"] = True
        return payload

    @staticmethod
    def _last_contiguous_completed_clip_index(clip_indices: list[int]) -> int:
        expected = 1
        for clip_index in clip_indices:
            if clip_index != expected:
                break
            expected += 1
        return expected - 1
