from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.shared import first_non_blank, map_value, string_value

ACTIVE_VIDEO_RUN_STATUSES = frozenset({"pending", "running", "queued", "processing"})
SUCCESSFUL_VIDEO_RUN_STATUSES = frozenset({"completed", "success", "succeeded"})

# Error messages that indicate a permanent / non-retryable failure.
# When these substrings appear in a provider error message, polling should stop
# immediately rather than continuing to retry.
_PERMANENT_ERROR_MARKERS: tuple[str, ...] = (
    "quota",
    "额度",
    "billing",
    "账户",
    "account",
    "insufficient",
    "exceeded",
    "limit reached",
    "rate limit",
    "too many requests",
    "invalid api",
    "invalid key",
    "invalid token",
    "invalid credentials",
    "is invalid",
    "unauthorized",
    "authentication",
    "forbidden",
    "permission denied",
    "not allowed",
    "unsupported",
    "model not found",
    "model not available",
    "deprecated",
    "disabled",
    "suspended",
    "revoked",
)


def _find_nested_strings(payload: object, *keys: str) -> str:
    """Recursively search a dict/list for string values matching any key."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k.lower() in {key.lower() for key in keys}:
                return string_value(v)
        for v in payload.values():
            found = _find_nested_strings(v, *keys)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_nested_strings(item, *keys)
            if found:
                return found
    return ""


def is_permanent_provider_error(message: str, provider_response: object = None) -> bool:
    """Return True when the error message or provider response body indicates a
    permanent (non-retryable) error such as quota exceeded, billing issues, or
    authentication failures.

    Permanent errors should cause the caller to fail fast rather than retry.
    """
    normalized = (message or "").lower()
    if not normalized:
        return False
    for marker in _PERMANENT_ERROR_MARKERS:
        if marker in normalized:
            return True
    # Also check nested provider response body
    if provider_response is not None:
        body_text = _find_nested_strings(provider_response, "message", "error", "reason", "detail")
        body_lower = body_text.lower()
        for marker in _PERMANENT_ERROR_MARKERS:
            if marker in body_lower:
                return True
    return False

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
