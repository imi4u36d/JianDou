"""Serial and concurrent step execution for workflow auto-pilot."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from backend.services.workflow_auto_pilot_planner import CHARACTER_SHEET_CLIP_INDEX_BASE

if TYPE_CHECKING:
    from backend.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

MAX_CONCURRENT_STEPS = 5


class WorkflowAutoPilotStepExecutor:
    """Execute planned steps while isolating concurrent database sessions."""

    def __init__(
        self,
        workflow_service: WorkflowService,
        get_workflow: Callable[[str], Awaitable[Any]],
        set_current_task: Callable[[str, str], Awaitable[None]],
    ) -> None:
        self._workflow_service = workflow_service
        self._get_workflow = get_workflow
        self._set_current_task = set_current_task

    async def execute_step(
        self,
        step: dict[str, Any],
        workflow_id: str,
        owner_user_id: int,
        *,
        skip_task_label: bool = False,
    ) -> None:
        step_type = step.get("type")
        workflow = await self._get_workflow(workflow_id)
        stage_label, model_label = self._stage_and_model(step, workflow)
        if not skip_task_label:
            await self._set_current_task(
                workflow_id,
                self._task_label(step, stage_label),
            )

        if step_type == "generate_storyboard":
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s model=%s",
                workflow_id,
                stage_label,
                model_label,
            )
            await self._workflow_service.generate_storyboard(workflow_id, owner_user_id=owner_user_id)
        elif step_type == "select_storyboard":
            version_id = step.get("version_id", "")
            if version_id:
                logger.info(
                    "Auto-pilot step: workflow=%s stage=%s version=%s",
                    workflow_id,
                    stage_label,
                    version_id,
                )
                await self._workflow_service.select_storyboard(
                    workflow_id, version_id, owner_user_id=owner_user_id
                )
        elif step_type == "generate_keyframe":
            clip_index = step.get("clip_index", 1)
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s model=%s clip=%s",
                workflow_id,
                stage_label,
                model_label,
                clip_index,
            )
            if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
                await self._workflow_service.generate_character_sheet(
                    workflow_id,
                    clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE,
                    owner_user_id=owner_user_id,
                )
            else:
                await self._workflow_service.generate_keyframe(
                    workflow_id, clip_index, owner_user_id=owner_user_id
                )
        elif step_type == "generate_video":
            clip_index = step.get("clip_index", 1)
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s model=%s clip=%s",
                workflow_id,
                stage_label,
                model_label,
                clip_index,
            )
            await self._workflow_service.generate_video(
                workflow_id, clip_index, owner_user_id=owner_user_id
            )
        elif step_type == "select_video":
            clip_index = step.get("clip_index", 1)
            version_id = step.get("version_id", "")
            if version_id:
                logger.info(
                    "Auto-pilot step: workflow=%s stage=%s version=%s",
                    workflow_id,
                    stage_label,
                    version_id,
                )
                await self._workflow_service.select_video(
                    workflow_id, clip_index, version_id, owner_user_id=owner_user_id
                )
        elif step_type == "finalize":
            logger.info("Auto-pilot step: workflow=%s stage=%s", workflow_id, stage_label)
            await self._workflow_service.finalize_workflow(workflow_id, owner_user_id=owner_user_id)
        elif step_type == "wait":
            await self._wait_for_video_versions(step, workflow_id, skip_task_label)

        await asyncio.sleep(0.1)
        await self._set_current_task(workflow_id, "")

    def _stage_and_model(self, step: dict[str, Any], workflow: Any) -> tuple[str, str]:
        step_type = step.get("type")
        stage_model_map: dict[str, tuple[str, str]] = {
            "generate_storyboard": ("分镜脚本", workflow.text_analysis_model if workflow else "?"),
            "select_storyboard": ("选择分镜", workflow.text_analysis_model if workflow else "?"),
            "generate_keyframe": ("关键帧", workflow.image_model if workflow else "?"),
            "generate_video": ("视频生成", workflow.video_model if workflow else "?"),
            "select_video": ("选择视频", workflow.video_model if workflow else "?"),
            "finalize": ("成片拼接", "—"),
        }
        stage_label, model_label = stage_model_map.get(step_type, (step_type, "?"))
        if (
            step_type == "generate_keyframe"
            and step.get("clip_index", 0) >= CHARACTER_SHEET_CLIP_INDEX_BASE
        ):
            stage_label = "三视图"
        return stage_label, model_label

    @staticmethod
    def _task_label(step: dict[str, Any], stage_label: str) -> str:
        step_type = step.get("type")
        clip_index = step.get("clip_index")
        if clip_index is not None and step_type in {
            "generate_keyframe",
            "generate_video",
            "select_video",
        }:
            if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
                return f"正在{stage_label} (角色 {clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE})"
            return f"正在{stage_label} (镜头 {clip_index})"
        return f"正在{stage_label}" if stage_label else step_type

    async def _wait_for_video_versions(
        self, step: dict[str, Any], workflow_id: str, skip_task_label: bool
    ) -> None:
        pending_clips = step.get("pending_clip_indexes", [])
        clips_str = ", ".join(str(clip) for clip in pending_clips) if pending_clips else "?"
        if not skip_task_label:
            await self._set_current_task(workflow_id, f"镜头 {clips_str} 视频生成中，等待完成…")
        logger.info(
            "Auto-pilot step: workflow=%s stage=等待视频完成 clips=%s",
            workflow_id,
            clips_str,
        )
        workflow = await self._get_workflow(workflow_id)
        if workflow is not None:
            try:
                versions = await self._workflow_service._list_stage_versions(workflow_id)
                await self._workflow_service._refresh_video_versions(workflow, versions)
            except Exception:
                logger.exception(
                    "Auto-pilot: refresh video versions failed workflow=%s", workflow_id
                )
        await asyncio.sleep(5)

    async def execute_steps_concurrently(
        self,
        steps: list[dict[str, Any]],
        workflow_id: str,
        owner_user_id: int,
    ) -> None:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_STEPS)
        step_type = steps[0]["type"]
        clips_str = ", ".join(str(step.get("clip_index", "?")) for step in steps)
        label = (
            f"正在并行生成关键帧 (镜头 {clips_str})"
            if step_type == "generate_keyframe"
            else f"正在并行生成视频 (镜头 {clips_str})"
        )
        await self._set_current_task(workflow_id, label)
        logger.info(
            "Auto-pilot batch start: workflow=%s type=%s count=%d",
            workflow_id,
            step_type,
            len(steps),
        )

        async def run_one(step: dict[str, Any]) -> None:
            async with semaphore:
                await self._execute_step_isolated(step, workflow_id, owner_user_id)

        tasks = [asyncio.create_task(run_one(step)) for step in steps]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            exception = task.exception()
            if exception is not None:
                logger.error(
                    "Auto-pilot batch step failed: workflow=%s type=%s error=%s",
                    workflow_id,
                    step_type,
                    exception,
                )
                raise exception
        logger.info(
            "Auto-pilot batch complete: workflow=%s type=%s count=%d",
            workflow_id,
            step_type,
            len(steps),
        )

    async def _execute_step_isolated(
        self, step: dict[str, Any], workflow_id: str, owner_user_id: int
    ) -> None:
        from backend.database import async_session_factory
        from backend.services.workflow_service import WorkflowService

        async with async_session_factory() as session:
            service = WorkflowService(
                db=session,
                generation_service=self._workflow_service._generation_service,
            )
            step_type = step.get("type")
            clip_index = step.get("clip_index", 1)
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    await self._execute_isolated_generation(
                        service,
                        step_type,
                        workflow_id,
                        clip_index,
                        owner_user_id,
                        attempt,
                        max_attempts,
                    )
                    return
                except Exception as exc:  # noqa: BLE001
                    if not self.is_retryable_provider_error(exc) or attempt == max_attempts:
                        raise
                    delay = min(2**attempt, 5)
                    logger.warning(
                        "Auto-pilot retryable provider error: workflow=%s clip=%s attempt=%d/%d delay=%ds error=%s",
                        workflow_id,
                        clip_index,
                        attempt,
                        max_attempts,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)

    @staticmethod
    async def _execute_isolated_generation(
        service: WorkflowService,
        step_type: str,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int,
        attempt: int,
        max_attempts: int,
    ) -> None:
        if step_type == "generate_keyframe":
            logger.info(
                "Auto-pilot concurrent: workflow=%s stage=关键帧 clip=%s attempt=%d/%d",
                workflow_id,
                clip_index,
                attempt,
                max_attempts,
            )
            if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
                await service.generate_character_sheet(
                    workflow_id,
                    clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE,
                    owner_user_id=owner_user_id,
                )
            else:
                await service.generate_keyframe(
                    workflow_id, clip_index, owner_user_id=owner_user_id
                )
        elif step_type == "generate_video":
            logger.info(
                "Auto-pilot concurrent: workflow=%s stage=视频生成 clip=%s attempt=%d/%d",
                workflow_id,
                clip_index,
                attempt,
                max_attempts,
            )
            await service.generate_video(workflow_id, clip_index, owner_user_id=owner_user_id)

    @staticmethod
    def is_retryable_provider_error(exc: Exception) -> bool:
        from backend.services.generation_service import GenerationProviderException

        if not isinstance(exc, GenerationProviderException):
            return False
        message = str(exc).lower()
        return "readtimeout" in message or "connectionreset" in message
