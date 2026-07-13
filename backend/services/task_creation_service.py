"""Generation-task construction, charging, enqueueing, and persistence."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from backend.config import settings
from backend.domain.enums import AttemptTriggerType, TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_command_inputs import (
    credit_feature_code,
    normalize_optional_seed,
    normalize_output_count,
    normalize_string_list,
    normalize_task_type,
    normalized_asset_type,
    require_selected_model,
    trimmed,
)
from backend.services.task_command_mutations import merge_task_mutation
from backend.services.task_execution_coordinator import TaskExecutionCoordinator


class TaskCreationService:
    def __init__(
        self,
        repository: Callable[[], TaskRepository],
        coordinator: TaskExecutionCoordinator,
    ) -> None:
        self._repository = repository
        self._coordinator = coordinator

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
        require_selected_model(text_analysis_model, "text_analysis_model", "text_analysis_model")
        require_selected_model(image_model, "image_model", "image_model")
        normalized_type = normalize_task_type(task_type, reference_image_urls, asset_type)
        if normalized_type == "video_generation":
            require_selected_model(video_model, "video_model", "video_model")
        normalized_seed = normalize_optional_seed(seed)
        task = self._new_task(
            owner_user_id=owner_user_id,
            title=title,
            task_type=normalized_type,
            aspect_ratio=aspect_ratio,
            min_duration_seconds=min_duration_seconds,
            max_duration_seconds=max_duration_seconds,
            creative_prompt=creative_prompt,
            seed=normalized_seed,
            transcript_text=transcript_text,
        )
        context = task.mutable_execution_context()
        if task.task_seed is not None:
            context["taskSeed"] = task.task_seed
        context.update({
            "assetType": normalized_asset_type(asset_type, task.task_type),
            "imageSize": trimmed(image_size, ""),
            "referenceImageUrls": normalize_string_list(reference_image_urls),
            "referenceAssetIds": normalize_string_list(reference_asset_ids),
        })
        task.request_snapshot = self._request_snapshot(
            task,
            image_model,
            video_model,
            text_analysis_model,
            image_size,
            reference_image_urls,
            reference_asset_ids,
            kwargs,
        )

        mutation = TaskPersistenceMutation().set_task(task)
        mutation = merge_task_mutation(
            mutation,
            self._coordinator.create_attempt(
                task,
                AttemptTriggerType.CREATE,
                {
                    "videoModel": trimmed(video_model, ""),
                    "imageModel": trimmed(image_model, ""),
                    "textAnalysisModel": trimmed(text_analysis_model, ""),
                },
            ),
        )
        mutation = merge_task_mutation(
            mutation,
            self._coordinator.record_trace(
                task,
                "api",
                "task.created",
                "任务已创建，等待调度。",
                "INFO",
                {
                    "taskType": task.task_type,
                    "taskSeed": task.task_seed if task.task_seed is not None else "",
                },
            ),
        )
        mutation = merge_task_mutation(
            mutation,
            self._coordinator.enqueue(
                task,
                "dispatch",
                "task.enqueued",
                "任务已加入执行队列。",
            ),
        )
        await self._charge(task, owner_user_id)
        await self._repository().save_mutation(mutation)
        return task

    @staticmethod
    def _new_task(
        owner_user_id: int,
        title: str,
        task_type: str,
        aspect_ratio: str | None,
        min_duration_seconds: int | None,
        max_duration_seconds: int | None,
        creative_prompt: str | None,
        seed: int | None,
        transcript_text: str | None,
    ) -> TaskRecord:
        default_duration = settings.default_duration_seconds
        now = TaskRecord.now_iso()
        task = TaskRecord(
            id="task_" + uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            task_type=task_type,
            title=trimmed(title, "Unnamed Task"),
            status=TaskStatus.PENDING.value,
            progress=0,
            created_at=now,
            updated_at=now,
        )
        task.source_file_name = settings.source_file_name
        task.aspect_ratio = trimmed(aspect_ratio, settings.default_aspect_ratio)
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
        task.creative_prompt = trimmed(creative_prompt, "")
        task.task_seed = seed
        task.effect_rating = None
        task.effect_rating_note = ""
        task.rated_at = None
        task.transcript_text = trimmed(transcript_text, "")
        return task

    @staticmethod
    def _request_snapshot(
        task: TaskRecord,
        image_model: str | None,
        video_model: str | None,
        text_analysis_model: str | None,
        image_size: str | None,
        reference_image_urls: list[str] | None,
        reference_asset_ids: list[str] | None,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "title": task.title,
            "taskType": task.task_type,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "creativePrompt": task.creative_prompt,
            "seed": task.task_seed,
            "transcriptText": task.transcript_text,
            "imageModel": trimmed(image_model, ""),
            "videoModel": trimmed(video_model, ""),
            "textAnalysisModel": trimmed(text_analysis_model, ""),
            "imageSize": trimmed(image_size, ""),
            "videoSize": trimmed(options.get("video_size"), ""),
            "videoDurationSeconds": options.get("video_duration_seconds"),
            "outputCount": normalize_output_count(options.get("output_count")),
            "stopBeforeVideoGeneration": bool(options.get("stop_before_video_generation")),
            "referenceImageUrls": normalize_string_list(reference_image_urls),
            "referenceAssetIds": normalize_string_list(reference_asset_ids),
        }

    async def _charge(self, task: TaskRecord, owner_user_id: int) -> None:
        feature_code = credit_feature_code(task.task_type)
        if not feature_code:
            return
        from backend.services.credit_service import CreditService

        repository = self._repository()
        try:
            charge = await CreditService(repository.session).charge(
                owner_user_id,
                feature_code,
                task_id=task.id,
                reason="任务创建扣费",
                commit=False,
            )
        except Exception:
            await repository.session.rollback()
            raise
        task.mutable_execution_context()["creditCharge"] = charge
