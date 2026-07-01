from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TaskRecord:
    """In-memory write model for the task aggregate.

    Mirrors the Java TaskRecord class. All sub-collections are stored as
    list-of-dict in memory so the services can freely manipulate them before
    persisting via the repository.
    """

    # -- scalar fields -------------------------------------------------------
    id: str = ""
    owner_user_id: int | None = None
    task_type: str = "video_generation"
    title: str = ""
    status: str = ""
    progress: int = 0
    created_at: str = ""
    updated_at: str = ""
    source_file_name: str = ""
    aspect_ratio: str = ""
    min_duration_seconds: int = 8
    max_duration_seconds: int = 8
    retry_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    completed_output_count: int = 0
    current_attempt_no: int = 0
    has_transcript: bool = False
    has_timed_transcript: bool = False
    source_asset_count: int = 0
    editing_mode: str = ""
    is_queued: bool = False
    queue_position: int | None = None
    active_attempt_id: str = ""
    intro_template: str = ""
    outro_template: str = ""
    creative_prompt: str = ""
    task_seed: int | None = None
    effect_rating: int | None = None
    effect_rating_note: str = ""
    rated_at: str | None = None
    error_message: str = ""
    transcript_text: str = ""
    storyboard_script: str = ""

    # -- structured fields ---------------------------------------------------
    execution_context: dict[str, Any] = field(default_factory=dict)
    request_snapshot: dict[str, Any] = field(default_factory=dict)

    # -- sub-collections (in-memory, synced to DB on save) -------------------
    trace: list[dict[str, Any]] = field(default_factory=list)
    status_history: list[dict[str, Any]] = field(default_factory=list)
    attempts: list[dict[str, Any]] = field(default_factory=list)
    stage_runs: list[dict[str, Any]] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    materials: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    source_assets: list[dict[str, Any]] = field(default_factory=list)

    # -- mutation helpers ----------------------------------------------------

    def add_trace(self, row: dict[str, Any]) -> None:
        self.trace.append(row)

    def add_status_history(self, row: dict[str, Any]) -> None:
        self.status_history.append(row)

    def prepend_attempt(self, row: dict[str, Any]) -> None:
        self.attempts.insert(0, row)

    def add_stage_run(self, row: dict[str, Any]) -> None:
        self.stage_runs.append(row)

    def add_model_call(self, row: dict[str, Any]) -> None:
        _upsert_row(self.model_calls, row, "modelCallId")

    def add_material(self, row: dict[str, Any]) -> None:
        self.materials.append(row)

    def add_output(self, row: dict[str, Any]) -> None:
        rid = _string_value(row.get("resultId", row.get("id")))
        if not rid:
            self.outputs.append(row)
            return
        for i, existing in enumerate(self.outputs):
            existing_id = _string_value(existing.get("resultId", existing.get("id")))
            if rid == existing_id:
                self.outputs[i] = row
                return
        self.outputs.append(row)

    def add_source_asset(self, row: dict[str, Any]) -> None:
        self.source_assets.append(row)

    def set_active_attempt(self, attempt_id: str, attempt_no: int) -> None:
        self.active_attempt_id = attempt_id
        self.current_attempt_no = attempt_no

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()

    # -- view accessors (immutable-style, return same list) ------------------

    @property
    def attempts_view(self) -> list[dict[str, Any]]:
        return self.attempts

    @property
    def stage_runs_view(self) -> list[dict[str, Any]]:
        return self.stage_runs

    @property
    def trace_view(self) -> list[dict[str, Any]]:
        return self.trace

    @property
    def model_calls_view(self) -> list[dict[str, Any]]:
        return self.model_calls

    @property
    def materials_view(self) -> list[dict[str, Any]]:
        return self.materials

    @property
    def outputs_view(self) -> list[dict[str, Any]]:
        return self.outputs

    @property
    def source_assets_view(self) -> list[dict[str, Any]]:
        return self.source_assets

    def mutable_execution_context(self) -> dict[str, Any]:
        if self.execution_context is None:
            self.execution_context = {}
        return self.execution_context


# ---------------------------------------------------------------------------
# module-level helpers (mirrors the Java private static helpers)
# ---------------------------------------------------------------------------

def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _upsert_row(
    rows: list[dict[str, Any]],
    row: dict[str, Any] | None,
    id_key: str,
) -> None:
    """Insert or replace a row by its id key (e.g. modelCallId)."""
    if row is None:
        return
    rid = _string_value(row.get(id_key)) if id_key else ""
    if not rid:
        rows.append(row)
        return
    for i, existing in enumerate(rows):
        if rid == _string_value(existing.get(id_key)):
            rows[i] = row
            return
    rows.append(row)
