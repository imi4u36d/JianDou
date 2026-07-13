from __future__ import annotations

from types import SimpleNamespace

from backend.domain.task_record import TaskRecord
from backend.services.stubs import GenerationApplicationServiceStub
from backend.services.task_worker_pipeline_context import (
    build_character_definition_context,
    generation_result_map,
    put_execution_context,
)
from backend.services.task_worker_service import TaskWorkerPipelineHandler


def _task() -> TaskRecord:
    return TaskRecord(id="task_1", title="Task", status="PENDING", execution_context={})


def test_execution_context_normalizes_empty_values() -> None:
    task = _task()

    put_execution_context(task, "model", " video-model ")
    put_execution_context(task, "empty", "   ")
    put_execution_context(task, "model", None)

    assert task.execution_context == {}
    assert generation_result_map({"result": {"id": "run_1"}}) == {"id": "run_1"}
    assert generation_result_map({"result": "invalid"}) == {}


def test_character_context_is_a_pure_serializable_projection() -> None:
    rows = build_character_definition_context(
        [SimpleNamespace(name=" Hero ", appearance=" coat ", definition=" lead ")]
    )

    assert rows == [
        {
            "characterIndex": 1,
            "name": "Hero",
            "appearance": "coat",
            "definition": "lead",
        }
    ]


def test_worker_composition_shares_pipeline_dependencies() -> None:
    handler = TaskWorkerPipelineHandler(
        generation_application_service=GenerationApplicationServiceStub()
    )

    assert handler._render_stage_service._runtime_support is handler._runtime_support
    assert handler._video_stage_service._runtime_support is handler._runtime_support
    assert handler._render_stage_service._status_stage_service is handler._status_stage_service
