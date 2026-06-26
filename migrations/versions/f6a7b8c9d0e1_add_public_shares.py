"""add public shares

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "biz_public_shares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Internal numeric primary key."),
        sa.Column("share_id", sa.String(length=64), nullable=False, comment="Public stable share identifier."),
        sa.Column("owner_user_id", sa.Integer(), nullable=False, comment="Owner sys_user.id that published the share."),
        sa.Column("material_asset_id", sa.String(length=64), nullable=False, comment="Shared biz_material_assets.material_asset_id."),
        sa.Column("source_type", sa.String(length=32), nullable=False, comment="Source aggregate type: task, workflow, or material."),
        sa.Column("source_id", sa.String(length=64), nullable=False, comment="Source task_id, workflow_id, or material_asset_id."),
        sa.Column("media_type", sa.String(length=32), nullable=False, comment="Shared media type: image or video."),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="", comment="Display title captured at share time."),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE", comment="Share visibility status."),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0", comment="Cached active like count."),
        sa.Column("create_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the share was first created."),
        sa.Column("update_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the share was last updated."),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0", comment="Soft delete flag: 0 active, 1 deleted."),
        sa.Column("remark", sa.String(length=512), nullable=False, server_default="", comment="Operator remark; not used for core business logic."),
        sa.CheckConstraint("source_type in ('task', 'workflow', 'material')", name="ck_biz_public_shares_source_type"),
        sa.CheckConstraint("media_type in ('image', 'video')", name="ck_biz_public_shares_media_type"),
        sa.CheckConstraint("status in ('ACTIVE', 'REMOVED')", name="ck_biz_public_shares_status"),
        sa.CheckConstraint("like_count >= 0", name="ck_biz_public_shares_like_count_non_negative"),
        sa.CheckConstraint("is_deleted in (0, 1)", name="ck_biz_public_shares_is_deleted"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_id"),
        sa.UniqueConstraint("material_asset_id"),
        comment="User-confirmed public shares displayed on the home gallery.",
    )
    op.create_index("ix_biz_public_shares_media_status", "biz_public_shares", ["media_type", "status", "is_deleted"])
    op.create_index("ix_biz_public_shares_owner_status", "biz_public_shares", ["owner_user_id", "status", "is_deleted"])
    op.create_index("ix_biz_public_shares_popular", "biz_public_shares", ["status", "like_count", "create_time"])

    op.create_table(
        "biz_public_share_likes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Internal numeric primary key."),
        sa.Column("like_id", sa.String(length=64), nullable=False, comment="Public stable like identifier."),
        sa.Column("share_id", sa.String(length=64), nullable=False, comment="Parent biz_public_shares.share_id."),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="Liking sys_user.id."),
        sa.Column("create_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the like was first created."),
        sa.Column("update_time", sa.String(length=32), nullable=False, comment="ISO timestamp when the like was last updated."),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0", comment="Soft delete flag: 0 active, 1 removed."),
        sa.Column("remark", sa.String(length=512), nullable=False, server_default="", comment="Operator remark; not used for core business logic."),
        sa.CheckConstraint("is_deleted in (0, 1)", name="ck_biz_public_share_likes_is_deleted"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("like_id"),
        comment="Per-user likes for public shares.",
    )
    op.create_index("ux_biz_public_share_likes_share_user", "biz_public_share_likes", ["share_id", "user_id"], unique=True)
    op.create_index("ix_biz_public_share_likes_user", "biz_public_share_likes", ["user_id", "is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_biz_public_share_likes_user", table_name="biz_public_share_likes")
    op.drop_index("ux_biz_public_share_likes_share_user", table_name="biz_public_share_likes")
    op.drop_table("biz_public_share_likes")
    op.drop_index("ix_biz_public_shares_popular", table_name="biz_public_shares")
    op.drop_index("ix_biz_public_shares_owner_status", table_name="biz_public_shares")
    op.drop_index("ix_biz_public_shares_media_status", table_name="biz_public_shares")
    op.drop_table("biz_public_shares")
