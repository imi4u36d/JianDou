"""Drop obsolete workflow preset column.

Revision ID: 0a1b2c3d4e5f
Revises: f9a0b1c2d3e4
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0a1b2c3d4e5f"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None

_TABLE_NAME = "biz_stage_workflows"
_COLUMN_NAME = "style_preset"


def _has_column() -> bool:
    inspector = inspect(op.get_bind())
    if _TABLE_NAME not in inspector.get_table_names():
        return False
    return _COLUMN_NAME in {column["name"] for column in inspector.get_columns(_TABLE_NAME)}


def upgrade() -> None:
    if _has_column():
        op.drop_column(_TABLE_NAME, _COLUMN_NAME)


def downgrade() -> None:
    if not _has_column():
        op.add_column(
            _TABLE_NAME,
            sa.Column(
                _COLUMN_NAME,
                sa.String(length=128),
                nullable=False,
                server_default="cinematic",
                comment="Obsolete workflow preset key.",
            ),
        )
        op.alter_column(_TABLE_NAME, _COLUMN_NAME, server_default=None)
