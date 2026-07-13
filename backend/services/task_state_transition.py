"""Task state transition value object and fluent builder."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import AttemptStatus


class TaskStateTransition:
    """Value object for a task state transition.

    Mirrors Java TaskStateTransition with builder pattern.
    """

    def __init__(
        self,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
        attempt_status: str = "",
        attempt_error_message: str = "",
        updates_attempt: bool = False,
    ) -> None:
        self._next_status = next_status
        self._progress = progress
        self._stage = stage
        self._event = event
        self._message = message
        self._level = level
        self._payload = payload if payload is not None else {}
        self._attempt_status = attempt_status
        self._attempt_error_message = attempt_error_message
        self._updates_attempt = updates_attempt

    @property
    def next_status(self) -> str:
        return self._next_status

    @property
    def progress(self) -> int:
        return self._progress

    @property
    def stage(self) -> str:
        return self._stage

    @property
    def event(self) -> str:
        return self._event

    @property
    def message(self) -> str:
        return self._message

    @property
    def level(self) -> str:
        return self._level

    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    @property
    def attempt_status(self) -> str:
        return self._attempt_status

    @property
    def attempt_status_enum(self) -> AttemptStatus:
        result = AttemptStatus._missing_(self._attempt_status)
        return result if result is not None else AttemptStatus.CREATED

    @property
    def attempt_error_message(self) -> str:
        return self._attempt_error_message

    @property
    def updates_attempt(self) -> bool:
        return self._updates_attempt

    @staticmethod
    def info(
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransitionBuilder:
        return TaskStateTransitionBuilder(next_status, progress, stage, event, message, "INFO", payload)

    @staticmethod
    def warn(
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransitionBuilder:
        return TaskStateTransitionBuilder(next_status, progress, stage, event, message, "WARN", payload)

    @staticmethod
    def error(
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransitionBuilder:
        return TaskStateTransitionBuilder(next_status, progress, stage, event, message, "ERROR", payload)


class TaskStateTransitionBuilder:
    """Builder for TaskStateTransition with attempt chaining."""

    def __init__(
        self,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> None:
        self._next_status = next_status
        self._progress = progress
        self._stage = stage
        self._event = event
        self._message = message
        self._level = level
        self._payload = payload if payload is not None else {}

    def with_attempt(
        self,
        attempt_status: AttemptStatus | str,
        error_message: str = "",
    ) -> TaskStateTransition:
        if isinstance(attempt_status, AttemptStatus):
            status_str = attempt_status.value
        else:
            status_str = attempt_status
        return TaskStateTransition(
            next_status=self._next_status,
            progress=self._progress,
            stage=self._stage,
            event=self._event,
            message=self._message,
            level=self._level,
            payload=self._payload,
            attempt_status=status_str,
            attempt_error_message=error_message or "",
            updates_attempt=True,
        )

    def build(self) -> TaskStateTransition:
        return TaskStateTransition(
            next_status=self._next_status,
            progress=self._progress,
            stage=self._stage,
            event=self._event,
            message=self._message,
            level=self._level,
            payload=self._payload,
        )
