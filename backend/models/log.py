from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from backend.database import Base


class BizRequestLog(Base):
    __tablename__ = "biz_request_logs"

    request_log_id = Column(String(64), primary_key=True)
    owner_user_id = Column(Integer, nullable=True)
    owner_ref_id = Column(String(64), nullable=True)
    task_id = Column(String(64), nullable=True)
    workflow_id = Column(String(64), nullable=True)
    request_type = Column(String(32), nullable=False)
    stage = Column(String(64), nullable=True)
    operation = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=True)
    provider_model = Column(String(128), nullable=True)
    requested_model = Column(String(128), nullable=True)
    resolved_model = Column(String(128), nullable=True)
    endpoint_host = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=True)
    status = Column(String(32), nullable=True)
    success = Column(Integer, nullable=True)
    http_status = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(String(32), nullable=True)
    finished_at = Column(String(32), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    timezone_offset_minutes = Column(Integer, nullable=True)
    create_time = Column(String(32), default=None)
    update_time = Column(String(32), default=None)
    is_deleted = Column(Integer, default=0)
