from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ACTIVE_VIDEO_RUN_STATUSES = frozenset({"pending", "running", "queued", "processing"})
SUCCESSFUL_VIDEO_RUN_STATUSES = frozenset({"completed", "success", "succeeded"})


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _map_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_non_blank(*values: str | None) -> str:
    for value in values:
        if value is not None and value.strip():
            return value.strip()
    return ""


def normalized_video_run_status(run: dict[str, Any] | None) -> str:
    return _string_value((run or {}).get("status")).lower()


def is_video_run_active(status: str) -> bool:
    return status.lower() in ACTIVE_VIDEO_RUN_STATUSES


def is_video_run_successful(status: str) -> bool:
    return status.lower() in SUCCESSFUL_VIDEO_RUN_STATUSES


@dataclass(frozen=True)
class VideoRunFailure:
    run_id: str
    status: str
    message: str

    def to_exception_message(self) -> str:
        suffix = f", error={self.message}" if self.message else ""
        return f"video run did not complete successfully: runId={self.run_id}, status={self.status}{suffix}"


def video_run_failure(run: dict[str, Any] | None, status: str) -> VideoRunFailure:
    result = _map_value((run or {}).get("result"))
    metadata = _map_value(result.get("metadata"))
    message = _first_non_blank(
        _string_value(result.get("error")),
        _string_value(metadata.get("taskMessage")),
        _string_value(metadata.get("message")),
    )
    return VideoRunFailure(
        run_id=_string_value((run or {}).get("id")),
        status=status,
        message=message,
    )


def assert_video_run_succeeded(run: dict[str, Any] | None, status: str) -> None:
    if is_video_run_successful(status):
        return
    raise RuntimeError(video_run_failure(run, status).to_exception_message())
