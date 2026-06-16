"""Immutable snapshot of a task stage run record.

Mirrors the Java TaskStageRunSnapshot record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskStageRunSnapshot:
    """Immutable snapshot of a task stage run.

    Mirrors the Java TaskStageRunSnapshot record. Timestamps are stored as
    ISO-format strings (or None) to keep the snapshot serializable.
    """

    stage_run_id: str = ""
    task_id: str = ""
    attempt_id: str = ""
    stage_name: str = ""
    stage_seq: int = 0
    clip_index: int = 0
    status: str = ""
    worker_instance_id: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        # Ensure dicts are copies
        if self.input_summary is None:
            object.__setattr__(self, "input_summary", {})
        if self.output_summary is None:
            object.__setattr__(self, "output_summary", {})

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> TaskStageRunSnapshot:
        """Build a snapshot from a persistence row dict."""
        return cls(
            stage_run_id=str(row.get("stageRunId", "") or ""),
            task_id=str(row.get("taskId", "") or ""),
            attempt_id=str(row.get("attemptId", "") or ""),
            stage_name=str(row.get("stageName", "") or ""),
            stage_seq=int(row.get("stageSeq", 0) or 0),
            clip_index=int(row.get("clipIndex", 0) or 0),
            status=str(row.get("status", "") or ""),
            worker_instance_id=str(row.get("workerInstanceId", "") or ""),
            started_at=row.get("startedAt"),
            finished_at=row.get("finishedAt"),
            duration_ms=int(row.get("durationMs", 0) or 0),
            input_summary=dict(row.get("inputSummary") or {}),
            output_summary=dict(row.get("outputSummary") or {}),
            error_code=str(row.get("errorCode", "") or ""),
            error_message=str(row.get("errorMessage", "") or ""),
        )
