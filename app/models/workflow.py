from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class BizStageWorkflow(Base):
    __tablename__ = "biz_stage_workflows"

    workflow_id = Column(String(64), primary_key=True)
    owner_user_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False, default="")
    transcript_text = Column(Text, nullable=True)
    global_prompt = Column(Text, nullable=True)
    aspect_ratio = Column(String(32), nullable=True)
    style_preset = Column(String(64), nullable=True)
    text_analysis_model = Column(String(128), nullable=True)
    image_model = Column(String(128), nullable=True)
    video_model = Column(String(128), nullable=True)
    video_size = Column(String(32), nullable=True)
    keyframe_seed = Column(Integer, nullable=True)
    video_seed = Column(Integer, nullable=True)
    duration_mode = Column(String(32), nullable=True)
    task_seed = Column(Integer, nullable=True)
    min_duration_seconds = Column(Integer, nullable=True)
    max_duration_seconds = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False)
    current_stage = Column(String(64), nullable=True)
    selected_storyboard_version_id = Column(String(64), nullable=True)
    final_join_asset_id = Column(String(64), nullable=True)
    effect_rating = Column(Integer, nullable=True)
    effect_rating_note = Column(Text, nullable=True)
    rated_at = Column(String(32), nullable=True)
    metadata_json = Column(Text, nullable=True)
    create_time = Column(String(32), default=None)
    update_time = Column(String(32), default=None)
    is_deleted = Column(Integer, default=0)


class BizStageVersion(Base):
    __tablename__ = "biz_stage_versions"

    stage_version_id = Column(String(64), primary_key=True)
    workflow_id = Column(String(64), nullable=False)
    owner_user_id = Column(Integer, nullable=False)
    stage_type = Column(String(64), nullable=False)
    clip_index = Column(Integer, nullable=True)
    version_no = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False)
    selected = Column(Integer, default=0)
    rating = Column(Integer, nullable=True)
    rating_note = Column(Text, nullable=True)
    rated_at = Column(String(32), nullable=True)
    parent_version_id = Column(String(64), nullable=True)
    source_material_asset_id = Column(String(64), nullable=True)
    material_asset_id = Column(String(64), nullable=True)
    preview_url = Column(String(1024), nullable=True)
    download_url = Column(String(1024), nullable=True)
    input_summary_json = Column(Text, nullable=True)
    output_summary_json = Column(Text, nullable=True)
    model_call_summary_json = Column(Text, nullable=True)
    create_time = Column(String(32), default=None)
    update_time = Column(String(32), default=None)
    is_deleted = Column(Integer, default=0)
