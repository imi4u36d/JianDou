"""Auto-pilot engine for staged creative workflows.

Drives a workflow through its stages (storyboard -> keyframe -> video -> joined)
automatically, executing one step at a time until pause, failure, or completion.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from backend.domain.enums import AutoPilotState, WorkflowStage
from backend.domain.json_payloads import read_json_object
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

    # -- Public API ---------------------------------------------------------

    async def run(self, workflow_id: str, owner_user_id: int) -> dict[str, Any]:
        """Main loop: execute stages sequentially until pause/fail/complete.

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
                step = self._compute_next_step(wf, versions)

                if step["type"] == "complete":
                    await self._set_state(wf, AutoPilotState.COMPLETED)
                    result["status"] = "completed"
                    result["iterations"] = iteration
                    return result

                await self._execute_step(step, workflow_id, owner_user_id)

            result["status"] = "max_iterations"
            result["iterations"] = iteration

        except Exception as exc:
            logger.exception("Auto-pilot encountered an unexpected error")
            wf = await self._get_workflow_from_db(workflow_id)
            if wf is not None:
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

    def _compute_next_step(self, wf, versions) -> dict[str, Any]:
        """Determine the next step based on current version states.

        Algorithm:
        1. No storyboard versions -> generate_storyboard
        2. Has storyboard versions but none selected -> select_storyboard
        3. Missing character sheets (clip_index 1001, 1002, ...) -> generate_keyframe
        4. Missing keyframes (clip_index 1, 2, 3, ...) -> generate_keyframe
        5. Missing videos -> generate_video
        6. All videos ready -> finalize
        7. Done -> complete
        """
        storyboard_versions = [v for v in versions if v.stage_type == WorkflowStage.STORYBOARD.value]
        keyframe_versions = [v for v in versions if v.stage_type == WorkflowStage.KEYFRAME.value]
        video_versions = [v for v in versions if v.stage_type == WorkflowStage.VIDEO.value]

        # 1. No storyboard versions -> generate
        if not storyboard_versions:
            return {"type": "generate_storyboard"}

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
            return {"type": "select_storyboard", "version_id": first_version.stage_version_id}

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
        _, clips = plan
        characters, _ = plan

        # 3. Check character sheets (clip_index 1001, 1002, ...)
        for idx, _char in enumerate(characters, start=1):
            clip_index = CHARACTER_SHEET_CLIP_INDEX_BASE + idx
            char_keyframes = [
                v for v in keyframe_versions
                if v.clip_index == clip_index
            ]
            if not char_keyframes:
                return {"type": "generate_keyframe", "clip_index": clip_index}

        # 4. Check keyframes for each clip
        storyboard_clip_indexes = [safe_int(c.get("clipIndex"), 0) for c in clips]
        for clip_idx in sorted(storyboard_clip_indexes):
            if clip_idx == 0:
                continue
            kf_versions = [
                v for v in keyframe_versions
                if v.clip_index == clip_idx
                and trim(read_json_object(v.input_summary_json).get("variantKind", "")) != "character_sheet"
            ]
            if not kf_versions:
                return {"type": "generate_keyframe", "clip_index": clip_idx}
            # Check that at least one keyframe is selected
            if not any(v.selected == 1 for v in kf_versions):
                return {"type": "generate_keyframe", "clip_index": clip_idx}

        # 5. Check videos for each clip
        for clip_idx in sorted(storyboard_clip_indexes):
            if clip_idx == 0:
                continue
            vid_versions = [
                v for v in video_versions
                if v.clip_index == clip_idx
            ]
            # Check if any video has a material_asset_id (meaning it's complete)
            has_complete_video = any(
                trim(v.material_asset_id) and trim(v.preview_url)
                for v in vid_versions
            )
            if not has_complete_video:
                return {"type": "generate_video", "clip_index": clip_idx}

        # 6. All videos ready -> finalize
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
                    return {
                        "type": "select_video",
                        "clip_index": clip_idx,
                        "version_id": first_vid.stage_version_id,
                    }
            return {"type": "finalize"}

        # 7. Done
        return {"type": "complete"}

    # -- Step execution -----------------------------------------------------

    async def _execute_step(
        self,
        step: dict[str, Any],
        workflow_id: str,
        owner_user_id: int,
    ) -> None:
        """Execute one step by calling existing WorkflowService methods."""
        step_type = step.get("type")

        if step_type == "generate_storyboard":
            await self._workflow_service.generate_storyboard(
                workflow_id, owner_user_id=owner_user_id,
            )

        elif step_type == "select_storyboard":
            version_id = step.get("version_id", "")
            if version_id:
                await self._workflow_service.select_storyboard(
                    workflow_id, version_id, owner_user_id=owner_user_id,
                )

        elif step_type == "generate_keyframe":
            clip_index = step.get("clip_index", 1)
            await self._workflow_service.generate_keyframe(
                workflow_id, clip_index, owner_user_id=owner_user_id,
            )

        elif step_type == "generate_video":
            clip_index = step.get("clip_index", 1)
            await self._workflow_service.generate_video(
                workflow_id, clip_index, owner_user_id=owner_user_id,
            )

        elif step_type == "select_video":
            clip_index = step.get("clip_index", 1)
            version_id = step.get("version_id", "")
            if version_id:
                await self._workflow_service.select_video(
                    workflow_id, clip_index, version_id, owner_user_id=owner_user_id,
                )

        elif step_type == "finalize":
            await self._workflow_service.finalize_workflow(
                workflow_id, owner_user_id=owner_user_id,
            )

        # Small delay between steps to avoid tight DB loops
        await asyncio.sleep(0.1)

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
        """Update the workflow's auto_pilot fields in the database."""
        from sqlalchemy import update

        from backend.models.workflow import BizStageWorkflow

        now = now_iso()
        stmt = (
            update(BizStageWorkflow)
            .where(BizStageWorkflow.workflow_id == wf.workflow_id)
            .values(
                auto_pilot_state=state.value,
                update_time=now,
            )
        )
        if error_message:
            stmt = stmt.values(auto_pilot_error_message=error_message)
        if state == AutoPilotState.RUNNING and not wf.auto_pilot_started_at:
            stmt = stmt.values(auto_pilot_started_at=now)
        if state == AutoPilotState.PAUSED:
            stmt = stmt.values(auto_pilot_paused_at=now)

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
        """Extract characters and clips from a storyboard version's plan."""
        output = read_json_object(version.output_summary_json)
        script = trim(output.get("scriptMarkdown") or output.get("previewText"))
        if not script:
            return [], []

        # Simple markdown parser for the storyboard plan format
        characters: list[dict[str, Any]] = []
        clips: list[dict[str, Any]] = []

        lines = script.strip().split("\n")
        current_char: dict[str, Any] | None = None
        current_clip: dict[str, Any] | None = None
        clip_index = 0

        for line in lines:
            stripped = line.strip()
            # Character section
            if stripped.startswith(("##", "---")):
                if current_clip is not None:
                    clips.append(current_clip)
                    current_clip = None
                if current_char is not None:
                    characters.append(current_char)
                    current_char = None
            elif stripped and not stripped.startswith("#"):
                # This is likely a character name or clip description
                if current_char is None and not stripped.startswith("-"):
                    current_char = {"name": stripped, "appearance": ""}
                elif current_char is not None and "appearance" not in str(current_char):
                    current_char["appearance"] = stripped
                elif current_clip is None:
                    clip_index += 1
                    current_clip = {
                        "clipIndex": clip_index,
                        "shotLabel": stripped,
                        "scene": "",
                        "targetDurationSeconds": 8,
                    }
                elif current_clip is not None:
                    current_clip["scene"] = stripped

        if current_char is not None:
            characters.append(current_char)
        if current_clip is not None:
            clips.append(current_clip)

        return characters, clips
