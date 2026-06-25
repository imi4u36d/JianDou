"""Tests for new enums and model fields added for auto-pilot."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.domain

from backend.domain.enums import AutoPilotState, ExecutionMode, WorkflowStatus


class TestExecutionMode:
    def test_auto_value(self):
        assert ExecutionMode.AUTO.value == "auto"
        assert ExecutionMode.AUTO == "auto"

    def test_manual_value(self):
        assert ExecutionMode.MANUAL.value == "manual"
        assert ExecutionMode.MANUAL == "manual"

    def test_members(self):
        assert list(ExecutionMode) == [ExecutionMode.AUTO, ExecutionMode.MANUAL]


class TestAutoPilotState:
    def test_idle(self):
        assert AutoPilotState.IDLE.value == "idle"

    def test_running(self):
        assert AutoPilotState.RUNNING.value == "running"

    def test_paused(self):
        assert AutoPilotState.PAUSED.value == "paused"

    def test_failed(self):
        assert AutoPilotState.FAILED.value == "failed"

    def test_completed(self):
        assert AutoPilotState.COMPLETED.value == "completed"

    def test_all_states(self):
        states = [e.value for e in AutoPilotState]
        assert states == ["idle", "queued", "running", "paused", "failed", "completed"]

    def test_missing_fallback(self):
        """StrEnum._missing_ should map unknown strings to IDLE."""
        unknown = AutoPilotState("unknown")
        assert unknown == AutoPilotState.IDLE


class TestWorkflowStatus:
    def test_new_states_exist(self):
        assert hasattr(WorkflowStatus, "RUNNING")
        assert hasattr(WorkflowStatus, "PAUSED")

    def test_running_value(self):
        assert WorkflowStatus.RUNNING.value == "RUNNING"

    def test_paused_value(self):
        assert WorkflowStatus.PAUSED.value == "PAUSED"

    def test_all_states(self):
        states = [e.value for e in WorkflowStatus]
        assert "DRAFT" in states
        assert "READY" in states
        assert "RUNNING" in states
        assert "PAUSED" in states
        assert "COMPLETED" in states
        assert "FAILED" in states


# ---------------------------------------------------------------------------
# Model field tests
# ---------------------------------------------------------------------------


class TestModelFields:
    def test_workflow_has_execution_mode_column(self):
        from backend.models.workflow import BizStageWorkflow

        assert hasattr(BizStageWorkflow, "execution_mode")

    def test_workflow_has_auto_pilot_state_column(self):
        from backend.models.workflow import BizStageWorkflow

        assert hasattr(BizStageWorkflow, "auto_pilot_state")

    def test_workflow_has_auto_pilot_next_stage_column(self):
        from backend.models.workflow import BizStageWorkflow

        assert hasattr(BizStageWorkflow, "auto_pilot_next_stage")

    def test_workflow_has_auto_pilot_error_message_column(self):
        from backend.models.workflow import BizStageWorkflow

        assert hasattr(BizStageWorkflow, "auto_pilot_error_message")

    def test_workflow_has_auto_pilot_started_at_column(self):
        from backend.models.workflow import BizStageWorkflow

        assert hasattr(BizStageWorkflow, "auto_pilot_started_at")

    def test_workflow_has_auto_pilot_paused_at_column(self):
        from backend.models.workflow import BizStageWorkflow

        assert hasattr(BizStageWorkflow, "auto_pilot_paused_at")

    def test_workflow_has_auto_pilot_index(self):
        from backend.models.workflow import BizStageWorkflow

        index_names = {idx.name for idx in BizStageWorkflow.__table__.indexes}
        assert "ix_biz_stage_workflows_auto_pilot" in index_names

    def test_workflow_has_execution_mode_check_constraint(self):
        from backend.models.workflow import BizStageWorkflow

        # The CHECK constraint should exist (name may vary)
        check_constraints = [
            cn
            for cn in BizStageWorkflow.__table__.constraints
            if hasattr(cn, "name") and cn.name is not None and "ck_" in str(cn.name)
        ]
        # At least one check constraint should reference execution_mode
        has_exec_mode_check = any("execution_mode" in str(cn) for cn in check_constraints)
        assert has_exec_mode_check

    def test_workflow_has_auto_pilot_state_check_constraint(self):
        from backend.models.workflow import BizStageWorkflow

        check_constraints = [
            cn
            for cn in BizStageWorkflow.__table__.constraints
            if hasattr(cn, "name") and cn.name is not None and "ck_" in str(cn.name)
        ]
        has_state_check = any("auto_pilot_state" in str(cn) for cn in check_constraints)
        assert has_state_check

    def test_workflow_has_status_check_constraint_extended(self):
        from backend.models.workflow import BizStageWorkflow

        check_constraints = [
            cn
            for cn in BizStageWorkflow.__table__.constraints
            if hasattr(cn, "name") and cn.name is not None and "ck_" in str(cn.name)
        ]
        # The status check should include PAUSED
        has_paused = any("PAUSED" in str(getattr(cn, "sqltext", "")) for cn in check_constraints)
        assert has_paused
