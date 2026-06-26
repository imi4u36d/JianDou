"""Drop sys_user.display_name.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sys_user") as batch_op:
        batch_op.drop_column("display_name")


def downgrade() -> None:
    with op.batch_alter_table("sys_user") as batch_op:
        batch_op.add_column(
            sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
        )
        batch_op.alter_column("display_name", server_default=None)
