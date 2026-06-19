from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, Integer, String, Text

from backend.database import Base


class BizStageWorkflow(Base):
    __tablename__ = "biz_stage_workflows"
    __table_args__ = (
        CheckConstraint("status in ('DRAFT', 'READY', 'COMPLETED', 'FAILED')", name="ck_biz_stage_workflows_status"),
        CheckConstraint(
            "current_stage in ('storyboard', 'keyframe', 'video', 'joined')",
            name="ck_biz_stage_workflows_current_stage",
        ),
        CheckConstraint("duration_mode in ('auto', 'manual')", name="ck_biz_stage_workflows_duration_mode"),
        CheckConstraint("min_duration_seconds >= 1", name="ck_biz_stage_workflows_min_duration"),
        CheckConstraint("max_duration_seconds >= min_duration_seconds", name="ck_biz_stage_workflows_duration_range"),
        CheckConstraint("(effect_rating is null or effect_rating between 1 and 5)", name="ck_biz_stage_workflows_rating"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_stage_workflows_is_deleted"),
        Index("ix_biz_stage_workflows_owner_status", "owner_user_id", "status", "is_deleted"),
        {"comment": "Editable staged generation workflow owned by a user."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    workflow_id = Column(String(64), unique=True, nullable=False, comment="Public stable workflow identifier.")
    owner_user_id = Column(Integer, nullable=False, comment="Owner sys_user.id.")
    title = Column(String(512), nullable=False, default="", comment="User-facing workflow title.")
    transcript_text = Column(Text, nullable=True, comment="Source transcript or creative brief for storyboard generation.")
    global_prompt = Column(Text, nullable=True, comment="Optional global prompt applied across stages.")
    aspect_ratio = Column(String(32), nullable=False, comment="Target aspect ratio such as 16:9, 9:16, or 1:1.")
    style_preset = Column(String(128), nullable=False, comment="Visual style preset key.")
    text_analysis_model = Column(String(128), nullable=False, comment="Configured text model key for storyboard planning.")
    image_model = Column(String(128), nullable=False, comment="Configured image model key for keyframes.")
    video_model = Column(String(128), nullable=False, comment="Configured video model key for clip generation.")
    video_size = Column(String(32), nullable=False, comment="Target video size string, e.g. 1280*720.")
    keyframe_seed = Column(Integer, nullable=True, comment="Optional seed for image/keyframe generation.")
    video_seed = Column(Integer, nullable=True, comment="Optional seed for video generation.")
    task_seed = Column(Integer, nullable=True, comment="Shared seed captured at workflow creation.")
    min_duration_seconds = Column(Integer, nullable=False, comment="Minimum per-clip duration in seconds.")
    max_duration_seconds = Column(Integer, nullable=False, comment="Maximum per-clip duration in seconds.")
    duration_mode = Column(String(32), nullable=False, comment="Duration mode: auto or manual.")
    status = Column(String(32), nullable=False, comment="WorkflowStatus enum value.")
    current_stage = Column(String(64), nullable=False, comment="WorkflowStage enum value representing the active stage.")
    selected_storyboard_version_id = Column(String(64), nullable=False, comment="Selected storyboard stage_version_id.")
    final_join_asset_id = Column(String(64), nullable=False, comment="Final joined material_asset_id when available.")
    effect_rating = Column(Integer, nullable=True, comment="User workflow rating from 1 to 5.")
    effect_rating_note = Column(String(512), nullable=False, comment="Optional note attached to effect_rating.")
    rated_at = Column(String(32), nullable=True, comment="ISO timestamp when workflow rating was submitted.")
    metadata_json = Column(Text, nullable=False, comment="Mutable workflow metadata JSON.")
    timezone_offset_minutes = Column(Integer, nullable=False, comment="Client timezone offset captured at creation.")
    is_deleted = Column(Integer, nullable=False, comment="Soft delete flag: 0 active, 1 deleted.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the workflow was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the workflow was last updated.")
    remark = Column(String(512), nullable=False, comment="Operator remark; not used for core business logic.")


class BizStageVersion(Base):
    __tablename__ = "biz_stage_versions"
    __table_args__ = (
        CheckConstraint(
            "stage_type in ('storyboard', 'keyframe', 'video', 'joined')",
            name="ck_biz_stage_versions_stage_type",
        ),
        CheckConstraint(
            "status in ('QUEUED', 'SUBMITTED', 'RUNNING', 'ACCEPTED', 'SUCCEEDED', 'SUCCESS', 'COMPLETED', 'FAILED')",
            name="ck_biz_stage_versions_status",
        ),
        CheckConstraint("selected in (0, 1)", name="ck_biz_stage_versions_selected"),
        CheckConstraint("(rating is null or rating between 1 and 5)", name="ck_biz_stage_versions_rating"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_stage_versions_is_deleted"),
        Index("ix_biz_stage_versions_workflow_stage", "workflow_id", "stage_type", "clip_index", "is_deleted"),
        {"comment": "Versioned output for a workflow stage or clip."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    stage_version_id = Column(String(64), unique=True, nullable=False, comment="Public stable stage version identifier.")
    workflow_id = Column(String(64), nullable=False, comment="Parent biz_stage_workflows.workflow_id.")
    owner_user_id = Column(Integer, nullable=True, comment="Owner sys_user.id; nullable only for legacy rows.")
    stage_type = Column(String(64), nullable=False, comment="WorkflowStage enum value for this version.")
    clip_index = Column(Integer, nullable=False, comment="Storyboard/keyframe/video clip index; 0 for storyboard.")
    version_no = Column(Integer, nullable=False, comment="Sequential version number within stage and clip.")
    title = Column(String(512), nullable=False, comment="User-facing version title.")
    status = Column(String(32), nullable=False, comment="StageVersionStatus enum value.")
    selected = Column(Integer, nullable=False, comment="Selection flag: 0 not selected, 1 selected.")
    rating = Column(Integer, nullable=True, comment="User stage version rating from 1 to 5.")
    rating_note = Column(String(512), nullable=False, comment="Optional note attached to rating.")
    rated_at = Column(String(32), nullable=True, comment="ISO timestamp when rating was submitted.")
    parent_version_id = Column(String(64), nullable=False, comment="Parent stage_version_id used to derive this version.")
    source_material_asset_id = Column(String(64), nullable=False, comment="Source material_asset_id used to derive this version.")
    material_asset_id = Column(String(64), nullable=False, comment="Produced material_asset_id when available.")
    preview_url = Column(String(2048), nullable=False, comment="Preview URL for UI rendering.")
    download_url = Column(String(2048), nullable=False, comment="Download URL for produced media.")
    input_summary_json = Column(Text, nullable=False, comment="Condensed input snapshot JSON.")
    output_summary_json = Column(Text, nullable=False, comment="Condensed output snapshot JSON.")
    model_call_summary_json = Column(Text, nullable=False, comment="Condensed model invocation summary JSON.")
    timezone_offset_minutes = Column(Integer, nullable=False, comment="Client timezone offset captured at creation.")
    is_deleted = Column(Integer, nullable=False, comment="Soft delete flag: 0 active, 1 deleted.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the version was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the version was last updated.")
    remark = Column(String(512), nullable=False, comment="Operator remark; not used for core business logic.")
