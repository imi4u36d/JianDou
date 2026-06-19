from __future__ import annotations

from backend.domain.task_monitoring import missing_clip_indices, task_monitoring_snapshot, task_outputs
from backend.domain.task_record import TaskRecord


def test_task_monitoring_snapshot_matches_worker_view_contract() -> None:
    task = TaskRecord(
        id="task_monitoring",
        execution_context={"plannedClipCount": 3},
        outputs=[
            {"resultType": "image", "clipIndex": 1, "downloadUrl": "ignored.png"},
            {"resultType": "video_clip", "clipIndex": 1, "downloadUrl": "clip-1.mp4"},
            {"resultType": "video_generation", "clipIndex": 2, "previewUrl": "clip-2-preview.mp4"},
            {
                "resultType": "video_join",
                "clipIndex": 10002,
                "downloadUrl": "joined.mp4",
                "extra": {"joinName": "join-2", "clipIndices": [1, 2]},
            },
        ],
    )

    monitoring = task_monitoring_snapshot(task)

    assert monitoring["plannedClipCount"] == 3
    assert monitoring["renderedClipCount"] == 2
    assert monitoring["renderedClipIndices"] == [1, 2]
    assert monitoring["contiguousRenderedClipCount"] == 2
    assert monitoring["missingClipIndices"] == [3]
    assert monitoring["latestVideoOutputUrl"] == "clip-2-preview.mp4"
    assert monitoring["latestJoinName"] == "join-2"
    assert monitoring["latestJoinOutputUrl"] == "joined.mp4"
    assert monitoring["latestJoinClipIndices"] == [1, 2]


def test_task_monitoring_snapshot_resolves_stage_and_worker_from_attempts_and_trace() -> None:
    task = TaskRecord(
        id="task_monitoring_attempt",
        execution_context={"clipPrompts": ["one", "two"]},
        active_attempt_id="attempt_2",
        attempts=[
            {"attemptId": "attempt_1", "startedAt": "2026-01-01T00:00:00+00:00", "workerInstanceId": "worker_old"},
            {
                "attemptId": "attempt_2",
                "startedAt": "2026-01-01T00:01:00+00:00",
                "resumeFromStage": "render",
                "workerInstanceId": "worker_active",
                "status": "RUNNING",
            },
        ],
        trace=[{"timestamp": "2026-01-01T00:02:00+00:00", "stage": "trace_stage"}],
    )

    monitoring = task_monitoring_snapshot(task)

    assert monitoring["plannedClipCount"] == 2
    assert monitoring["currentStage"] == "render"
    assert monitoring["activeWorkerInstanceId"] == "worker_active"
    assert monitoring["activeAttemptStatus"] == "RUNNING"
    assert monitoring["resumeFromStage"] == "render"
    assert monitoring["resumeFromClipIndex"] == 1


def test_task_outputs_and_missing_clip_indices_ignore_invalid_shapes() -> None:
    class TaskWithCallableOutputs:
        def outputs_view(self):
            return [{"resultType": "video", "clipIndex": 1}, "bad"]

    assert task_outputs(TaskWithCallableOutputs()) == [{"resultType": "video", "clipIndex": 1}]
    assert missing_clip_indices(4, [1, 3]) == [2, 4]
