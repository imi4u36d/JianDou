"""Joined-video scheduling facade."""

from __future__ import annotations

import uuid

from backend.infrastructure.task_repository import TaskRepository
from backend.services.stubs import LocalMediaArtifactServiceStub
from backend.services.task_artifact_assembler import _TaskArtifactNaming
from backend.services.task_execution_coordinator import TaskExecutionCoordinator


class JoinOutputService:
    JOIN_OUTPUT_CLIP_INDEX_BASE = 10000

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        local_media_artifact_service: LocalMediaArtifactServiceStub | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        self._local_media_artifact_service = local_media_artifact_service
        self._join_worker_instance_id = f"spring_join_worker_{uuid.uuid4().hex}"

    def schedule_join(self, task_id: str, end_clip_index: int) -> None:
        """Schedule joining when the concrete deployment provides an executor."""

    def _join_output_name(self, end_clip_index: int) -> str:
        return "join-1" if end_clip_index <= 1 else _TaskArtifactNaming.join_name(end_clip_index)
