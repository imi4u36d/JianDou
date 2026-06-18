from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from backend.database import Base


class BizStageWorkflow(Base):
    __tablename__ = "biz_stage_workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(64), unique=True, nullable=False)
    owner_user_id = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False, default="")
    transcript_text = Column(Text, nullable=True)
    global_prompt = Column(Text, nullable=True)
    aspect_ratio = Column(String(32), nullable=False)
    style_preset = Column(String(128), nullable=False)
    text_analysis_model = Column(String(128), nullable=False)
    image_model = Column(String(128), nullable=False)
    video_model = Column(String(128), nullable=False)
    video_size = Column(String(32), nullable=False)
    keyframe_seed = Column(Integer, nullable=True)
    video_seed = Column(Integer, nullable=True)
    task_seed = Column(Integer, nullable=True)
    min_duration_seconds = Column(Integer, nullable=False)
    max_duration_seconds = Column(Integer, nullable=False)
    duration_mode = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    current_stage = Column(String(64), nullable=False)
    selected_storyboard_version_id = Column(String(64), nullable=False)
    final_join_asset_id = Column(String(64), nullable=False)
    effect_rating = Column(Integer, nullable=True)
    effect_rating_note = Column(String(512), nullable=False)
    rated_at = Column(String(32), nullable=True)
    metadata_json = Column(Text, nullable=False)
    timezone_offset_minutes = Column(Integer, nullable=False)
    is_deleted = Column(Integer, nullable=False)
    create_time = Column(String(32), nullable=False)
    update_time = Column(String(32), nullable=False)
    remark = Column(String(512), nullable=False)


class BizStageVersion(Base):
    __tablename__ = "biz_stage_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_version_id = Column(String(64), unique=True, nullable=False)
    workflow_id = Column(String(64), nullable=False)
    owner_user_id = Column(Integer, nullable=True)
    stage_type = Column(String(64), nullable=False)
    clip_index = Column(Integer, nullable=False)
    version_no = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False)
    selected = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=True)
    rating_note = Column(String(512), nullable=False)
    rated_at = Column(String(32), nullable=True)
    parent_version_id = Column(String(64), nullable=False)
    source_material_asset_id = Column(String(64), nullable=False)
    material_asset_id = Column(String(64), nullable=False)
    preview_url = Column(String(2048), nullable=False)
    download_url = Column(String(2048), nullable=False)
    input_summary_json = Column(Text, nullable=False)
    output_summary_json = Column(Text, nullable=False)
    model_call_summary_json = Column(Text, nullable=False)
    timezone_offset_minutes = Column(Integer, nullable=False)
    is_deleted = Column(Integer, nullable=False)
    create_time = Column(String(32), nullable=False)
    update_time = Column(String(32), nullable=False)
    remark = Column(String(512), nullable=False)
