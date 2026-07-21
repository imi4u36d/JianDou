"""Drop the retired public sharing tables.

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-07-20 00:00:00.000000+08:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "1b2c3d4e5f6a"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None

_SHARES_TABLE = "biz_public_shares"
_LIKES_TABLE = "biz_public_share_likes"


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    table_names = _table_names()
    if _LIKES_TABLE in table_names:
        op.drop_table(_LIKES_TABLE)
    if _SHARES_TABLE in table_names:
        op.drop_table(_SHARES_TABLE)


def downgrade() -> None:
    table_names = _table_names()
    if _SHARES_TABLE not in table_names:
        op.create_table(
            _SHARES_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Internal numeric primary key."),
            sa.Column("share_id", sa.String(length=64), nullable=False, comment="Public stable share identifier."),
            sa.Column("owner_user_id", sa.Integer(), nullable=False, comment="Owner sys_user.id that published the share."),
            sa.Column("material_asset_id", sa.String(length=64), nullable=False, comment="Shared biz_material_assets.material_asset_id."),
            sa.Column("source_type", sa.String(length=32), nullable=False, comment="Source aggregate type: task, workflow, or material."),
            sa.Column("source_id", sa.String(length=64), nullable=False, comment="Source task_id, workflow_id, or material_asset_id."),
            sa.Column("media_type", sa.String(length=32), nullable=False, comment="Shared media type: image or video."),
            sa.Column("title", sa.String(length=255), nullable=False, comment="Display title captured at share time."),
            sa.Column("status", sa.String(length=32), nullable=False, comment="Share visibility status."),
            sa.Column("like_count", sa.Integer(), nullable=False, comment="Cached active like count."),
            sa.Column("create_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the share was first created."),
            sa.Column("update_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the share was last updated."),
            sa.Column("is_deleted", sa.Integer(), nullable=False, comment="Soft delete flag: 0 active, 1 deleted."),
            sa.Column("remark", sa.String(length=512), nullable=False, comment="Operator remark; not used for core business logic."),
            sa.CheckConstraint("source_type in ('task', 'workflow', 'material')", name="ck_biz_public_shares_source_type"),
            sa.CheckConstraint("media_type in ('image', 'video')", name="ck_biz_public_shares_media_type"),
            sa.CheckConstraint("status in ('ACTIVE', 'REMOVED')", name="ck_biz_public_shares_status"),
            sa.CheckConstraint("like_count >= 0", name="ck_biz_public_shares_like_count_non_negative"),
            sa.CheckConstraint("is_deleted in (0, 1)", name="ck_biz_public_shares_is_deleted"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("material_asset_id"),
            sa.UniqueConstraint("share_id"),
            comment="User-confirmed public shares displayed on the home gallery.",
        )
        op.create_index("ix_biz_public_shares_media_status", _SHARES_TABLE, ["media_type", "status", "is_deleted"])
        op.create_index("ix_biz_public_shares_owner_status", _SHARES_TABLE, ["owner_user_id", "status", "is_deleted"])
        op.create_index("ix_biz_public_shares_popular", _SHARES_TABLE, ["status", "like_count", "create_time"])

    if _LIKES_TABLE not in table_names:
        op.create_table(
            _LIKES_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Internal numeric primary key."),
            sa.Column("like_id", sa.String(length=64), nullable=False, comment="Public stable like identifier."),
            sa.Column("share_id", sa.String(length=64), nullable=False, comment="Parent biz_public_shares.share_id."),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="Liking sys_user.id."),
            sa.Column("create_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the like was first created."),
            sa.Column("update_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the like was last updated."),
            sa.Column("is_deleted", sa.Integer(), nullable=False, comment="Soft delete flag: 0 active, 1 removed."),
            sa.Column("remark", sa.String(length=512), nullable=False, comment="Operator remark; not used for core business logic."),
            sa.CheckConstraint("is_deleted in (0, 1)", name="ck_biz_public_share_likes_is_deleted"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("like_id"),
            comment="Per-user likes for public shares.",
        )
        op.create_index("ux_biz_public_share_likes_share_user", _LIKES_TABLE, ["share_id", "user_id"], unique=True)
        op.create_index("ix_biz_public_share_likes_user", _LIKES_TABLE, ["user_id", "is_deleted"])
