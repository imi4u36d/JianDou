"""Add durable user preference table.

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f9a0b1c2d3e4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sys_user_preference",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Internal numeric primary key."),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="Owner sys_user.id."),
        sa.Column(
            "preference_key",
            sa.String(length=128),
            nullable=False,
            comment="Stable preference key, e.g. generation.default_aspect_ratio.",
        ),
        sa.Column("preference_value", sa.String(length=2048), nullable=False, comment="Serialized preference value."),
        sa.Column("created_at", sa.String(length=32), nullable=False, comment="ISO timestamp when the preference was created."),
        sa.Column("updated_at", sa.String(length=32), nullable=False, comment="ISO timestamp when the preference was last updated."),
        sa.PrimaryKeyConstraint("id"),
        comment="Per-user durable preference key-value storage.",
    )
    op.create_index("ix_sys_user_preference_user", "sys_user_preference", ["user_id"], unique=False)
    op.create_index(
        "ux_sys_user_preference_user_key",
        "sys_user_preference",
        ["user_id", "preference_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_sys_user_preference_user_key", table_name="sys_user_preference")
    op.drop_index("ix_sys_user_preference_user", table_name="sys_user_preference")
    op.drop_table("sys_user_preference")
