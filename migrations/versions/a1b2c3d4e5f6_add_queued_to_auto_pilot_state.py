"""add queued to auto_pilot_state

Revision ID: a1b2c3d4e5f6
Revises: 9bc26b63ffbd
Create Date: 2026-06-24 07:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "9bc26b63ffbd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility — batch_alter_table
    # transparently rebuilds the table when the backend doesn't support
    # ALTER TABLE … DROP CONSTRAINT.
    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        batch_op.drop_constraint(
            "ck_biz_stage_workflows_auto_pilot_state", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_biz_stage_workflows_auto_pilot_state",
            "auto_pilot_state IN ('idle', 'queued', 'running', 'paused', 'failed', 'completed')",
        )


def downgrade() -> None:
    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        batch_op.drop_constraint(
            "ck_biz_stage_workflows_auto_pilot_state", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_biz_stage_workflows_auto_pilot_state",
            "auto_pilot_state IN ('idle', 'running', 'paused', 'failed', 'completed')",
        )
