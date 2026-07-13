from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_storyboard_preparation_service import TaskStoryboardPreparationService
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext


class _Shot:
    def sequential_index(self) -> int:
        return 1

    def shot_label(self) -> str:
        return "1"

    def scene(self) -> str:
        return "场景"

    def first_frame_prompt(self) -> str:
        return "首帧"

    def last_frame_prompt(self) -> str:
        return "尾帧"

    def motion(self) -> str:
        return "移动"

    def camera_movement(self) -> str:
        return "固定"

    def duration_hint(self) -> str:
        return "5秒"

    def image_prompt(self) -> str:
        return "图片提示词"

    def video_prompt(self) -> str:
        return "镜头提示词"


class _Planner:
    def build_storyboard_shot_plans(self, task: TaskRecord, markdown: str) -> list[_Shot]:
        return [_Shot()]

    def extract_character_definitions(self, markdown: str) -> list[Any]:
        return []

    def resolve_requested_output_count(self, task: TaskRecord, clip_count: int) -> int:
        return clip_count

    def extract_storyboard_shot_duration_ranges(self, markdown: str) -> list[Any]:
        return []

    def build_clip_duration_plan(
        self,
        task: TaskRecord,
        duration_seconds: int,
        clip_count: int,
        markdown: str,
    ) -> list[list[int]]:
        return [[duration_seconds, duration_seconds, duration_seconds]]

    def normalize_clip_duration_plan(self, model: str, plan: list[list[int]]) -> list[list[int]]:
        return plan

    def request_snapshot_output_count(self, task: TaskRecord) -> dict[str, Any]:
        return {"auto": True}

    def build_clip_duration_plan_context(self, plan: list[list[int]], ranges: list[Any]) -> list[dict[str, Any]]:
        return [{"clipIndex": 1, "durationSeconds": plan[0][0]}]


class _Repository:
    def __init__(self) -> None:
        self.saved: list[TaskRecord] = []

    async def save(self, task: TaskRecord) -> None:
        self.saved.append(task)


class _StatusService:
    def update_status(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}


@pytest.mark.asyncio
async def test_reused_storyboard_builds_normalized_render_plan_without_model_call() -> None:
    repository = _Repository()
    generation = SimpleNamespace(create_run=lambda request: pytest.fail("model call should be skipped"))
    saved_results: list[dict[str, Any] | None] = []

    async def save_result(result: dict[str, Any] | None) -> None:
        saved_results.append(result)

    service = TaskStoryboardPreparationService(
        repository,  # type: ignore[arg-type]
        generation,
        TaskExecutionRuntimeSupport(),
        TaskExecutionArtifactAssembler(),
        _Planner(),
        _StatusService(),  # type: ignore[arg-type]
        TaskExecutionCoordinator(),
        save_result,
    )
    task = TaskRecord(
        id="task-1",
        title="复用分镜",
        storyboard_script="existing storyboard",
        request_snapshot={"videoModel": "video-1"},
        execution_context={},
    )

    result = await service.prepare(
        task,
        TaskWorkerExecutionContext("worker-1", "test", "queue"),
        duration_seconds=5,
        reuse_storyboard=True,
        completed_clip_count=0,
        render_start_index=1,
        requested_resume_stage="planning",
        requested_resume_clip_index=1,
    )

    assert result.script_run == {}
    assert len(result.shot_plans) == 1
    assert result.clip_duration_plan == [[5, 5, 5]]
    assert task.execution_context["plannedClipCount"] == 1
    assert task.execution_context["storyboardFormatVersion"] == "structured-md-v1"
    assert repository.saved == [task]
    assert len(saved_results) == 3
