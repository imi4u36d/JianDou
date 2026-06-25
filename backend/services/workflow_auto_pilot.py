"""Auto-pilot engine for staged creative workflows.

Drives a workflow through its stages (storyboard -> keyframe -> video -> joined)
automatically.  Keyframe generation steps run sequentially (each clip's start
frame references the previous clip's tail frame for visual continuity) while
video generation steps execute concurrently (max 5 at a time).  Storyboard and
selection steps remain serial.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from backend.domain.enums import AutoPilotState, WorkflowStage, WorkflowStatus
from backend.domain.json_payloads import read_json_object
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown
from backend.shared import now_iso, safe_int, trim

if TYPE_CHECKING:
    from backend.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 200
TIMEOUT_SECONDS = 7200  # 2 hours
CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
MAX_CONCURRENT_STEPS = 5

# ---------------------------------------------------------------------------
# WorkflowAutoPilot
# ---------------------------------------------------------------------------


class WorkflowAutoPilot:
    """Drives a workflow through its stages automatically.

    After each step the engine re-reads the workflow from the database to
    check whether a pause request arrived.  Errors are caught, the
    auto_pilot_state is set to "failed", and the error message is recorded.
    """

    def __init__(self, db, workflow_service: WorkflowService) -> None:  # noqa: ANN001
        self._db = db
        self._workflow_service = workflow_service
        self._current_step: dict[str, Any] | None = None

    # -- Public API ---------------------------------------------------------

    async def run(self, workflow_id: str, owner_user_id: int) -> dict[str, Any]:
        """Main loop: execute stages until pause/fail/complete.

        Keyframe generation steps run sequentially (each clip's start frame
        references the previous clip's tail frame for visual continuity).
        Video generation steps are batched and executed concurrently (max 5
        at a time).  Other steps remain serial.

        Returns a result dict with keys *status*, *iterations*, and optionally
        *error*.
        """
        start_time = datetime.now(UTC)
        iteration = 0
        result: dict[str, Any] = {
            "status": "completed",
            "iterations": 0,
        }

        try:
            while iteration < MAX_ITERATIONS:
                iteration += 1

                # Timeout guard
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                if elapsed > TIMEOUT_SECONDS:
                    result["status"] = "timeout"
                    result["iterations"] = iteration
                    return result

                # Re-read workflow from DB to check for pause / failure requests
                wf = await self._get_workflow_from_db(workflow_id)
                if wf is None:
                    result["status"] = "not_found"
                    result["iterations"] = iteration
                    return result

                # Check pause
                if await self._check_pause(wf):
                    result["status"] = "paused"
                    result["iterations"] = iteration
                    return result

                # Check already failed
                if wf.auto_pilot_state == AutoPilotState.FAILED.value:
                    result["status"] = "failed"
                    result["iterations"] = iteration
                    result["error"] = wf.auto_pilot_error_message
                    return result

                # Check already completed
                if wf.auto_pilot_state == AutoPilotState.COMPLETED.value:
                    result["status"] = "completed"
                    result["iterations"] = iteration
                    return result

                versions = await self._workflow_service._list_stage_versions(workflow_id)
                steps = self._compute_next_steps(wf, versions)

                if not steps or steps[0]["type"] == "complete":
                    await self._set_state(wf, AutoPilotState.COMPLETED)
                    result["status"] = "completed"
                    result["iterations"] = iteration
                    return result

                self._current_step = steps[0]
                step_type = steps[0]["type"]

                # Videos run concurrently; keyframes run sequentially because
                # each clip's start frame references the previous clip's tail
                # frame for visual continuity.
                if step_type == "generate_video" and len(steps) > 1:
                    await self._execute_steps_concurrently(steps, workflow_id, owner_user_id)
                elif step_type == "generate_keyframe" and len(steps) > 1:
                    for idx, step in enumerate(steps):
                        self._current_step = step
                        clip_index = step.get("clip_index", 0)
                        clip_label = step.get("clip_index", "?")
                        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
                            stage_name = "三视图"
                            clip_label = f"角色 {clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE}"
                        else:
                            stage_name = "关键帧"
                            clip_label = f"镜头 {clip_label}"
                        await self._set_current_task(
                            workflow_id,
                            f"正在生成{stage_name} {idx + 1}/{len(steps)} ({clip_label})",
                        )
                        await self._execute_step(step, workflow_id, owner_user_id, skip_task_label=True)
                else:
                    # Serial execution for single steps or non-batchable types
                    for step in steps:
                        self._current_step = step
                        await self._execute_step(step, workflow_id, owner_user_id)

                # Small delay between iterations
                await asyncio.sleep(0.1)
                # Clear the current-task annotation after the iteration finishes
                await self._set_current_task(workflow_id, "")

            result["status"] = "max_iterations"
            result["iterations"] = iteration

        except Exception as exc:
            step_type = self._current_step.get("type", "?") if self._current_step else "?"
            clip_index = self._current_step.get("clip_index") if self._current_step else None
            extra = f" clip={clip_index}" if clip_index is not None else ""
            logger.exception(
                "Auto-pilot failed: workflow=%s step=%s%s error=%s",
                workflow_id, step_type, extra, exc,
            )
            wf = await self._get_workflow_from_db(workflow_id)
            if wf is not None:
                await self._set_current_task(workflow_id, "")
                await self._set_state(
                    wf,
                    AutoPilotState.FAILED,
                    error_message=f"Auto-pilot error: {exc}",
                )
            result["status"] = "error"
            result["iterations"] = iteration
            result["error"] = str(exc)

        return result

    # -- Step computation (pure function) -----------------------------------

    def _compute_next_steps(self, wf, versions) -> list[dict[str, Any]]:
        """Determine the next steps, batching independent work together.

        Returns a list of steps:
        - Single-element list for serial phases (storyboard, select, wait,
          select-video, finalize).
        - Multi-element list for concurrent phases (keyframes, videos).
        - ``[{"type": "complete"}]`` when everything is done.

        Algorithm:
        1. No storyboard versions -> generate_storyboard
        2. Has storyboard versions but none selected -> select_storyboard
        3. Missing character sheets (clip_index 1001, 1002, ...) -> ALL missing
        4. Missing keyframes (clip_index 1, 2, 3, ...) -> ALL missing
        5. Missing videos -> ALL missing
        6. Videos pending -> wait
        7. All videos ready, some not selected -> select_video
        8. All videos selected -> finalize
        9. Done -> complete
        """
        storyboard_versions = [v for v in versions if v.stage_type == WorkflowStage.STORYBOARD.value]
        keyframe_versions = [v for v in versions if v.stage_type == WorkflowStage.KEYFRAME.value]
        video_versions = [v for v in versions if v.stage_type == WorkflowStage.VIDEO.value]

        # 1. No storyboard versions -> generate
        if not storyboard_versions:
            return [{"type": "generate_storyboard"}]

        # 2. Has storyboard versions but none selected -> select first
        selected_storyboard_id = trim(wf.selected_storyboard_version_id)
        has_selected = (
            selected_storyboard_id
            and any(v.stage_version_id == selected_storyboard_id for v in storyboard_versions)
        )
        if not has_selected:
            first_version = min(
                storyboard_versions,
                key=lambda v: safe_int(v.version_no, 0),
            )
            return [{"type": "select_storyboard", "version_id": first_version.stage_version_id}]

        # Get the storyboard plan to know how many clips/characters we need
        selected_sb = next(
            (v for v in storyboard_versions if v.stage_version_id == selected_storyboard_id),
            None,
        )
        if selected_sb is None:
            selected_sb = next((v for v in storyboard_versions if v.selected == 1), None)
        if selected_sb is None:
            selected_sb = storyboard_versions[0]

        plan = self._get_storyboard_plan(selected_sb)
        characters, clips = plan
        storyboard_clip_indexes = [safe_int(c.get("clipIndex"), 0) for c in clips]

        # 3-4. Collect ALL missing keyframes (character sheets + regular clips)
        keyframe_steps: list[dict[str, Any]] = []

        for idx, _char in enumerate(characters, start=1):
            clip_index = CHARACTER_SHEET_CLIP_INDEX_BASE + idx
            char_keyframes = [
                v for v in keyframe_versions
                if v.clip_index == clip_index
            ]
            if not char_keyframes:
                keyframe_steps.append({"type": "generate_keyframe", "clip_index": clip_index})

        for clip_idx in sorted(storyboard_clip_indexes):
            if clip_idx == 0:
                continue
            kf_versions = [
                v for v in keyframe_versions
                if v.clip_index == clip_idx
                and trim(read_json_object(v.input_summary_json).get("variantKind", "")) != "character_sheet"
            ]
            if not kf_versions:
                keyframe_steps.append({"type": "generate_keyframe", "clip_index": clip_idx})
                continue
            # Check that at least one keyframe is selected
            if not any(v.selected == 1 for v in kf_versions):
                keyframe_steps.append({"type": "generate_keyframe", "clip_index": clip_idx})

        if keyframe_steps:
            return keyframe_steps

        # 5. Collect ALL pending videos
        video_steps: list[dict[str, Any]] = []
        pending_clip_indexes: list[int] = []

        for clip_idx in sorted(storyboard_clip_indexes):
            if clip_idx == 0:
                continue
            vid_versions = [
                v for v in video_versions
                if v.clip_index == clip_idx
            ]
            if not vid_versions:
                video_steps.append({"type": "generate_video", "clip_index": clip_idx})
                continue
            # Check if any video has a material_asset_id + preview_url (complete)
            has_complete_video = any(
                trim(v.material_asset_id) and trim(v.preview_url)
                for v in vid_versions
            )
            if has_complete_video:
                continue
            # Check if any video is still being generated (async / running)
            _PENDING_STATUSES = {"RUNNING", "SUBMITTED", "PENDING", "PROCESSING", ""}
            if any(
                trim(v.status).upper() in _PENDING_STATUSES
                for v in vid_versions
            ):
                pending_clip_indexes.append(clip_idx)
                continue
            # Neither complete nor pending (e.g. all FAILED) -> re-generate
            video_steps.append({"type": "generate_video", "clip_index": clip_idx})

        if pending_clip_indexes and not video_steps:
            return [{"type": "wait", "pending_clip_indexes": pending_clip_indexes}]

        if video_steps:
            return video_steps

        # 6. All videos ready -> auto-select, finalize, or complete
        selected_videos = [
            v for v in video_versions
            if v.selected == 1 and trim(v.preview_url)
        ]
        if not selected_videos:
            # Auto-select first completed video per clip
            for clip_idx in sorted(storyboard_clip_indexes):
                if clip_idx == 0:
                    continue
                vid_versions_for_clip = [
                    v for v in video_versions if v.clip_index == clip_idx
                ]
                if vid_versions_for_clip:
                    first_vid = min(
                        vid_versions_for_clip,
                        key=lambda v: safe_int(v.version_no, 0),
                    )
                    return [{
                        "type": "select_video",
                        "clip_index": clip_idx,
                        "version_id": first_vid.stage_version_id,
                    }]
            return [{"type": "finalize"}]

        # All expected clips have a selected video — now join them
        expected_clip_count = len([i for i in storyboard_clip_indexes if i != 0])
        if len(selected_videos) >= expected_clip_count:
            if not trim(wf.final_join_asset_id):
                return [{"type": "finalize"}]
            return [{"type": "complete"}]

        # 7. Still missing some clip selections (shouldn't normally reach here)
        return [{"type": "complete"}]

    # -- Step execution -----------------------------------------------------

    async def _execute_step(
        self,
        step: dict[str, Any],
        workflow_id: str,
        owner_user_id: int,
        *,
        skip_task_label: bool = False,
    ) -> None:
        """Execute one step by calling existing WorkflowService methods.

        Used for serial steps (storyboard, select, wait, finalize) and
        single-instance concurrent-type steps.

        When *skip_task_label* is True the method does not overwrite the
        current-task annotation — the caller is responsible for setting a
        more detailed label (e.g. "正在生成关键帧 1/3 (镜头 1)").
        """
        step_type = step.get("type")
        wf = await self._get_workflow_from_db(workflow_id)

        # Map step type to stage name and model for logging
        _STAGE_MODEL_MAP: dict[str, tuple[str, str]] = {
            "generate_storyboard": ("分镜脚本", wf.text_analysis_model if wf else "?"),
            "select_storyboard":   ("选择分镜", wf.text_analysis_model if wf else "?"),
            "generate_keyframe":   ("关键帧",     wf.image_model if wf else "?"),
            "generate_video":      ("视频生成",   wf.video_model if wf else "?"),
            "select_video":        ("选择视频",   wf.video_model if wf else "?"),
            "finalize":            ("成片拼接",   "—"),
        }

        stage_label, model_label = _STAGE_MODEL_MAP.get(step_type, (step_type, "?"))
        # Distinguish character sheets (三视图) from regular clip keyframes
        if step_type == "generate_keyframe" and step.get("clip_index", 0) >= CHARACTER_SHEET_CLIP_INDEX_BASE:
            stage_label = "三视图"

        # Update the current-task annotation so the frontend can show "正在生成XXX"
        if not skip_task_label:
            clip_index = step.get("clip_index")
            if clip_index is not None and step_type in ("generate_keyframe", "generate_video", "select_video"):
                if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
                    char_num = clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE
                    task_label = f"正在{stage_label} (角色 {char_num})"
                else:
                    task_label = f"正在{stage_label} (镜头 {clip_index})"
            else:
                task_label = f"正在{stage_label}" if stage_label else step_type
            await self._set_current_task(workflow_id, task_label)

        if step_type == "generate_storyboard":
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s model=%s",
                workflow_id, stage_label, model_label,
            )
            await self._workflow_service.generate_storyboard(
                workflow_id, owner_user_id=owner_user_id,
            )

        elif step_type == "select_storyboard":
            version_id = step.get("version_id", "")
            if version_id:
                logger.info(
                    "Auto-pilot step: workflow=%s stage=%s version=%s",
                    workflow_id, stage_label, version_id,
                )
                await self._workflow_service.select_storyboard(
                    workflow_id, version_id, owner_user_id=owner_user_id,
                )

        elif step_type == "generate_keyframe":
            clip_index = step.get("clip_index", 1)
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s model=%s clip=%s",
                workflow_id, stage_label, model_label, clip_index,
            )
            await self._workflow_service.generate_keyframe(
                workflow_id, clip_index, owner_user_id=owner_user_id,
            )

        elif step_type == "generate_video":
            clip_index = step.get("clip_index", 1)
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s model=%s clip=%s",
                workflow_id, stage_label, model_label, clip_index,
            )
            await self._workflow_service.generate_video(
                workflow_id, clip_index, owner_user_id=owner_user_id,
            )

        elif step_type == "select_video":
            clip_index = step.get("clip_index", 1)
            version_id = step.get("version_id", "")
            if version_id:
                logger.info(
                    "Auto-pilot step: workflow=%s stage=%s version=%s",
                    workflow_id, stage_label, version_id,
                )
                await self._workflow_service.select_video(
                    workflow_id, clip_index, version_id, owner_user_id=owner_user_id,
                )

        elif step_type == "finalize":
            logger.info(
                "Auto-pilot step: workflow=%s stage=%s",
                workflow_id, stage_label,
            )
            await self._workflow_service.finalize_workflow(
                workflow_id, owner_user_id=owner_user_id,
            )

        elif step_type == "wait":
            pending_clips = step.get("pending_clip_indexes", [])
            clips_str = ", ".join(str(c) for c in pending_clips) if pending_clips else "?"
            if not skip_task_label:
                await self._set_current_task(workflow_id, f"镜头 {clips_str} 视频生成中，等待完成…")
            logger.info(
                "Auto-pilot step: workflow=%s stage=等待视频完成 clips=%s",
                workflow_id, clips_str,
            )
            wf_for_refresh = await self._get_workflow_from_db(workflow_id)
            if wf_for_refresh is not None:
                try:
                    versions_for_refresh = await self._workflow_service._list_stage_versions(workflow_id)
                    await self._workflow_service._refresh_video_versions(wf_for_refresh, versions_for_refresh)
                except Exception:
                    logger.exception(
                        "Auto-pilot: refresh video versions failed workflow=%s",
                        workflow_id,
                    )
            # Wait before next poll to avoid tight loops while async videos run
            await asyncio.sleep(5)

        # Small delay between steps to avoid tight DB loops
        await asyncio.sleep(0.1)

        # Clear the current-task annotation after the step finishes
        await self._set_current_task(workflow_id, "")

    # -- Concurrent step execution ------------------------------------------

    async def _execute_steps_concurrently(
        self,
        steps: list[dict[str, Any]],
        workflow_id: str,
        owner_user_id: int,
    ) -> None:
        """Execute multiple steps concurrently, limited to MAX_CONCURRENT_STEPS.

        Each step runs in its own DB session to avoid shared-session conflicts.
        On the first exception, remaining tasks are cancelled.
        """
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_STEPS)
        step_type = steps[0]["type"]
        count = len(steps)

        # Set batch-level task label with clip indexes
        clip_indexes = [s.get("clip_index", "?") for s in steps]
        clips_str = ", ".join(str(c) for c in clip_indexes)
        if step_type == "generate_keyframe":
            await self._set_current_task(workflow_id, f"正在并行生成关键帧 (镜头 {clips_str})")
        else:
            await self._set_current_task(workflow_id, f"正在并行生成视频 (镜头 {clips_str})")

        logger.info(
            "Auto-pilot batch start: workflow=%s type=%s count=%d",
            workflow_id, step_type, count,
        )

        async def run_one(step: dict[str, Any]) -> None:
            async with semaphore:
                await self._execute_step_isolated(step, workflow_id, owner_user_id)

        tasks = [asyncio.create_task(run_one(s)) for s in steps]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        # Cancel remaining tasks if any failed
        for task in pending:
            task.cancel()

        # Re-raise the first exception if any
        for task in done:
            exc = task.exception()
            if exc is not None:
                logger.error(
                    "Auto-pilot batch step failed: workflow=%s type=%s error=%s",
                    workflow_id, step_type, exc,
                )
                raise exc

        logger.info(
            "Auto-pilot batch complete: workflow=%s type=%s count=%d",
            workflow_id, step_type, count,
        )

    async def _execute_step_isolated(
        self,
        step: dict[str, Any],
        workflow_id: str,
        owner_user_id: int,
    ) -> None:
        """Execute a single step with an isolated DB session.

        Creates a fresh WorkflowService instance with its own AsyncSession so
        that concurrent steps do not interfere with each other's transactions.
        """
        from backend.database import async_session_factory
        from backend.services.workflow_service import WorkflowService

        async with async_session_factory() as session:
            svc = WorkflowService(
                db=session,
                generation_service=self._workflow_service._generation_service,
            )
            step_type = step.get("type")
            clip_index = step.get("clip_index", 1)

            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    if step_type == "generate_keyframe":
                        logger.info(
                            "Auto-pilot concurrent: workflow=%s stage=关键帧 clip=%s attempt=%d/%d",
                            workflow_id, clip_index, attempt, max_attempts,
                        )
                        await svc.generate_keyframe(
                            workflow_id, clip_index, owner_user_id=owner_user_id,
                        )
                    elif step_type == "generate_video":
                        logger.info(
                            "Auto-pilot concurrent: workflow=%s stage=视频生成 clip=%s attempt=%d/%d",
                            workflow_id, clip_index, attempt, max_attempts,
                        )
                        await svc.generate_video(
                            workflow_id, clip_index, owner_user_id=owner_user_id,
                        )
                    return
                except Exception as exc:  # noqa: BLE001
                    if not self._is_retryable_provider_error(exc) or attempt == max_attempts:
                        raise
                    delay = min(2 ** attempt, 5)
                    logger.warning(
                        "Auto-pilot retryable provider error: workflow=%s clip=%s attempt=%d/%d delay=%ds error=%s",
                        workflow_id, clip_index, attempt, max_attempts, delay, exc,
                    )
                    await asyncio.sleep(delay)

    @staticmethod
    def _is_retryable_provider_error(exc: Exception) -> bool:
        from backend.services.generation_service import GenerationProviderException

        if not isinstance(exc, GenerationProviderException):
            return False
        message = str(exc).lower()
        return "readtimeout" in message or "connectionreset" in message

    # -- Pause / state helpers ----------------------------------------------

    async def _check_pause(self, wf) -> bool:
        """Re-read workflow from DB, check if pause was requested."""
        fresh = await self._get_workflow_from_db(wf.workflow_id)
        if fresh is None:
            return False
        return fresh.auto_pilot_state == AutoPilotState.PAUSED.value

    async def _get_workflow_from_db(self, workflow_id: str):
        """Re-read workflow from DB to check for state changes."""
        from sqlalchemy import select
        from backend.models.workflow import BizStageWorkflow

        stmt = select(BizStageWorkflow).where(
            BizStageWorkflow.workflow_id == workflow_id,
            BizStageWorkflow.is_deleted == 0,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _set_state(
        self,
        wf,  # noqa: ANN001
        state: AutoPilotState,
        error_message: str = "",
    ) -> None:
        """Update the workflow's auto_pilot fields in the database.

        When entering a terminal auto-pilot state (FAILED / COMPLETED), the
        workflow-level ``status`` column is synced so that the frontend list
        filter can correctly surface failed or completed workflows.
        """
        from sqlalchemy import update

        from backend.models.workflow import BizStageWorkflow

        now = now_iso()
        values: dict[str, Any] = {
            "auto_pilot_state": state.value,
            "auto_pilot_current_task": "",  # clear on every state transition
            "update_time": now,
        }

        if error_message:
            values["auto_pilot_error_message"] = error_message
        if state == AutoPilotState.RUNNING and not wf.auto_pilot_started_at:
            values["auto_pilot_started_at"] = now
        if state == AutoPilotState.PAUSED:
            values["auto_pilot_paused_at"] = now

        # Sync workflow-level status for terminal auto-pilot states
        if state == AutoPilotState.FAILED:
            values["status"] = WorkflowStatus.FAILED.value
        elif state == AutoPilotState.COMPLETED:
            values["status"] = WorkflowStatus.COMPLETED.value

        stmt = (
            update(BizStageWorkflow)
            .where(BizStageWorkflow.workflow_id == wf.workflow_id)
            .values(**values)
        )

        await self._db.execute(stmt)
        await self._db.commit()

    async def _set_current_task(self, workflow_id: str, task: str) -> None:
        """Update the auto_pilot_current_task column so the frontend can show a note."""
        from sqlalchemy import update

        from backend.models.workflow import BizStageWorkflow

        stmt = (
            update(BizStageWorkflow)
            .where(BizStageWorkflow.workflow_id == workflow_id)
            .values(auto_pilot_current_task=task, update_time=now_iso())
        )
        await self._db.execute(stmt)
        await self._db.commit()

    async def _auto_select_first_version(
        self,
        wf,  # noqa: ANN001
        stage_type: str,
        clip_index: int,
    ) -> bool:
        """Auto-select first completed version for a stage."""
        from sqlalchemy import select
        from backend.models.workflow import BizStageVersion

        stmt = select(BizStageVersion).where(
            BizStageVersion.workflow_id == wf.workflow_id,
            BizStageVersion.stage_type == stage_type,
            BizStageVersion.clip_index == clip_index,
            BizStageVersion.is_deleted == 0,
        ).order_by(BizStageVersion.version_no)

        result = await self._db.execute(stmt)
        versions = result.scalars().all()

        if versions:
            first_version = versions[0]
            await self._workflow_service._mark_selected_stage_version(
                wf.workflow_id,
                stage_type,
                clip_index,
                first_version.stage_version_id,
            )
            return True
        return False

    def _get_storyboard_plan(self, version) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract characters and clips from a storyboard version's plan.

        Uses the same markdown table parser as WorkflowService so that the
        auto-pilot and the manual flow agree on what clips exist.
        """
        output = read_json_object(version.output_summary_json)
        script = trim(output.get("scriptMarkdown") or output.get("previewText"))
        if not script:
            return [], []
        return parse_workflow_storyboard_markdown(script).to_view()
