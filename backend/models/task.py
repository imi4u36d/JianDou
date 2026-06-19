from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Float, Index, Integer, String, Text

from backend.database import Base


class BizTask(Base):
    """Top-level generation task.

    This table intentionally keeps the public task contract stable while the
    worker pipeline evolves. Fields marked as legacy/deprecated should be read
    for compatibility only and removed through an Alembic migration later.
    """

    __tablename__ = "biz_tasks"
    __table_args__ = (
        CheckConstraint(
            "status in ('PENDING', 'PAUSED', 'ANALYZING', 'PLANNING', 'RENDERING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_biz_tasks_status",
        ),
        CheckConstraint("(progress is null or progress between 0 and 100)", name="ck_biz_tasks_progress"),
        CheckConstraint("(effect_rating is null or effect_rating between 1 and 5)", name="ck_biz_tasks_effect_rating"),
        CheckConstraint("(retry_count is null or retry_count >= 0)", name="ck_biz_tasks_retry_count"),
        CheckConstraint("(min_duration_seconds is null or min_duration_seconds >= 1)", name="ck_biz_tasks_min_duration"),
        CheckConstraint(
            "(min_duration_seconds is null or max_duration_seconds is null or max_duration_seconds >= min_duration_seconds)",
            name="ck_biz_tasks_duration_range",
        ),
        CheckConstraint("(is_deleted is null or is_deleted in (0, 1))", name="ck_biz_tasks_is_deleted"),
        Index("ix_biz_tasks_owner_status", "owner_user_id", "status", "is_deleted"),
        Index("ix_biz_tasks_created", "create_time"),
        {"comment": "Generation task aggregate root; owns lifecycle, request snapshot and worker progress."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_id = Column(String(64), nullable=False, unique=True, comment="Public stable task identifier used by APIs and child tables.")
    owner_user_id = Column(Integer, nullable=True, comment="Owner sys_user.id; nullable only for legacy rows.")
    task_type = Column(String(64), nullable=False, comment="Task flow type, e.g. video_generation, image_generation, image_to_image.")
    title = Column(String(255), nullable=False, default="", comment="User-facing task title.")
    description = Column(Text, nullable=True, comment="Optional user-facing task description.")
    aspect_ratio = Column(String(32), nullable=True, comment="Requested aspect ratio such as 16:9 or 9:16.")
    min_duration_seconds = Column(Integer, nullable=True, comment="Minimum requested output duration in seconds.")
    max_duration_seconds = Column(Integer, nullable=True, comment="Maximum requested output duration in seconds.")
    output_count = Column(Integer, nullable=True, comment="Deprecated: requested output count. Prefer request_payload_json.outputCount.")
    source_primary_asset_id = Column(String(64), nullable=True, comment="Deprecated: primary source material id. Prefer material tables.")
    source_file_name = Column(String(255), nullable=True, comment="Original uploaded source file name for display/search.")
    source_asset_ids_json = Column(Text, nullable=True, comment="Deprecated JSON list of source asset ids. Prefer material tables.")
    source_file_names_json = Column(Text, nullable=True, comment="Deprecated JSON list of source file names. Prefer material tables.")
    request_payload_json = Column(Text, nullable=True, comment="Immutable request snapshot used to reproduce the task.")
    context_json = Column(Text, nullable=True, comment="Mutable execution context produced by planning/rendering stages.")
    intro_template = Column(Text, nullable=True, comment="Selected intro template key or serialized template data.")
    outro_template = Column(Text, nullable=True, comment="Selected outro template key or serialized template data.")
    creative_prompt = Column(Text, nullable=True, comment="User prompt or generated creative prompt used for the task.")
    task_seed = Column(Integer, nullable=True, comment="Optional random seed applied across task stages when supported.")
    effect_rating = Column(Integer, nullable=True, comment="User rating from 1 to 5 after reviewing output.")
    effect_rating_note = Column(Text, nullable=True, comment="Optional note attached to effect_rating.")
    rated_at = Column(String(32), nullable=True, comment="ISO timestamp when effect_rating was submitted.")
    model_provider = Column(String(64), nullable=True, comment="Deprecated aggregate provider hint. Prefer request_payload_json model fields.")
    execution_mode = Column(String(32), nullable=True, comment="Execution mode snapshot, e.g. queue or direct.")
    editing_mode = Column(String(32), nullable=True, comment="Creative/editing preset key used by planning.")
    status = Column(String(32), nullable=False, comment="TaskStatus enum value; stored as string until DB enum migration.")
    progress = Column(Integer, nullable=True, comment="Coarse progress percentage from 0 to 100.")
    error_code = Column(String(64), nullable=True, comment="Machine-readable terminal error code.")
    error_message = Column(Text, nullable=True, comment="Human-readable terminal error message.")
    plan_json = Column(Text, nullable=True, comment="Deprecated: historical plan payload. Prefer context_json/storyboard artifacts.")
    retry_count = Column(Integer, default=0, comment="Number of retry attempts requested for this task.")
    timezone_offset_minutes = Column(Integer, nullable=True, comment="Client timezone offset captured at task creation.")
    started_at = Column(String(32), nullable=True, comment="ISO timestamp when execution first started.")
    finished_at = Column(String(32), nullable=True, comment="ISO timestamp when execution reached a terminal state.")
    create_time = Column(String(32), default=None, comment="ISO timestamp when the row was created.")
    update_time = Column(String(32), default=None, comment="ISO timestamp when the row was last updated.")
    is_deleted = Column(Integer, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizTaskStatusHistory(Base):
    __tablename__ = "biz_task_status_history"
    __table_args__ = (
        CheckConstraint("progress between 0 and 100", name="ck_biz_task_status_history_progress"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_task_status_history_is_deleted"),
        Index("ix_biz_task_status_history_task_time", "task_id", "change_time", "is_deleted"),
        {"comment": "Append-only task status and trace history. Empty statuses are allowed for trace-only rows."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_status_history_id = Column(String(64), nullable=False, unique=True, comment="Public stable status history identifier.")
    task_id = Column(String(64), nullable=False, comment="Parent biz_tasks.task_id.")
    previous_status = Column(String(32), nullable=False, default="", comment="Previous TaskStatus value; empty for trace-only rows.")
    current_status = Column(String(32), nullable=False, comment="Next TaskStatus value; empty for trace-only rows.")
    progress = Column(Integer, nullable=False, default=0, comment="Task progress snapshot from 0 to 100.")
    stage = Column(String(64), nullable=False, default="", comment="Pipeline stage that emitted this history row.")
    event = Column(String(64), nullable=False, default="", comment="Domain event or trace event name.")
    message = Column(Text, nullable=True, comment="Human-readable status or trace message.")
    payload_json = Column(Text, nullable=True, comment="Structured event payload JSON.")
    change_time = Column(String(32), nullable=False, comment="ISO timestamp when the status or trace event occurred.")
    operator_type = Column(String(32), nullable=False, default="", comment="Operator type, e.g. system, user, or worker.")
    operator_id = Column(String(64), nullable=False, default="", comment="Operator identifier when available.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the event.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the history row was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the history row was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizTaskAttempt(Base):
    __tablename__ = "biz_task_attempts"
    __table_args__ = (
        CheckConstraint("attempt_no >= 1", name="ck_biz_task_attempts_attempt_no_positive"),
        CheckConstraint(
            "trigger_type in ('create', 'retry', 'continue', 'recover')",
            name="ck_biz_task_attempts_trigger_type",
        ),
        CheckConstraint(
            "status in ('CREATED', 'PENDING', 'QUEUED', 'RUNNING', 'FINISHED', 'FAILED', 'TERMINATED', 'PAUSED', 'REMOVED')",
            name="ck_biz_task_attempts_status",
        ),
        CheckConstraint("resume_from_clip_index >= 0", name="ck_biz_task_attempts_resume_clip_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_task_attempts_is_deleted"),
        Index("ix_biz_task_attempts_task_status", "task_id", "status", "is_deleted"),
        Index("ix_biz_task_attempts_queue_status", "queue_name", "status", "queue_entered_at"),
        {"comment": "Execution attempt for a task, including queue ownership and retry trigger metadata."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_attempt_id = Column(String(64), nullable=False, unique=True, comment="Public stable attempt identifier.")
    task_id = Column(String(64), nullable=False, comment="Parent biz_tasks.task_id.")
    attempt_no = Column(Integer, nullable=False, comment="Monotonic attempt number within the task.")
    trigger_type = Column(String(32), nullable=False, default="", comment="AttemptTriggerType enum value.")
    status = Column(String(32), nullable=False, comment="AttemptStatus enum value; PENDING is accepted for legacy queue rows.")
    queue_name = Column(String(64), nullable=False, default="", comment="Logical queue name claimed by the attempt.")
    worker_instance_id = Column(String(64), nullable=False, default="", comment="Worker instance currently or last responsible.")
    queue_entered_at = Column(String(32), nullable=True, comment="ISO timestamp when the attempt entered the queue.")
    queue_left_at = Column(String(32), nullable=True, comment="ISO timestamp when the attempt left the queue.")
    claimed_at = Column(String(32), nullable=True, comment="ISO timestamp when a worker claimed the attempt.")
    started_at = Column(String(32), nullable=True, comment="ISO timestamp when execution started.")
    finished_at = Column(String(32), nullable=True, comment="ISO timestamp when execution reached a terminal state.")
    resume_from_stage = Column(String(64), nullable=False, default="", comment="Stage name used for resume/recover attempts.")
    resume_from_clip_index = Column(Integer, nullable=False, default=0, comment="Clip index used for resume/recover attempts.")
    failure_code = Column(String(64), nullable=False, default="", comment="Machine-readable attempt failure code.")
    failure_message = Column(Text, nullable=True, comment="Human-readable attempt failure message.")
    payload_json = Column(Text, nullable=False, default="{}", comment="Attempt execution payload JSON.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the attempt.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the attempt was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the attempt was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizTaskStageRun(Base):
    __tablename__ = "biz_task_stage_runs"
    __table_args__ = (
        CheckConstraint("status in ('RUNNING', 'COMPLETED', 'FAILED')", name="ck_biz_task_stage_runs_status"),
        CheckConstraint("stage_seq >= 0", name="ck_biz_task_stage_runs_stage_seq_non_negative"),
        CheckConstraint("clip_index >= 0", name="ck_biz_task_stage_runs_clip_index_non_negative"),
        CheckConstraint("duration_ms >= 0", name="ck_biz_task_stage_runs_duration_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_task_stage_runs_is_deleted"),
        Index("ix_biz_task_stage_runs_task_stage", "task_id", "stage_name", "clip_index", "is_deleted"),
        {"comment": "Execution record for one task pipeline stage or clip."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_stage_run_id = Column(String(64), nullable=False, unique=True, comment="Public stable stage run identifier.")
    task_id = Column(String(64), nullable=False, comment="Parent biz_tasks.task_id.")
    attempt_id = Column(String(64), nullable=False, default="", comment="Related task_attempt_id when available.")
    stage_name = Column(String(64), nullable=False, comment="Pipeline stage name.")
    stage_seq = Column(Integer, nullable=False, default=0, comment="Stage order within the task pipeline.")
    clip_index = Column(Integer, nullable=False, default=0, comment="Clip index for per-clip stages.")
    status = Column(String(32), nullable=False, comment="StageRunStatus enum value.")
    worker_instance_id = Column(String(64), nullable=False, default="", comment="Worker instance that produced this stage run.")
    started_at = Column(String(32), nullable=False, comment="ISO timestamp when the stage run started.")
    finished_at = Column(String(32), nullable=True, comment="ISO timestamp when the stage run finished.")
    duration_ms = Column(Integer, nullable=False, default=0, comment="Stage run duration in milliseconds.")
    input_summary_json = Column(Text, nullable=False, default="{}", comment="Condensed stage input summary JSON.")
    output_summary_json = Column(Text, nullable=False, default="{}", comment="Condensed stage output summary JSON.")
    error_code = Column(String(64), nullable=False, default="", comment="Machine-readable stage error code.")
    error_message = Column(Text, nullable=True, comment="Human-readable stage error message.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the stage run.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the stage run row was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the stage run row was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizTaskQueueEvent(Base):
    __tablename__ = "biz_task_queue_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('enqueued', 'claimed', 'completed', 'failed', 'removed', 're_enqueued')",
            name="ck_biz_task_queue_events_event_type",
        ),
        CheckConstraint("queue_position_hint >= 0", name="ck_biz_task_queue_events_position_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_task_queue_events_is_deleted"),
        Index("ix_biz_task_queue_events_task_time", "task_id", "event_time"),
        {"comment": "Append-only queue lifecycle events for task attempts."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_queue_event_id = Column(String(64), nullable=False, unique=True, comment="Public stable queue event identifier.")
    task_id = Column(String(64), nullable=False, comment="Parent biz_tasks.task_id.")
    attempt_id = Column(String(64), nullable=False, default="", comment="Related task_attempt_id when available.")
    queue_name = Column(String(64), nullable=False, default="", comment="Logical queue that emitted the event.")
    event_type = Column(String(32), nullable=False, comment="QueueEventType enum value.")
    worker_instance_id = Column(String(64), nullable=False, default="", comment="Related worker instance id when available.")
    queue_position_hint = Column(Integer, nullable=False, default=0, comment="Best-effort queue position hint.")
    payload_json = Column(Text, nullable=False, default="{}", comment="Structured queue event metadata JSON.")
    event_time = Column(String(32), nullable=False, comment="ISO timestamp when the queue event occurred.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the event.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the event row was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the event row was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizWorkerInstance(Base):
    __tablename__ = "biz_worker_instances"
    __table_args__ = (
        CheckConstraint("status in ('RUNNING', 'STOPPED', 'FAILED', 'STALE')", name="ck_biz_worker_instances_status"),
        CheckConstraint("process_id >= 0", name="ck_biz_worker_instances_process_id_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_worker_instances_is_deleted"),
        Index("ix_biz_worker_instances_status_heartbeat", "status", "last_heartbeat_at"),
        {"comment": "Runtime worker process registration and heartbeat state."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    worker_instance_id = Column(String(64), nullable=False, unique=True, comment="Public stable worker instance identifier.")
    worker_type = Column(String(64), nullable=False, comment="Worker type or pool name.")
    queue_name = Column(String(64), nullable=False, default="", comment="Logical queue served by this worker.")
    host_name = Column(String(255), nullable=False, default="", comment="Host name reported by the worker process.")
    process_id = Column(Integer, nullable=False, default=0, comment="Operating system process id when available.")
    status = Column(String(32), nullable=False, comment="WorkerStatus enum value.")
    started_at = Column(String(32), nullable=False, comment="ISO timestamp when the worker started.")
    last_heartbeat_at = Column(String(32), nullable=False, comment="ISO timestamp of the latest worker heartbeat.")
    stopped_at = Column(String(32), nullable=True, comment="ISO timestamp when the worker stopped.")
    metadata_json = Column(Text, nullable=False, default="{}", comment="Worker runtime metadata JSON.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the worker.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the worker row was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the worker row was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizTaskModelCall(Base):
    __tablename__ = "biz_task_model_calls"
    __table_args__ = (
        CheckConstraint("http_status >= 0", name="ck_biz_task_model_calls_http_status_non_negative"),
        CheckConstraint("response_status_code >= 0", name="ck_biz_task_model_calls_response_status_non_negative"),
        CheckConstraint("success in (0, 1)", name="ck_biz_task_model_calls_success"),
        CheckConstraint("latency_ms >= 0", name="ck_biz_task_model_calls_latency_non_negative"),
        CheckConstraint("duration_ms >= 0", name="ck_biz_task_model_calls_duration_non_negative"),
        CheckConstraint("input_tokens >= 0", name="ck_biz_task_model_calls_input_tokens_non_negative"),
        CheckConstraint("output_tokens >= 0", name="ck_biz_task_model_calls_output_tokens_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_task_model_calls_is_deleted"),
        Index("ix_biz_task_model_calls_task_stage", "task_id", "stage", "operation", "is_deleted"),
        Index("ix_biz_task_model_calls_provider_model", "provider", "resolved_model", "is_deleted"),
        {"comment": "Audit row for one provider/model invocation used by a task."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_model_call_id = Column(String(64), nullable=False, unique=True, comment="Public stable model call identifier.")
    task_id = Column(String(64), nullable=False, comment="Parent biz_tasks.task_id.")
    call_kind = Column(String(32), nullable=False, default="", comment="Call category, e.g. text, image, video, or material snapshot.")
    stage = Column(String(64), nullable=False, default="", comment="Pipeline stage that issued the call.")
    operation = Column(String(64), nullable=False, default="", comment="Operation name within the stage.")
    provider = Column(String(64), nullable=False, default="", comment="Configured provider key.")
    provider_model = Column(String(128), nullable=False, default="", comment="Provider-reported model identifier.")
    requested_model = Column(String(128), nullable=False, default="", comment="Model requested by task/workflow configuration.")
    resolved_model = Column(String(128), nullable=False, default="", comment="Final model selected after alias/provider resolution.")
    model_name = Column(String(128), nullable=False, default="", comment="Deprecated display model name. Prefer resolved_model.")
    model_alias = Column(String(128), nullable=False, default="", comment="Deprecated model alias. Prefer requested_model/resolved_model.")
    endpoint_host = Column(String(255), nullable=False, default="", comment="Remote endpoint host without secrets.")
    request_id = Column(String(64), nullable=False, default="", comment="Provider request identifier when available.")
    request_payload_json = Column(Text, nullable=False, default="{}", comment="Sanitized provider request payload JSON.")
    response_payload_json = Column(Text, nullable=False, default="{}", comment="Sanitized provider response payload JSON.")
    http_status = Column(Integer, nullable=False, default=0, comment="HTTP status code; 0 when unavailable.")
    response_status_code = Column(Integer, nullable=False, default=0, comment="Provider business status code; 0 when unavailable.")
    success = Column(Integer, nullable=False, default=0, comment="Success flag: 0 failed/unknown, 1 succeeded.")
    error_code = Column(String(64), nullable=False, default="", comment="Machine-readable provider error code.")
    error_message = Column(Text, nullable=True, comment="Human-readable provider error message.")
    latency_ms = Column(Integer, nullable=False, default=0, comment="Network or provider latency in milliseconds.")
    duration_ms = Column(Integer, nullable=False, default=0, comment="Total invocation duration in milliseconds.")
    input_tokens = Column(Integer, nullable=False, default=0, comment="Input token count when reported by the provider.")
    output_tokens = Column(Integer, nullable=False, default=0, comment="Output token count when reported by the provider.")
    started_at = Column(String(32), nullable=False, comment="ISO timestamp when the invocation started.")
    finished_at = Column(String(32), nullable=False, comment="ISO timestamp when the invocation finished.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the call.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the model call row was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the model call row was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizTaskResult(Base):
    __tablename__ = "biz_task_results"
    __table_args__ = (
        CheckConstraint("clip_index >= 0", name="ck_biz_task_results_clip_index_non_negative"),
        CheckConstraint("start_seconds >= 0", name="ck_biz_task_results_start_non_negative"),
        CheckConstraint("end_seconds >= 0", name="ck_biz_task_results_end_non_negative"),
        CheckConstraint("duration_seconds >= 0", name="ck_biz_task_results_duration_non_negative"),
        CheckConstraint("width >= 0", name="ck_biz_task_results_width_non_negative"),
        CheckConstraint("height >= 0", name="ck_biz_task_results_height_non_negative"),
        CheckConstraint("size_bytes >= 0", name="ck_biz_task_results_size_non_negative"),
        CheckConstraint("is_deleted in (0, 1)", name="ck_biz_task_results_is_deleted"),
        Index("ix_biz_task_results_task_type", "task_id", "result_type", "clip_index", "is_deleted"),
        {"comment": "Produced task output rows, including media paths and optional material references."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    task_result_id = Column(String(64), nullable=False, unique=True, comment="Public stable result identifier.")
    task_id = Column(String(64), nullable=False, comment="Parent biz_tasks.task_id.")
    result_type = Column(String(32), nullable=False, comment="Result type such as text, image, video, or video_join.")
    clip_index = Column(Integer, nullable=False, default=0, comment="Clip index for per-clip outputs.")
    title = Column(String(255), nullable=False, default="", comment="User-facing output title.")
    reason = Column(Text, nullable=False, default="", comment="Generation or selection reason for this result.")
    source_model_call_id = Column(String(64), nullable=False, default="", comment="biz_task_model_calls.task_model_call_id that produced this result.")
    material_asset_id = Column(String(64), nullable=False, default="", comment="Linked biz_material_assets.material_asset_id when persisted as an asset.")
    start_seconds = Column(Float, nullable=False, default=0.0, comment="Start timestamp within the produced media.")
    end_seconds = Column(Float, nullable=False, default=0.0, comment="End timestamp within the produced media.")
    duration_seconds = Column(Float, nullable=False, default=0.0, comment="Produced media duration in seconds.")
    preview_path = Column(String(512), nullable=False, default="", comment="Local or public preview path used by the UI.")
    download_path = Column(String(512), nullable=False, default="", comment="Local or public download path used by the UI.")
    width = Column(Integer, nullable=False, default=0, comment="Media width in pixels when known.")
    height = Column(Integer, nullable=False, default=0, comment="Media height in pixels when known.")
    mime_type = Column(String(64), nullable=False, default="", comment="Media MIME type when known.")
    size_bytes = Column(Integer, nullable=False, default=0, comment="Media size in bytes when known.")
    remote_url = Column(String(1024), nullable=False, default="", comment="Remote provider or object storage URL when available.")
    extra_json = Column(Text, nullable=True, comment="Additional result metadata JSON.")
    produced_at = Column(String(32), nullable=False, comment="ISO timestamp when the result was produced.")
    timezone_offset_minutes = Column(Integer, nullable=False, default=0, comment="Client timezone offset captured for the result.")
    create_time = Column(String(32), nullable=False, comment="ISO timestamp when the result row was created.")
    update_time = Column(String(32), nullable=False, comment="ISO timestamp when the result row was last updated.")
    is_deleted = Column(Integer, nullable=False, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")


class BizMaterialAsset(Base):
    __tablename__ = "biz_material_assets"
    __table_args__ = (
        CheckConstraint("(clip_index is null or clip_index >= 0)", name="ck_biz_material_assets_clip_index_non_negative"),
        CheckConstraint("(version_no is null or version_no >= 1)", name="ck_biz_material_assets_version_no_positive"),
        CheckConstraint("(selected_for_next is null or selected_for_next in (0, 1))", name="ck_biz_material_assets_selected_for_next"),
        CheckConstraint("(user_rating is null or user_rating between 1 and 5)", name="ck_biz_material_assets_user_rating"),
        CheckConstraint("(size_bytes is null or size_bytes >= 0)", name="ck_biz_material_assets_size_non_negative"),
        CheckConstraint("(duration_seconds is null or duration_seconds >= 0)", name="ck_biz_material_assets_duration_non_negative"),
        CheckConstraint("(width is null or width >= 0)", name="ck_biz_material_assets_width_non_negative"),
        CheckConstraint("(height is null or height >= 0)", name="ck_biz_material_assets_height_non_negative"),
        CheckConstraint("(has_audio is null or has_audio in (0, 1))", name="ck_biz_material_assets_has_audio"),
        CheckConstraint("(is_deleted is null or is_deleted in (0, 1))", name="ck_biz_material_assets_is_deleted"),
        Index("ix_biz_material_assets_owner_media", "owner_user_id", "media_type", "is_deleted"),
        Index("ix_biz_material_assets_task", "task_id", "asset_role", "is_deleted"),
        Index("ix_biz_material_assets_workflow_stage", "workflow_id", "stage_type", "clip_index", "is_deleted"),
        {"comment": "Inventory of uploaded and generated media assets. Location fields include legacy aliases."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    material_asset_id = Column(String(64), nullable=False, unique=True, comment="Public stable material asset identifier.")
    remark = Column(String(512), nullable=False, default="", comment="Operator remark; not used for core business logic.")
    owner_user_id = Column(Integer, nullable=False, comment="Owner sys_user.id.")
    task_id = Column(String(64), nullable=True, comment="Task that produced or imported this asset.")
    workflow_id = Column(String(64), nullable=True, comment="Workflow that produced or imported this asset.")
    source_task_id = Column(String(64), nullable=True, comment="Original source task id when this asset is derived from another task.")
    source_material_id = Column(String(64), nullable=True, comment="Original material_asset_id when this asset is derived from another asset.")
    asset_role = Column(String(32), nullable=True, comment="Role in the pipeline, e.g. source, keyframe, video, or final.")
    stage_type = Column(String(64), nullable=True, comment="Workflow stage type associated with this asset.")
    clip_index = Column(Integer, nullable=True, comment="Clip index for per-clip workflow assets.")
    version_no = Column(Integer, nullable=True, comment="Version number within a workflow stage and clip.")
    selected_for_next = Column(Integer, default=0, comment="Selection flag for feeding this asset to the next stage.")
    user_rating = Column(Integer, nullable=True, comment="User rating from 1 to 5.")
    rating_note = Column(Text, nullable=True, comment="Optional note attached to user_rating.")
    media_type = Column(String(32), nullable=True, comment="Media type such as image, video, audio, or text.")
    title = Column(String(255), nullable=True, comment="User-facing asset title.")
    origin_provider = Column(String(64), nullable=True, comment="Provider that generated or hosted the asset.")
    origin_model = Column(String(128), nullable=True, comment="Provider model that generated the asset.")
    remote_task_id = Column(String(64), nullable=True, comment="Provider-side generation task id.")
    remote_asset_id = Column(String(64), nullable=True, comment="Provider-side asset id.")
    original_file_name = Column(String(255), nullable=True, comment="Original uploaded file name.")
    stored_file_name = Column(String(255), nullable=True, comment="File name after local/object storage normalization.")
    file_ext = Column(String(32), nullable=True, comment="File extension without path.")
    storage_provider = Column(String(64), nullable=True, comment="Storage backend key, e.g. local or object storage provider.")
    mime_type = Column(String(64), nullable=True, comment="Media MIME type when known.")
    size_bytes = Column(Integer, nullable=True, comment="Media size in bytes when known.")
    sha256 = Column(String(64), nullable=True, comment="SHA-256 checksum for deduplication and integrity checks.")
    duration_seconds = Column(Float, nullable=True, comment="Media duration in seconds when applicable.")
    width = Column(Integer, nullable=True, comment="Media width in pixels when applicable.")
    height = Column(Integer, nullable=True, comment="Media height in pixels when applicable.")
    has_audio = Column(Integer, default=0, comment="Audio presence flag: 0 absent/unknown, 1 present.")
    local_storage_path = Column(String(512), nullable=True, comment="Canonical local storage path for new writes.")
    local_file_path = Column(String(512), nullable=True, comment="Legacy local path alias kept for compatibility.")
    public_url = Column(String(1024), nullable=True, comment="Canonical URL exposed to the frontend for new writes.")
    thumbnail_url = Column(String(1024), nullable=True, comment="Preview thumbnail URL when available.")
    third_party_url = Column(String(1024), nullable=True, comment="Legacy third-party provider URL alias.")
    remote_url = Column(String(1024), nullable=True, comment="Legacy remote URL alias kept for compatibility.")
    metadata_json = Column(Text, nullable=True, comment="Additional media metadata JSON.")
    captured_at = Column(String(32), nullable=True, comment="ISO timestamp when the asset was captured or generated.")
    timezone_offset_minutes = Column(Integer, nullable=True, comment="Client timezone offset captured for the asset.")
    create_time = Column(String(32), default=None, comment="ISO timestamp when the asset row was created.")
    update_time = Column(String(32), default=None, comment="ISO timestamp when the asset row was last updated.")
    is_deleted = Column(Integer, default=0, comment="Soft delete flag: 0 active, 1 deleted.")
