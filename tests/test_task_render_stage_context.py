from backend.domain.task_record import TaskRecord
from backend.services.task_render_stage_context import TaskRenderStageContext


def _task() -> TaskRecord:
    return TaskRecord(
        id="task_render_context",
        owner_user_id=7,
        title="Render",
        execution_context={
            "clipImageRunIds": ["run_1", "run_1"],
            "videoRunId": "old_video",
            "resumeRenderFromClipIndex": 2,
        },
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def test_complete_merges_image_runs_and_clears_video_resume_state() -> None:
    task = _task()
    context = TaskRenderStageContext()

    context.complete(task, ["run_2", "run_1"], 3)

    assert set(task.execution_context["clipImageRunIds"]) == {"run_1", "run_2"}
    assert task.execution_context["clipVideoRunIds"] == []
    assert "videoRunId" not in task.execution_context
    assert "resumeRenderFromClipIndex" not in task.execution_context
    assert task.completed_output_count == 3


def test_put_clip_frame_replaces_same_clip_and_sorts_rows() -> None:
    task = _task()
    task.execution_context["clipFrameContexts"] = [
        {"clipIndex": 2, "value": "old"},
        {"clipIndex": 1, "value": "first"},
    ]
    context = TaskRenderStageContext()

    context.put_clip_frame(task, 2, {"clipIndex": 2, "value": "new"})

    assert task.execution_context["clipFrameContexts"] == [
        {"clipIndex": 1, "value": "first"},
        {"clipIndex": 2, "value": "new"},
    ]
