from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import logging

from ai_cut_shared.schemas import TaskTraceEvent
from ai_cut_shared.utils import truncate_text, utcnow


logger = logging.getLogger("ai_cut.task_trace")


def _sanitize_value(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            return truncate_text(value, 3000)
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _sanitize_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_value(item) for item in value]
    return truncate_text(str(value), 1000)


@dataclass
class TaskTraceWriter:
    task_id: str
    trace_path: Path

    def log(
        self,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, object] | None = None,
        level: str = "INFO",
    ) -> None:
        entry = TaskTraceEvent(
            timestamp=utcnow().isoformat(),
            level=level.upper(),
            stage=stage,
            event=event,
            message=truncate_text(message, 1000) or "",
            payload=_sanitize_value(payload or {}) or {},
        )
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.model_dump(), ensure_ascii=False) + "\n")
        logger.info(
            "[task=%s] [%s] %s: %s",
            self.task_id,
            entry.stage,
            entry.event,
            entry.message,
        )


def read_task_trace(trace_path: Path, limit: int = 500) -> list[TaskTraceEvent]:
    if not trace_path.exists():
        return []
    events: list[TaskTraceEvent] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            events.append(TaskTraceEvent.model_validate_json(line))
        except Exception:
            continue
    return events
