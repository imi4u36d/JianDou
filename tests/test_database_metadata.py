from __future__ import annotations

import pytest
pytestmark = pytest.mark.integration
from sqlalchemy import CheckConstraint

import backend.models  # noqa: F401
from backend.database import Base

REQUIRED_CONSTRAINED_STRING_COLUMNS = {
    ("biz_stage_versions", "stage_type"),
    ("biz_stage_versions", "status"),
    ("biz_stage_workflows", "current_stage"),
    ("biz_stage_workflows", "duration_mode"),
    ("biz_stage_workflows", "status"),
    ("biz_task_attempts", "status"),
    ("biz_task_attempts", "trigger_type"),
    ("biz_task_queue_events", "event_type"),
    ("biz_task_stage_runs", "status"),
    ("biz_tasks", "status"),
    ("biz_worker_instances", "status"),
    ("sys_credit_transaction", "transaction_type"),
    ("sys_invite_code", "role"),
    ("sys_invite_code", "status"),
    ("sys_user", "role"),
    ("sys_user", "status"),
}


def test_all_database_tables_and_columns_have_comments() -> None:
    missing_table_comments: list[str] = []
    missing_column_comments: list[str] = []

    for table in Base.metadata.sorted_tables:
        if not _non_blank(table.comment):
            missing_table_comments.append(table.name)
        for column in table.columns:
            if not _non_blank(column.comment):
                missing_column_comments.append(f"{table.name}.{column.name}")

    assert missing_table_comments == []
    assert missing_column_comments == []


def test_core_string_state_columns_are_constrained() -> None:
    unconstrained: list[str] = []

    for table_name, column_name in sorted(REQUIRED_CONSTRAINED_STRING_COLUMNS):
        table = Base.metadata.tables[table_name]
        if not _has_column_check_constraint(table, column_name):
            unconstrained.append(f"{table_name}.{column_name}")

    assert unconstrained == []


def _has_column_check_constraint(table: object, column_name: str) -> bool:
    for constraint in table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        if column_name in str(constraint.sqltext):
            return True
    return False


def _non_blank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
