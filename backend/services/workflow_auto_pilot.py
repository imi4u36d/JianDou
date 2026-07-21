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

from backend.domain.enums import AutoPilotState, WorkflowStatus
from backend.domain.json_payloads import read_json_object
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown
from backend.services.workflow_auto_pilot_executor import WorkflowAutoPilotStepExecutor
from backend.services.workflow_auto_pilot_planner import (
    CHARACTER_SHEET_CLIP_INDEX_BASE,
    WorkflowAutoPilotPlanner,
)
from backend.shared import now_iso, trim

if TYPE_CHECKING:
    from backend.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 200
TIMEOUT_SECONDS = 7200  # 2 hours

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
        self._planner = WorkflowAutoPilotPlanner()
        self._step_executor = WorkflowAutoPilotStepExecutor(
            workflow_service,
            self._get_workflow_from_db,
            self._set_current_task,
        )
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
                    await self._step_executor.execute_steps_concurrently(
                        steps, workflow_id, owner_user_id
                    )
                elif step_type == "generate_keyframe" and len(steps) > 1:
                    for idx, step in enumerate(steps):
                        self._current_step = step
                        clip_index = step.get("clip_index", 0)
                        clip_label = step.get("clip_index", "?")
                        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
                            stage_name = "公共素材"
                            clip_label = f"素材 {clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE}"
                        else:
                            stage_name = "关键帧"
                            clip_label = f"镜头 {clip_label}"
                        await self._set_current_task(
                            workflow_id,
                            f"正在生成{stage_name} {idx + 1}/{len(steps)} ({clip_label})",
                        )
                        await self._step_executor.execute_step(
                            step,
                            workflow_id,
                            owner_user_id,
                            skip_task_label=True,
                        )
                else:
                    # Serial execution for single steps or non-batchable types
                    for step in steps:
                        self._current_step = step
                        await self._step_executor.execute_step(step, workflow_id, owner_user_id)

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
                workflow_id,
                step_type,
                extra,
                exc,
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

    def _compute_next_steps(self, wf, versions) -> list[dict[str, Any]]:
        """Compatibility seam around the pure next-step planner."""
        return self._planner.compute_next_steps(wf, versions, self._get_storyboard_plan)

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

        stmt = update(BizStageWorkflow).where(BizStageWorkflow.workflow_id == wf.workflow_id).values(**values)

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

        stmt = (
            select(BizStageVersion)
            .where(
                BizStageVersion.workflow_id == wf.workflow_id,
                BizStageVersion.stage_type == stage_type,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
            .order_by(BizStageVersion.version_no)
        )

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
