from backend.domain.task_record import TaskRecord
from backend.services.task_query_presenters import task_detail, task_list_item


def _task() -> TaskRecord:
    task = TaskRecord(
        id="task-presenter",
        owner_user_id=7,
        task_type="video_generation",
        title="Presenter task",
        status="RENDERING",
        progress=60,
        creative_prompt="A rainy street",
        transcript_text="A" * 250,
        active_attempt_id="attempt-2",
    )
    task.attempts.extend([
        {"attemptId": "attempt-1", "resumeFromStage": "plan", "workerInstanceId": "old-worker"},
        {"attemptId": "attempt-2", "resumeFromStage": "render", "workerInstanceId": "worker-2"},
    ])
    task.outputs.append({"resultType": "video", "clipIndex": 1})
    return task


def test_task_list_item_uses_active_attempt_context() -> None:
    item = task_list_item(_task())

    assert item["id"] == "task-presenter"
    assert item["currentStage"] == "render"
    assert item["activeWorkerInstanceId"] == "worker-2"
    assert item["ownerUserId"] == 7


def test_task_detail_copies_aggregate_collections_and_limits_transcript_preview() -> None:
    task = _task()
    detail = task_detail(task)

    assert detail["outputs"] == [{"resultType": "video", "clipIndex": 1}]
    assert detail["outputs"] is not task.outputs
    assert len(detail["transcriptPreview"]) == 220
    assert detail["creativePrompt"] == "A rainy street"
