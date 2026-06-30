"""Generation run constants and status helpers."""

from __future__ import annotations

DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-2"


class GenerationRunKinds:
    PROBE = "probe"
    SCRIPT = "script"
    SCRIPT_ADJUST = "script_adjust"
    IMAGE = "image"
    VIDEO = "video"


class GenerationRunStatuses:
    QUEUED = "queued"
    SUBMITTED = "submitted"
    RUNNING = "running"
    ACCEPTED = "accepted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPLETED = "completed"
    SUCCESS = "success"

    _ACTIVE = {ACCEPTED, QUEUED, SUBMITTED, RUNNING}
    _SUCCESSFUL = {SUCCEEDED, COMPLETED, SUCCESS}

    @classmethod
    def is_active(cls, raw: str) -> bool:
        return cls._normalize(raw) in cls._ACTIVE

    @classmethod
    def is_successful(cls, raw: str) -> bool:
        return cls._normalize(raw) in cls._SUCCESSFUL

    @classmethod
    def _normalize(cls, raw: str) -> str:
        return raw.strip().lower() if raw else ""


class GenerationModelKinds:
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
