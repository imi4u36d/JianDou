"""Writes task/workflow diagnostic events to the application log.

Mirrors the Java StructuredApplicationLogger (task/observability).
Events are also retained in an in-memory ring buffer for recent-trace queries.
"""
from __future__ import annotations

import collections
import hashlib
import json
import logging
import re
import threading
from datetime import datetime, timezone
from typing import Any

from app.services.provider_payload_sanitizer import ProviderPayloadSanitizer

_logger_task_trace = logging.getLogger("jiandou.task.trace")
_logger_workflow_trace = logging.getLogger("jiandou.workflow.trace")

MAX_RECENT_EVENTS = 1000


class StructuredApplicationLogger:
    """Writes task/workflow diagnostic events to the application log.

    Mirrors the Java StructuredApplicationLogger.  All methods are static;
    the class is never instantiated.
    """

    _lock = threading.Lock()
    _recent_events: collections.deque[dict[str, Any]] = collections.deque(maxlen=MAX_RECENT_EVENTS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def log_task_trace(task_id: str, trace: dict[str, Any]) -> None:
        """Write a task trace event to the log."""
        safe_trace = trace if trace is not None else {}
        event = StructuredApplicationLogger._task_trace_event(task_id, safe_trace)
        StructuredApplicationLogger._remember(event)
        StructuredApplicationLogger._log(
            _logger_task_trace,
            str(event.get("level", "INFO")),
            event,
        )

    @staticmethod
    def log_workflow_event(
        owner_ref_id: str,
        module: str,
        stage: str,
        event_name: str,
        level: str,
        message: str,
        payload: dict[str, Any] | None,
    ) -> None:
        """Write a workflow diagnostic event to the log."""
        event = StructuredApplicationLogger._workflow_event(
            owner_ref_id, module, stage, event_name, level, message, payload,
        )
        StructuredApplicationLogger._remember(event)
        StructuredApplicationLogger._log(
            _logger_workflow_trace,
            str(event.get("level", "INFO")),
            event,
        )

    @staticmethod
    def list_recent_traces(
        task_id: str | None = None,
        stage: str | None = None,
        level: str | None = None,
        query_text: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return filtered recent structured trace events from the in-memory buffer."""
        resolved_limit = max(1, limit)
        with StructuredApplicationLogger._lock:
            snapshot = list(StructuredApplicationLogger._recent_events)

        rows: list[dict[str, Any]] = []
        for event in snapshot:
            if not StructuredApplicationLogger._matches(event, task_id, stage, level, query_text):
                continue
            rows.append(dict(event))
            if len(rows) >= resolved_limit:
                break
        return rows

    # ------------------------------------------------------------------
    # Event builders
    # ------------------------------------------------------------------

    @staticmethod
    def _task_trace_event(task_id: str, trace: dict[str, Any]) -> dict[str, Any]:
        return {
            "logType": "task_trace",
            "taskId": _str(task_id),
            "traceId": _first_non_blank(_str(trace.get("traceId")), ""),
            "timestamp": _first_non_blank(_str(trace.get("timestamp")), _now_iso()),
            "level": _normalize_level(_str(trace.get("level"))),
            "stage": _str(trace.get("stage")),
            "event": _str(trace.get("event")),
            "message": _str(trace.get("message")),
            "payload": ProviderPayloadSanitizer.sanitize(trace.get("payload", {})),
            "source": "python-api",
            "serviceName": "api-python",
        }

    @staticmethod
    def _workflow_event(
        owner_ref_id: str,
        module: str,
        stage: str,
        event_name: str,
        level: str,
        message: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "logType": "workflow_event",
            "taskId": _str(owner_ref_id),
            "ownerRefId": _str(owner_ref_id),
            "traceId": "",
            "timestamp": _now_iso(),
            "level": _normalize_level(level),
            "module": _str(module),
            "stage": _str(stage),
            "event": _str(event_name),
            "message": _str(message),
            "payload": ProviderPayloadSanitizer.sanitize(payload if payload is not None else {}),
            "source": "python-api",
            "serviceName": "api-python",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log(logger: logging.Logger, raw_level: str, event: dict[str, Any]) -> None:
        message = json.dumps(event, ensure_ascii=False, default=str)
        normalized = _normalize_level(raw_level)
        if normalized == "ERROR":
            logger.error(message)
        elif normalized == "WARN":
            logger.warning(message)
        elif normalized == "DEBUG":
            logger.debug(message)
        elif normalized == "TRACE":
            logger.log(logging.DEBUG - 5, message)  # custom TRACE level
        else:
            logger.info(message)

    @staticmethod
    def _remember(event: dict[str, Any]) -> None:
        with StructuredApplicationLogger._lock:
            StructuredApplicationLogger._recent_events.appendleft(dict(event))

    @staticmethod
    def _matches(
        event: dict[str, Any],
        task_id: str | None,
        stage: str | None,
        level: str | None,
        query_text: str | None,
    ) -> bool:
        if task_id and _str(task_id).strip() and _str(event.get("taskId")) != _str(task_id).strip():
            return False
        if stage and _str(stage).strip() and _str(event.get("stage")) != _str(stage).strip():
            return False
        if level and _str(level).strip() and _str(event.get("level")).upper() != _str(level).strip().upper():
            return False
        if not query_text or not query_text.strip():
            return True
        query = query_text.strip().lower()
        return (
            query in _str(event.get("taskId")).lower()
            or query in _str(event.get("traceId")).lower()
            or query in _str(event.get("event")).lower()
            or query in _str(event.get("message")).lower()
            or query in _str(event.get("stage")).lower()
        )


# ---------------------------------------------------------------------------
# Module-level utility functions
# ---------------------------------------------------------------------------

def _str(value: Any) -> str:
    return "" if value is None else str(value)


def _normalize_level(raw_level: str | None) -> str:
    normalized = (raw_level or "").strip().upper()
    return normalized if normalized else "INFO"


def _first_non_blank(value: str, fallback: str) -> str:
    return value if value and value.strip() else fallback


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
