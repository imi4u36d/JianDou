from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, Integer, String, Text

from backend.database import Base


class BizRequestLog(Base):
    __tablename__ = "biz_request_logs"
    __table_args__ = (
        CheckConstraint("length(trim(request_type)) > 0", name="ck_biz_request_logs_request_type_not_blank"),
        CheckConstraint("(success is null or success in (0, 1))", name="ck_biz_request_logs_success"),
        CheckConstraint("(http_status is null or http_status >= 0)", name="ck_biz_request_logs_http_status_non_negative"),
        CheckConstraint("(duration_ms is null or duration_ms >= 0)", name="ck_biz_request_logs_duration_non_negative"),
        CheckConstraint("(timezone_offset_minutes is null or timezone_offset_minutes between -840 and 840)", name="ck_biz_request_logs_timezone_offset"),
        CheckConstraint("(is_deleted is null or is_deleted in (0, 1))", name="ck_biz_request_logs_is_deleted"),
        Index("ix_biz_request_logs_owner_time", "owner_user_id", "create_time", "is_deleted"),
        Index("ix_biz_request_logs_task_time", "task_id", "create_time", "is_deleted"),
        Index("ix_biz_request_logs_workflow_time", "workflow_id", "create_time", "is_deleted"),
        {"comment": "Audit log for provider and backend operation requests."},
    )

    request_log_id = Column(String(64), primary_key=True, comment="Public stable request log identifier.")
    owner_user_id = Column(Integer, nullable=True, comment="Owner sys_user.id when the request is user-scoped.")
    owner_ref_id = Column(String(64), nullable=True, comment="Generic owner reference id, usually task_id or workflow_id.")
    task_id = Column(String(64), nullable=True, comment="Related biz_tasks.task_id when available.")
    workflow_id = Column(String(64), nullable=True, comment="Related biz_stage_workflows.workflow_id when available.")
    request_type = Column(String(32), nullable=False, comment="Request category such as text, image, video, workflow, or backend.")
    stage = Column(String(64), nullable=True, comment="Pipeline or workflow stage that issued the request.")
    operation = Column(String(64), nullable=True, comment="Operation name within the stage.")
    provider = Column(String(64), nullable=True, comment="Configured provider key.")
    provider_model = Column(String(128), nullable=True, comment="Provider-reported model identifier.")
    requested_model = Column(String(128), nullable=True, comment="Model requested by task or workflow configuration.")
    resolved_model = Column(String(128), nullable=True, comment="Final model selected after alias/provider resolution.")
    endpoint_host = Column(String(255), nullable=True, comment="Remote endpoint host without secrets.")
    request_id = Column(String(64), nullable=True, comment="Provider request id or correlation id when available.")
    status = Column(String(32), nullable=True, comment="Provider or backend status string captured for audit.")
    success = Column(Integer, nullable=True, comment="Success flag: 0 failed, 1 succeeded, null unknown.")
    http_status = Column(Integer, nullable=True, comment="HTTP status code when available.")
    error_code = Column(String(64), nullable=True, comment="Machine-readable error code.")
    error_message = Column(Text, nullable=True, comment="Human-readable error message.")
    started_at = Column(String(32), nullable=True, comment="ISO timestamp when the request started.")
    finished_at = Column(String(32), nullable=True, comment="ISO timestamp when the request finished.")
    duration_ms = Column(Integer, nullable=True, comment="Request duration in milliseconds.")
    timezone_offset_minutes = Column(Integer, nullable=True, comment="Client timezone offset captured for the request.")
    create_time = Column(String(32), default=None, comment="ISO timestamp when the row was created.")
    update_time = Column(String(32), default=None, comment="ISO timestamp when the row was last updated.")
    is_deleted = Column(Integer, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
