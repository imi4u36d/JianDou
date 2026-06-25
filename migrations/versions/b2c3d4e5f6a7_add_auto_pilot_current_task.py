"""add auto_pilot_current_task column

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-25 12:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_pilot_current_task",
                sa.String(128),
                nullable=False,
                server_default="",
                comment="Human-readable label of the task currently executing, e.g. '正在生成分镜脚本'.",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("biz_stage_workflows") as batch_op:
        batch_op.drop_column("auto_pilot_current_task")
