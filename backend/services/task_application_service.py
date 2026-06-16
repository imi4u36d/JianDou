"""Task application service implementation - orchestrates task lifecycle operations.

Mirrors the Java TaskApplicationServiceImpl class.
Delegates to query and command services for the heavy lifting.
"""

from __future__ import annotations

from typing import Any

from backend.services.task_command_service import TaskCommandService
from backend.services.task_query_service import TaskQueryService


def _trimmed(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    v = value.strip()
    return v if v else fallback


class TaskApplicationServiceImpl:
    """Application service implementation for task operations.

    Mirrors the Java TaskApplicationServiceImpl.
    Delegates reads to TaskQueryService and writes to TaskCommandService.
    """

    def __init__(
        self,
        query_service: TaskQueryService,
        command_service: TaskCommandService,
    ) -> None:
        self._query_service = query_service
        self._command_service = command_service

    # ------------------------------------------------------------------
    # Create / Generate
    # ------------------------------------------------------------------

    async def create_generation_task(self, request: Any) -> dict[str, Any]:
        """Create a generation task and return its detail."""
        owner_user_id = self._require_current_user_id()
        task = await self._command_service.create_generation_task(
            owner_user_id=owner_user_id,
            title=_trimmed(getattr(request, "title", None) if hasattr(request, "title") else
                          getattr(request, "title", None), ""),
            task_type=getattr(request, "task_type", None) if hasattr(request, "task_type") else
                      getattr(request, "taskType", None),
            aspect_ratio=getattr(request, "aspect_ratio", None) if hasattr(request, "aspect_ratio") else
                         getattr(request, "aspectRatio", None),
            min_duration_seconds=getattr(request, "min_duration_seconds", None) if hasattr(request, "min_duration_seconds") else
                                  getattr(request, "minDurationSeconds", None),
            max_duration_seconds=getattr(request, "max_duration_seconds", None) if hasattr(request, "max_duration_seconds") else
                                  getattr(request, "maxDurationSeconds", None),
            creative_prompt=getattr(request, "creative_prompt", None) if hasattr(request, "creative_prompt") else
                             getattr(request, "creativePrompt", None),
            seed=getattr(request, "seed", None) if hasattr(request, "seed") else
                  getattr(request, "taskSeed", None),
            transcript_text=getattr(request, "transcript_text", None) if hasattr(request, "transcript_text") else
                             getattr(request, "transcriptText", None),
            image_model=getattr(request, "image_model", None) if hasattr(request, "image_model") else
                         getattr(request, "imageModel", None),
            video_model=getattr(request, "video_model", None) if hasattr(request, "video_model") else
                         getattr(request, "videoModel", None),
            text_analysis_model=getattr(request, "text_analysis_model", None) if hasattr(request, "text_analysis_model") else
                                 getattr(request, "textAnalysisModel", None),
            image_size=getattr(request, "image_size", None) if hasattr(request, "image_size") else
                        getattr(request, "imageSize", None),
            reference_image_urls=getattr(request, "reference_image_urls", None) if hasattr(request, "reference_image_urls") else
                                  getattr(request, "referenceImageUrls", None),
            reference_asset_ids=getattr(request, "reference_asset_ids", None) if hasattr(request, "reference_asset_ids") else
                                 getattr(request, "referenceAssetIds", None),
            asset_type=getattr(request, "asset_type", None) if hasattr(request, "asset_type") else
                        getattr(request, "assetType", None),
        )
        return await self._query_service.get_task(task.id, owner_user_id)

    async def generate_creative_prompt(self, request: Any) -> dict[str, Any]:
        """Generate a creative prompt stub."""
        owner_user_id = self._require_current_user_id()
        title = _trimmed(
            getattr(request, "title", None) if hasattr(request, "title") else
            getattr(request, "title", None), "Unnamed Task",
        )
        prompt = f"Short drama style, emotional progression, facial expressions fitting the context, realistic cinematography, dialogue and voiceover matching plot: {title}"
        return {
            "prompt": prompt,
            "source": "default",  # placeholder for taskDefaultsProperties.getPromptSource()
        }

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        user_id: int,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tasks owned by the user."""
        return await self._query_service.list_tasks(user_id, q, status, sort)

    async def admin_list_tasks(
        self,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all tasks (admin)."""
        return await self._query_service.admin_list_tasks(q, status, sort)

    async def showcase_cases(self) -> dict[str, Any]:
        """Return public showcase data."""
        return await self._query_service.showcase_cases()

    async def get_task(self, task_id: str, user_id: int) -> dict[str, Any]:
        """Get a single task by ID with owner check."""
        return await self._query_service.get_task(task_id, user_id)

    async def admin_get_task(self, task_id: str) -> dict[str, Any]:
        """Get task detail without owner check."""
        return await self._query_service.admin_get_task(task_id)

    # ------------------------------------------------------------------
    # Sub-collections
    # ------------------------------------------------------------------

    async def get_trace(self, task_id: str, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.get_trace(task_id, user_id, limit)

    async def get_logs(self, task_id: str, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.get_logs(task_id, user_id, limit)

    async def get_status_history(self, task_id: str, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.get_status_history(task_id, user_id, limit)

    async def get_model_calls(self, task_id: str, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.get_model_calls(task_id, user_id, limit)

    async def get_results(self, task_id: str, user_id: int) -> list[dict[str, Any]]:
        return await self._query_service.get_results(task_id, user_id)

    async def get_materials(self, task_id: str, user_id: int) -> list[dict[str, Any]]:
        return await self._query_service.get_materials(task_id, user_id)

    # ------------------------------------------------------------------
    # Remote task query
    # ------------------------------------------------------------------

    async def get_seedance_task_result(self, remote_task_id: str) -> dict[str, Any]:
        """Query Seedance remote task result."""
        # Placeholder - would normally use model_resolver and video provider
        return {
            "taskId": remote_task_id,
            "status": "unknown",
            "videoUrl": None,
            "message": None,
            "payload": {},
        }

    # ------------------------------------------------------------------
    # Lifecycle commands
    # ------------------------------------------------------------------

    async def retry_task(self, task_id: str, user_id: int) -> dict[str, Any]:
        """Retry a failed task."""
        task = await self._query_service._require_owned_task(task_id, user_id)
        await self._command_service.retry(task)
        return await self._query_service.get_task(task.id, user_id)

    async def pause_task(self, task_id: str, user_id: int) -> dict[str, Any]:
        """Pause an active task."""
        task = await self._query_service._require_owned_task(task_id, user_id)
        await self._command_service.pause(task)
        return await self._query_service.get_task(task.id, user_id)

    async def continue_task(self, task_id: str, user_id: int) -> dict[str, Any]:
        """Continue a paused task."""
        task = await self._query_service._require_owned_task(task_id, user_id)
        await self._command_service.resume(task)
        return await self._query_service.get_task(task.id, user_id)

    async def terminate_task(self, task_id: str, user_id: int) -> dict[str, Any]:
        """Terminate a running task."""
        task = await self._query_service._require_owned_task(task_id, user_id)
        await self._command_service.terminate(task)
        return await self._query_service.get_task(task.id, user_id)

    async def admin_terminate_task(self, task_id: str) -> dict[str, Any]:
        """Admin-terminate a task (no owner check)."""
        task = await self._query_service._require_task(task_id)
        await self._command_service.terminate(task)
        return await self._query_service.admin_get_task(task.id)

    async def rate_task_effect(self, task_id: str, user_id: int, request: Any) -> dict[str, Any]:
        """Rate the effect of a completed task."""
        task = await self._query_service._require_owned_task(task_id, user_id)
        effect_rating = getattr(request, "effect_rating", None) if hasattr(request, "effect_rating") else getattr(request, "effectRating", None)
        effect_rating_note = getattr(request, "effect_rating_note", None) if hasattr(request, "effect_rating_note") else getattr(request, "effectRatingNote", None)
        await self._command_service.rate_effect(task, effect_rating=effect_rating, effect_rating_note=effect_rating_note)
        return await self._query_service.get_task(task.id, user_id)

    async def delete_task(self, task_id: str, user_id: int) -> dict[str, Any]:
        """Soft-delete a task."""
        task = await self._query_service._require_owned_task(task_id, user_id)
        return await self._command_service.delete_task(task)

    # ------------------------------------------------------------------
    # Admin queries
    # ------------------------------------------------------------------

    async def admin_overview(self) -> dict[str, Any]:
        return await self._query_service.admin_overview()

    async def admin_traces(
        self,
        task_id: str,
        stage: str | None = None,
        level: str | None = None,
        q: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return await self._query_service.admin_get_trace(task_id, stage, level, q, limit)

    async def admin_workers(self, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.admin_workers(limit)

    async def admin_worker(self, worker_instance_id: str) -> dict[str, Any]:
        return await self._query_service.admin_worker(worker_instance_id)

    async def admin_queue_events(self, task_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.admin_queue_events(task_id, limit)

    async def admin_queue_overview(self, limit: int = 50) -> dict[str, Any]:
        return await self._query_service.admin_queue_overview(limit)

    async def admin_task_diagnosis(self, task_id: str) -> dict[str, Any]:
        """Admin task diagnosis."""
        task = await self._query_service._require_task(task_id)
        from backend.services.task_diagnosis_service import TaskDiagnosisService
        diagnosis = TaskDiagnosisService()
        return diagnosis.diagnose(task)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_current_user_id() -> int:
        """Get current user ID from security context."""
        # Placeholder - replace with actual auth context resolution
        # Mirrors SecurityCurrentUser.requireCurrentUserId()
        from backend.services.auth_service import get_current_user_id
        user_id = get_current_user_id()
        if user_id is None:
            raise PermissionError("Authentication required")
        return user_id
