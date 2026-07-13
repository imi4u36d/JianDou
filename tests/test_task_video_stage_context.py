from __future__ import annotations

from backend.domain.task_record import TaskRecord
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_video_stage_context import TaskVideoStageContext


def _task() -> TaskRecord:
    return TaskRecord(
        id="task_video",
        owner_user_id=1,
        title="Video",
        task_type="video_generation",
        status="RENDERING",
        min_duration_seconds=5,
        execution_context={
            "plannedClipCount": 2,
            "videoSize": "1280*720",
            "clipFrameContexts": [
                {"clipIndex": 2, "scene": "second", "targetDurationSeconds": 8},
                {"clipIndex": 1, "scene": "first", "targetDurationSeconds": 6},
            ],
            "storyboardClips": [{"clipIndex": 1, "videoPrompt": "storyboard prompt"}],
        },
        outputs=[
            {
                "resultType": "video",
                "clipIndex": 1,
                "downloadUrl": "/clip-1.mp4",
            }
        ],
    )


def test_context_resolves_order_duration_prompt_and_resume_clip() -> None:
    context = TaskVideoStageContext(TaskExecutionRuntimeSupport(), None)
    task = _task()
    rows = context.clip_frame_contexts(task)

    assert [row["clipIndex"] for row in rows] == [1, 2]
    assert context.planned_clip_count(task, rows) == 2
    assert context.next_missing_clip_index(task) == 2
    assert context.duration_for_clip(task, rows[0], 1) == (6, 6, 6)
    assert context.video_prompt_for_clip(task, rows[0], 1) == "storyboard prompt"
    assert context.video_size(task) == "1280*720"


def test_context_updates_submitted_and_returned_video_metadata() -> None:
    context = TaskVideoStageContext(TaskExecutionRuntimeSupport(), None)
    task = _task()

    context.mark_clip_video_submitted(task, 2, "run_2")
    context.update_clip_video_context(task, 2, "run_2", "/clip-2.mp4", "/last.png", "provider")
    context.put_join_context(task, 2, "/joined.mp4")

    row = context.clip_frame_contexts(task)[1]
    assert context.submitted_video_run_id(task, {}, 2) == "run_2"
    assert row["videoOutputUrl"] == "/clip-2.mp4"
    assert row["returnedLastFrameUrl"] == "/last.png"
    assert task.execution_context["latestJoinClipIndices"] == [1, 2]
