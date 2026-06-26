"""add workflow auto-pilot fields

Revision ID: a1b2c3d4e5f6
Revises: 9bc26b63ffbd
Create Date: 2026-06-24 07:00:00.000000+00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "a1b2c3d4e5f6"
down_revision = "9bc26b63ffbd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind, "biz_stage_workflows")
    checks = _check_names(bind, "biz_stage_workflows")
    is_mysql = bind.dialect.name == "mysql"

    # Use batch mode for SQLite compatibility; batch_alter_table transparently
    # rebuilds the table when the backend cannot alter constraints in place.
    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        if "execution_mode" not in columns:
            batch_op.add_column(
                sa.Column(
                    "execution_mode",
                    sa.String(32),
                    nullable=False,
                    server_default="manual",
                    comment="Execution mode: auto or manual.",
                )
            )
        if "auto_pilot_state" not in columns:
            batch_op.add_column(
                sa.Column(
                    "auto_pilot_state",
                    sa.String(32),
                    nullable=False,
                    server_default="idle",
                    comment="AutoPilotState enum value.",
                )
            )
        if "auto_pilot_next_stage" not in columns:
            batch_op.add_column(
                sa.Column(
                    "auto_pilot_next_stage",
                    sa.String(64),
                    nullable=False,
                    server_default="",
                    comment="Next stage the auto-pilot should execute.",
                )
            )
        if "auto_pilot_error_message" not in columns:
            batch_op.add_column(
                sa.Column(
                    "auto_pilot_error_message",
                    sa.Text(),
                    nullable=is_mysql,
                    server_default=None if is_mysql else "",
                    comment="Error message when auto-pilot entered failed state.",
                )
            )
        if "auto_pilot_started_at" not in columns:
            batch_op.add_column(
                sa.Column(
                    "auto_pilot_started_at",
                    sa.String(32),
                    nullable=False,
                    server_default="",
                    comment="ISO timestamp when auto-pilot started execution.",
                )
            )
        if "auto_pilot_paused_at" not in columns:
            batch_op.add_column(
                sa.Column(
                    "auto_pilot_paused_at",
                    sa.String(32),
                    nullable=False,
                    server_default="",
                    comment="ISO timestamp when auto-pilot was paused.",
                )
            )

        if "ck_biz_stage_workflows_status" in checks:
            batch_op.drop_constraint("ck_biz_stage_workflows_status", type_="check")
        if "ck_biz_stage_workflows_execution_mode" in checks:
            batch_op.drop_constraint("ck_biz_stage_workflows_execution_mode", type_="check")
        if "ck_biz_stage_workflows_auto_pilot_state" in checks:
            batch_op.drop_constraint("ck_biz_stage_workflows_auto_pilot_state", type_="check")

        batch_op.create_check_constraint(
            "ck_biz_stage_workflows_status",
            "status in ('DRAFT', 'READY', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED')",
        )
        batch_op.create_check_constraint(
            "ck_biz_stage_workflows_execution_mode",
            "execution_mode in ('auto', 'manual')",
        )
        batch_op.create_check_constraint(
            "ck_biz_stage_workflows_auto_pilot_state",
            "auto_pilot_state in ('idle', 'queued', 'running', 'paused', 'failed', 'completed')",
        )

    if "ix_biz_stage_workflows_auto_pilot" not in _index_names(bind, "biz_stage_workflows"):
        op.create_index(
            "ix_biz_stage_workflows_auto_pilot",
            "biz_stage_workflows",
            ["auto_pilot_state", "is_deleted"],
            unique=False,
        )

    if is_mysql and "auto_pilot_error_message" in _column_names(bind, "biz_stage_workflows"):
        op.execute("UPDATE biz_stage_workflows SET auto_pilot_error_message = '' WHERE auto_pilot_error_message IS NULL")

    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        batch_op.alter_column("execution_mode", existing_type=sa.String(32), server_default=None)
        batch_op.alter_column("auto_pilot_state", existing_type=sa.String(32), server_default=None)
        batch_op.alter_column("auto_pilot_next_stage", existing_type=sa.String(64), server_default=None)
        batch_op.alter_column("auto_pilot_error_message", existing_type=sa.Text(), nullable=False, server_default=None)
        batch_op.alter_column("auto_pilot_started_at", existing_type=sa.String(32), server_default=None)
        batch_op.alter_column("auto_pilot_paused_at", existing_type=sa.String(32), server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind, "biz_stage_workflows")
    checks = _check_names(bind, "biz_stage_workflows")

    if "ix_biz_stage_workflows_auto_pilot" in _index_names(bind, "biz_stage_workflows"):
        op.drop_index("ix_biz_stage_workflows_auto_pilot", table_name="biz_stage_workflows")

    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        for constraint_name in (
            "ck_biz_stage_workflows_auto_pilot_state",
            "ck_biz_stage_workflows_execution_mode",
            "ck_biz_stage_workflows_status",
        ):
            if constraint_name in checks:
                batch_op.drop_constraint(constraint_name, type_="check")

        for column_name in (
            "auto_pilot_paused_at",
            "auto_pilot_started_at",
            "auto_pilot_error_message",
            "auto_pilot_next_stage",
            "auto_pilot_state",
            "execution_mode",
        ):
            if column_name in columns:
                batch_op.drop_column(column_name)

        batch_op.create_check_constraint(
            "ck_biz_stage_workflows_status",
            "status in ('DRAFT', 'READY', 'COMPLETED', 'FAILED')",
        )


def _column_names(bind, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def _check_names(bind, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspect(bind).get_check_constraints(table_name)}


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in inspect(bind).get_indexes(table_name)}
