"""Drop sys_user.display_name.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_column("sys_user", "display_name"):
        return

    with op.batch_alter_table("sys_user") as batch_op:
        batch_op.drop_column("display_name")


def downgrade() -> None:
    if _has_column("sys_user", "display_name"):
        return

    with op.batch_alter_table("sys_user") as batch_op:
        batch_op.add_column(
            sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
        )
        batch_op.alter_column("display_name", server_default=None)


def _has_column(table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}
