"""Task aggregate: a read-model snapshot combining a task with its sub-collections.

Mirrors the Java TaskAggregate record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.domain.enums import TaskStatus
from backend.domain.task_attempt_snapshot import TaskAttemptSnapshot
from backend.domain.task_stage_run_snapshot import TaskStageRunSnapshot


@dataclass
class TaskAggregate:
    """Full task aggregate combining the task row with attempts and stage runs.

    Mirrors the Java TaskAggregate record.  Used as the return type for
    query-oriented operations that need the complete task state.
    """

    task_id: str = ""
    task_type: str = ""
    title: str = ""
    description: str = ""
    aspect_ratio: str = ""
    min_duration_seconds: int = 0
    max_duration_seconds: int = 0
    output_count: int = 0
    source_primary_asset_id: str = ""
    source_file_name: str = ""
    source_asset_ids: list[str] = field(default_factory=list)
    source_file_names: list[str] = field(default_factory=list)
    request_payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    intro_template: str = ""
    outro_template: str = ""
    creative_prompt: str = ""
    model_provider: str = ""
    execution_mode: str = ""
    editing_mode: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    error_code: str = ""
    error_message: str = ""
    plan_json: str = ""
    retry_count: int = 0
    timezone_offset_minutes: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    attempts: list[TaskAttemptSnapshot] = field(default_factory=list)
    stage_runs: list[TaskStageRunSnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Defensive copies for mutable collections
        if self.source_asset_ids is None:
            self.source_asset_ids = []
        if self.source_file_names is None:
            self.source_file_names = []
        if self.request_payload is None:
            self.request_payload = {}
        if self.context is None:
            self.context = {}
        if self.attempts is None:
            self.attempts = []
        if self.stage_runs is None:
            self.stage_runs = []
