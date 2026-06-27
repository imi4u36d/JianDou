"""Add durable user preference table.

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "f9a0b1c2d3e4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None

_TABLE_NAME = "sys_user_preference"
_USER_INDEX_NAME = "ix_sys_user_preference_user"
_USER_KEY_INDEX_NAME = "ux_sys_user_preference_user_key"
_REQUIRED_COLUMNS = {
    "id",
    "user_id",
    "preference_key",
    "preference_value",
    "created_at",
    "updated_at",
}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if _TABLE_NAME in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
        missing_columns = _REQUIRED_COLUMNS - existing_columns
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise RuntimeError(f"{_TABLE_NAME} already exists but is missing required columns: {missing}")
    else:
        op.create_table(
            _TABLE_NAME,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Internal numeric primary key."),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="Owner sys_user.id."),
            sa.Column(
                "preference_key",
                sa.String(length=128),
                nullable=False,
                comment="Stable preference key, e.g. generation.default_aspect_ratio.",
            ),
            sa.Column("preference_value", sa.String(length=2048), nullable=False, comment="Serialized preference value."),
            sa.Column(
                "created_at",
                sa.String(length=32),
                nullable=False,
                comment="ISO timestamp when the preference was created.",
            ),
            sa.Column(
                "updated_at",
                sa.String(length=32),
                nullable=False,
                comment="ISO timestamp when the preference was last updated.",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="Per-user durable preference key-value storage.",
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes(_TABLE_NAME)}
    if _USER_INDEX_NAME not in existing_indexes:
        op.create_index(_USER_INDEX_NAME, _TABLE_NAME, ["user_id"], unique=False)
    if _USER_KEY_INDEX_NAME not in existing_indexes:
        op.create_index(
            _USER_KEY_INDEX_NAME,
            _TABLE_NAME,
            ["user_id", "preference_key"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(_USER_KEY_INDEX_NAME, table_name=_TABLE_NAME)
    op.drop_index(_USER_INDEX_NAME, table_name=_TABLE_NAME)
    op.drop_table(_TABLE_NAME)
