"""Worker instance record construction for task execution."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import WorkerStatus
from backend.shared import now_iso, string_value


class TaskWorkerRegistry:
    """Create heartbeat rows while preserving existing worker metadata."""

    def upsert(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        now = now_iso()
        return {
            "workerInstanceId": worker_instance_id,
            "workerType": worker_type,
            "queueName": "default",
            "hostName": "",
            "processId": 0,
            "status": status,
            "startedAt": now,
            "lastHeartbeatAt": now,
            "stoppedAt": "",
            "metadata": metadata if metadata is not None else {},
        }

    def touch(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any] | None,
        existing_instance: dict[str, Any] | None,
    ) -> dict[str, Any]:
        now = now_iso()
        started_at = string_value(existing_instance.get("startedAt", now)) if existing_instance else now
        return {
            "workerInstanceId": worker_instance_id,
            "workerType": worker_type,
            "queueName": (
                string_value(existing_instance.get("queueName", "default"))
                if existing_instance
                else "default"
            ),
            "hostName": string_value(existing_instance.get("hostName", "")) if existing_instance else "",
            "processId": existing_instance.get("processId", 0) if existing_instance else 0,
            "status": status,
            "startedAt": started_at,
            "lastHeartbeatAt": now,
            "stoppedAt": (
                now
                if status in (WorkerStatus.STOPPED.value, WorkerStatus.FAILED.value)
                else string_value(existing_instance.get("stoppedAt", ""))
                if existing_instance
                else ""
            ),
            "metadata": (
                metadata
                if metadata is not None
                else (existing_instance.get("metadata", {}) if existing_instance else {})
            ),
        }
