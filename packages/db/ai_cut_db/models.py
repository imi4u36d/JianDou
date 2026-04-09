from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.dialects.mysql import INTEGER as MYSQL_INTEGER
from sqlalchemy.dialects.mysql import TINYINT as MYSQL_TINYINT
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from ai_cut_db.db import Base
from ai_cut_shared.utils import utcnow

_UNSIGNED_BIGINT = (
    BigInteger()
    .with_variant(MYSQL_BIGINT(unsigned=True), "mysql")
    .with_variant(Integer(), "sqlite")
)
_UNSIGNED_INT = Integer().with_variant(MYSQL_INTEGER(unsigned=True), "mysql")
_UNSIGNED_TINYINT = SmallInteger().with_variant(MYSQL_TINYINT(unsigned=True), "mysql")

_SHANGHAI_TZ = timezone(timedelta(hours=8))


def shanghai_now() -> datetime:
    return datetime.now(_SHANGHAI_TZ)


class AuditMixin:
    # 业务语义按东八区记录，存储层保持 timezone-aware datetime。
    created_at: Mapped[datetime] = mapped_column(
        "create_time",
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间（业务时区：UTC+8）",
    )
    updated_at: Mapped[datetime] = mapped_column(
        "update_time",
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="更新时间（业务时区：UTC+8）",
    )
    is_deleted: Mapped[int] = mapped_column(
        _UNSIGNED_TINYINT,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="逻辑删除: 0-未删, 1-已删",
    )
    remark: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        server_default=text("''"),
        comment="备注",
    )


class Task(AuditMixin, Base):
    __tablename__ = "biz_tasks"
    __table_args__ = (
        UniqueConstraint("task_id", name="uk_task_id"),
        Index("idx_tasks_status_create_time", "status", "create_time"),
        Index("idx_tasks_platform_create_time", "platform", "create_time"),
        Index("idx_tasks_source_primary_asset_id", "source_primary_asset_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "comment": "任务主表（业务时间语义：UTC+8）",
        },
    )

    row_id: Mapped[int] = mapped_column(
        "id",
        _UNSIGNED_BIGINT,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
    )
    id: Mapped[str] = mapped_column("task_id", String(64), nullable=False, comment="任务业务ID")
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, default="generation", server_default=text("'generation'"), comment="任务类型")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default=text("''"), comment="任务标题")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="任务描述")
    platform: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="投放平台")
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default=text("''"), comment="画幅比例")
    min_duration_seconds: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="最小时长(秒)")
    max_duration_seconds: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="最大时长(秒)")
    output_count: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=1, server_default=text("1"), comment="输出数量")
    source_material_id: Mapped[str] = mapped_column("source_primary_asset_id", String(64), nullable=False, default="", server_default=text("''"), comment="主源素材ID")
    source_file_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default=text("''"), comment="主源素材文件名")
    source_material_ids_json: Mapped[list[str]] = mapped_column("source_asset_ids_json", JSON, nullable=False, default=list, comment="源素材ID列表")
    source_file_names_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="源素材文件名列表")
    request_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="任务请求快照")
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="任务上下文")
    intro_template: Mapped[str] = mapped_column(String(64), nullable=False, default="none", server_default=text("'none'"), comment="片头模板")
    outro_template: Mapped[str] = mapped_column(String(64), nullable=False, default="none", server_default=text("'none'"), comment="片尾模板")
    creative_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="创意提示词")
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="模型提供方")
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default=text("''"), comment="执行模式")
    editing_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="drama", server_default=text("'drama'"), comment="编辑模式")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default=text("'PENDING'"), comment="任务状态")
    progress: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="任务进度")
    error_code: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default=text("''"), comment="错误码")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="错误信息")
    plan_json: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="规划结果JSON")
    retry_count: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="重试次数")
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480, server_default=text("480"), comment="业务时区偏移分钟（东八区=480）")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间（UTC+8语义）")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间（UTC+8语义）")

    __mapper_args__ = {"primary_key": [id]}

    results: Mapped[list["TaskResult"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskResult.clip_index",
        primaryjoin="Task.id == foreign(TaskResult.task_id)",
    )
    status_history: Mapped[list["TaskStatusHistory"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStatusHistory.changed_at.desc()",
        primaryjoin="Task.id == foreign(TaskStatusHistory.task_id)",
    )
    model_calls: Mapped[list["TaskModelCall"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskModelCall.started_at.desc()",
        primaryjoin="Task.id == foreign(TaskModelCall.task_id)",
    )
    system_logs: Mapped[list["SystemLog"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="SystemLog.logged_at.desc()",
        primaryjoin="Task.id == foreign(SystemLog.task_id)",
    )
    source_asset: Mapped["MaterialAsset"] = relationship(
        primaryjoin="foreign(Task.source_material_id) == MaterialAsset.id",
        uselist=False,
    )


class TaskStatusHistory(AuditMixin, Base):
    __tablename__ = "biz_task_status_history"
    __table_args__ = (
        UniqueConstraint("task_status_history_id", name="uk_task_status_history_id"),
        Index("idx_task_status_history_task_id_change_time", "task_id", "change_time"),
        Index("idx_task_status_history_current_status", "current_status", "change_time"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "comment": "任务状态变更记录表（业务时间语义：UTC+8）",
        },
    )

    row_id: Mapped[int] = mapped_column("id", _UNSIGNED_BIGINT, primary_key=True, autoincrement=True, comment="主键ID")
    id: Mapped[str] = mapped_column("task_status_history_id", String(64), nullable=False, comment="状态记录业务ID")
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="任务业务ID")
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default=text("''"), comment="变更前状态")
    current_status: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default=text("''"), comment="变更后状态")
    progress: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="状态变更时进度")
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="处理阶段")
    event: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="事件名称")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="事件消息")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="扩展载荷")
    changed_at: Mapped[datetime] = mapped_column(
        "change_time",
        DateTime(timezone=True),
        nullable=False,
        default=shanghai_now,
        comment="状态变更时间（UTC+8语义）",
    )
    operator_type: Mapped[str] = mapped_column(String(32), nullable=False, default="system", server_default=text("'system'"), comment="操作者类型")
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="操作者标识")
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480, server_default=text("480"), comment="业务时区偏移分钟（东八区=480）")

    __mapper_args__ = {"primary_key": [id]}

    task: Mapped["Task"] = relationship(
        back_populates="status_history",
        primaryjoin="foreign(TaskStatusHistory.task_id) == Task.id",
    )


class TaskModelCall(AuditMixin, Base):
    __tablename__ = "biz_task_model_calls"
    __table_args__ = (
        UniqueConstraint("task_model_call_id", name="uk_task_model_call_id"),
        Index("idx_task_model_calls_task_id_start_time", "task_id", "started_at"),
        Index("idx_task_model_calls_provider_model", "provider", "resolved_model"),
        Index("idx_task_model_calls_success_start_time", "success", "started_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "comment": "任务模型调用记录表（请求/响应全链路，业务时间语义：UTC+8）",
        },
    )

    row_id: Mapped[int] = mapped_column("id", _UNSIGNED_BIGINT, primary_key=True, autoincrement=True, comment="主键ID")
    id: Mapped[str] = mapped_column("task_model_call_id", String(64), nullable=False, comment="模型调用业务ID")
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="任务业务ID")
    call_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default=text("''"), comment="调用类型")
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="调用阶段")
    operation: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="操作名")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="模型提供方")
    provider_model: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="提供方模型名")
    requested_model: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="请求模型名")
    resolved_model: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="最终模型名")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="模型名（兼容字段）")
    model_alias: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="模型别名（兼容字段）")
    endpoint_host: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default=text("''"), comment="请求目标主机")
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="上游请求ID")
    request_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="请求参数")
    response_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="响应参数")
    http_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"), comment="HTTP状态码")
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"), comment="HTTP状态码（兼容字段）")
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"), comment="调用是否成功")
    error_code: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default=text("''"), comment="错误码")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="错误信息")
    latency_ms: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="时延毫秒")
    duration_ms: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="调用耗时ms（兼容字段）")
    input_tokens: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="输入token")
    output_tokens: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="输出token")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=shanghai_now, comment="调用开始时间（UTC+8语义）")
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=shanghai_now, comment="调用结束时间（UTC+8语义）")
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480, server_default=text("480"), comment="业务时区偏移分钟（东八区=480）")

    __mapper_args__ = {"primary_key": [id]}

    task: Mapped["Task"] = relationship(
        back_populates="model_calls",
        primaryjoin="foreign(TaskModelCall.task_id) == Task.id",
    )


class TaskResult(AuditMixin, Base):
    __tablename__ = "biz_task_results"
    __table_args__ = (
        UniqueConstraint("task_result_id", name="uk_task_result_id"),
        UniqueConstraint("task_id", "clip_index", name="uk_task_results_task_clip"),
        Index("idx_task_results_task_id_clip_index", "task_id", "clip_index"),
        Index("idx_task_results_material_asset_id", "material_asset_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "comment": "任务结果表（视频/图片/文本等输出记录）",
        },
    )

    row_id: Mapped[int] = mapped_column("id", _UNSIGNED_BIGINT, primary_key=True, autoincrement=True, comment="主键ID")
    id: Mapped[str] = mapped_column("task_result_id", String(64), nullable=False, comment="任务结果业务ID")
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="任务业务ID")
    result_type: Mapped[str] = mapped_column(String(32), nullable=False, default="video", server_default=text("'video'"), comment="结果类型")
    clip_index: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="结果序号")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default=text("''"), comment="结果标题")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="结果说明")
    source_model_call_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="来源模型调用ID")
    material_asset_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="结果素材ID")
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=text("0"), comment="起始秒")
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=text("0"), comment="结束秒")
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=text("0"), comment="时长秒")
    preview_path: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="预览路径")
    download_path: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="下载路径")
    width: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="宽度")
    height: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="高度")
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="MIME类型")
    size_bytes: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, nullable=False, default=0, server_default=text("0"), comment="文件大小字节")
    remote_url: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="第三方结果地址")
    extra_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="扩展字段")
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=shanghai_now, comment="结果产出时间（UTC+8语义）")
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480, server_default=text("480"), comment="业务时区偏移分钟（东八区=480）")

    __mapper_args__ = {"primary_key": [id]}

    task: Mapped["Task"] = relationship(
        back_populates="results",
        primaryjoin="foreign(TaskResult.task_id) == Task.id",
    )
    material_asset: Mapped["MaterialAsset"] = relationship(
        primaryjoin="foreign(TaskResult.material_asset_id) == MaterialAsset.id",
        uselist=False,
    )


class SystemLog(AuditMixin, Base):
    __tablename__ = "biz_system_logs"
    __table_args__ = (
        UniqueConstraint("system_log_id", name="uk_system_log_id"),
        Index("idx_system_logs_task_id_logged_at", "task_id", "logged_at"),
        Index("idx_system_logs_level_logged_at", "level", "logged_at"),
        Index("idx_system_logs_module_stage", "module", "stage", "logged_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "comment": "系统日志表（全项目日志统一沉淀，业务时间语义：UTC+8）",
        },
    )

    row_id: Mapped[int] = mapped_column("id", _UNSIGNED_BIGINT, primary_key=True, autoincrement=True, comment="主键ID")
    id: Mapped[str] = mapped_column("system_log_id", String(64), nullable=False, comment="日志业务ID")
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="关联任务ID")
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="链路追踪ID")
    module: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="模块名")
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="阶段")
    event: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="事件")
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO", server_default=text("'INFO'"), comment="日志级别")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="日志消息")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="日志扩展参数")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="backend", server_default=text("'backend'"), comment="日志来源")
    service_name: Mapped[str] = mapped_column(String(64), nullable=False, default="pipeline", server_default=text("'pipeline'"), comment="服务名称")
    host_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="主机名")
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=shanghai_now, comment="日志时间（UTC+8语义）")
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480, server_default=text("480"), comment="业务时区偏移分钟（东八区=480）")

    __mapper_args__ = {"primary_key": [id]}

    task: Mapped["Task"] = relationship(
        back_populates="system_logs",
        primaryjoin="foreign(SystemLog.task_id) == Task.id",
    )


class MaterialAsset(AuditMixin, Base):
    __tablename__ = "biz_material_assets"
    __table_args__ = (
        UniqueConstraint("material_asset_id", name="uk_material_asset_id"),
        Index("idx_material_assets_task_id_role_create_time", "task_id", "asset_role", "create_time"),
        Index("idx_material_assets_sha256", "sha256"),
        Index("idx_material_assets_remote_task_id", "remote_task_id"),
        Index("idx_material_assets_media_type_create_time", "media_type", "create_time"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "comment": "素材表（源素材/中间素材/结果素材统一管理，业务时间语义：UTC+8）",
        },
    )

    row_id: Mapped[int] = mapped_column("id", _UNSIGNED_BIGINT, primary_key=True, autoincrement=True, comment="主键ID")
    id: Mapped[str] = mapped_column("material_asset_id", String(64), nullable=False, comment="素材业务ID")
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="关联任务ID")
    source_task_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="来源任务ID")
    source_material_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="来源素材ID（兼容字段）")
    asset_role: Mapped[str] = mapped_column(String(32), nullable=False, default="source", server_default=text("'source'"), comment="素材角色")
    media_type: Mapped[str] = mapped_column(String(32), nullable=False, default="video", server_default=text("'video'"), comment="媒体类型")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default=text("''"), comment="素材标题")
    origin_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default=text("''"), comment="来源提供方")
    origin_model: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="来源模型")
    remote_task_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="第三方任务ID")
    remote_asset_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="第三方素材ID")
    original_file_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default=text("''"), comment="原始文件名")
    stored_file_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default=text("''"), comment="存储文件名")
    file_ext: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default=text("''"), comment="文件后缀")
    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local", server_default=text("'local'"), comment="存储提供方")
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default=text("''"), comment="MIME类型")
    size_bytes: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, nullable=False, default=0, server_default=text("0"), comment="文件大小字节")
    sha256: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"), comment="内容哈希")
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=text("0"), comment="时长秒")
    width: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="宽度")
    height: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False, default=0, server_default=text("0"), comment="高度")
    has_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"), comment="是否有音轨")
    local_path: Mapped[str] = mapped_column("local_storage_path", Text, nullable=False, default="", comment="本地相对存储路径")
    local_file_path: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="本地绝对路径")
    public_url: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="对外访问URL")
    third_party_url: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="第三方URL（兼容字段）")
    remote_url: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="第三方URL")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="素材扩展元数据")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=shanghai_now, comment="素材采集时间（UTC+8语义）")
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480, server_default=text("480"), comment="业务时区偏移分钟（东八区=480）")

    __mapper_args__ = {"primary_key": [id]}

    @property
    def storage_path(self) -> str:
        return self.local_path

    @storage_path.setter
    def storage_path(self, value: str) -> None:
        self.local_path = value
