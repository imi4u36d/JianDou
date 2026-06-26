from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, Integer, String

from backend.database import Base


class BizPublicShare(Base):
    __tablename__ = "biz_public_shares"
    __table_args__ = (
        CheckConstraint("source_type in ('task', 'workflow', 'material')", name="ck_biz_public_shares_source_type"),
        CheckConstraint("media_type in ('image', 'video')", name="ck_biz_public_shares_media_type"),
        CheckConstraint("status in ('ACTIVE', 'REMOVED')", name="ck_biz_public_shares_status"),
        CheckConstraint("like_count >= 0", name="ck_biz_public_shares_like_count_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_public_shares_is_deleted"),
        Index("ix_biz_public_shares_media_status", "media_type", "status", "is_deleted"),
        Index("ix_biz_public_shares_owner_status", "owner_user_id", "status", "is_deleted"),
        Index("ix_biz_public_shares_popular", "status", "like_count", "create_time"),
        {"comment": "User-confirmed public shares displayed on the home gallery."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    share_id = Column(String(64), nullable=False, unique=True, comment="Public stable share identifier.")
    owner_user_id = Column(Integer, nullable=False, comment="Owner sys_user.id that published the share.")
    material_asset_id = Column(String(64), nullable=False, unique=True, comment="Shared biz_material_assets.material_asset_id.")
    source_type = Column(String(32), nullable=False, comment="Source aggregate type: task, workflow, or material.")
    source_id = Column(String(64), nullable=False, comment="Source task_id, workflow_id, or material_asset_id.")
    media_type = Column(String(32), nullable=False, comment="Shared media type: image or video.")
    title = Column(String(255), nullable=False, default="", comment="Display title captured at share time.")
    status = Column(String(32), nullable=False, default="ACTIVE", comment="Share visibility status.")
    like_count = Column(Integer, nullable=False, default=0, comment="Cached active like count.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the share was first created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the share was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizPublicShareLike(Base):
    __tablename__ = "biz_public_share_likes"
    __table_args__ = (
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_public_share_likes_is_deleted"),
        Index("ux_biz_public_share_likes_share_user", "share_id", "user_id", unique=True),
        Index("ix_biz_public_share_likes_user", "user_id", "is_deleted"),
        {"comment": "Per-user likes for public shares."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    like_id = Column(String(64), nullable=False, unique=True, comment="Public stable like identifier.")
    share_id = Column(String(64), nullable=False, comment="Parent biz_public_shares.share_id.")
    user_id = Column(Integer, nullable=False, comment="Liking sys_user.id.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the like was first created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the like was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 removed.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")
