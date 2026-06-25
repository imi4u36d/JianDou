"""add runtime provider config to user credentials

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-25 17:45:00.000000+08:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind, "sys_user_model_credential")
    with op.batch_alter_table("sys_user_model_credential") as batch_op:
        if "base_url" not in columns:
            batch_op.add_column(
                sa.Column(
                    "base_url",
                    sa.Text(),
                    nullable=False,
                    server_default="",
                    comment="User-scoped provider API base URL.",
                )
            )
        if "task_base_url" not in columns:
            batch_op.add_column(
                sa.Column(
                    "task_base_url",
                    sa.Text(),
                    nullable=False,
                    server_default="",
                    comment="User-scoped async task polling base URL.",
                )
            )
        if "extras_json" not in columns:
            batch_op.add_column(
                sa.Column(
                    "extras_json",
                    sa.Text(),
                    nullable=False,
                    server_default="{}",
                    comment="User-scoped provider runtime extras JSON.",
                )
            )

    with op.batch_alter_table("sys_user_model_credential") as batch_op:
        if "base_url" not in columns:
            batch_op.alter_column("base_url", existing_type=sa.Text(), server_default=None)
        if "task_base_url" not in columns:
            batch_op.alter_column("task_base_url", existing_type=sa.Text(), server_default=None)
        if "extras_json" not in columns:
            batch_op.alter_column("extras_json", existing_type=sa.Text(), server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind, "sys_user_model_credential")
    with op.batch_alter_table("sys_user_model_credential") as batch_op:
        if "extras_json" in columns:
            batch_op.drop_column("extras_json")
        if "task_base_url" in columns:
            batch_op.drop_column("task_base_url")
        if "base_url" in columns:
            batch_op.drop_column("base_url")


def _column_names(bind, table_name: str) -> set[str]:
    return {col["name"] for col in inspect(bind).get_columns(table_name)}
