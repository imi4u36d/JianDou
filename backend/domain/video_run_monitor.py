from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.shared import first_non_blank, map_value, string_value

ACTIVE_VIDEO_RUN_STATUSES = frozenset({"pending", "running", "queued", "processing"})
SUCCESSFUL_VIDEO_RUN_STATUSES = frozenset({"completed", "success", "succeeded"})

def normalized_video_run_status(run: dict[str, Any] | None) -> str:
    return string_value((run or {}).get("status")).lower()

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
    result = map_value((run or {}).get("result"))
    metadata = map_value(result.get("metadata"))
    message = first_non_blank(
        string_value(result.get("error")),
        string_value(metadata.get("taskMessage")),
        string_value(metadata.get("message")),
    )
    return VideoRunFailure(
        run_id=string_value((run or {}).get("id")),
        status=status,
        message=message,
    )

def assert_video_run_succeeded(run: dict[str, Any] | None, status: str) -> None:
    if is_video_run_successful(status):
        return
    raise RuntimeError(video_run_failure(run, status).to_exception_message())
