from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.domain.task_diagnosis import TaskDiagnosisRules
from backend.services.task_diagnosis_service import TaskDiagnosisService

pytestmark = pytest.mark.domain


def _task(**overrides):
    values = {
        "id": "task_diagnosis",
        "title": "Diagnosis",
        "status": "RENDERING",
        "error_message": None,
        "is_queued": True,
        "queue_position": 2,
        "execution_context": {"plannedClipCount": 3},
        "outputs": [
            {
                "resultType": "video",
                "clipIndex": 1,
                "downloadUrl": "clip-1.mp4",
                "extra": {"hasAudio": True, "lastFrameUrl": "frame-1.png"},
            },
            {
                "resultType": "video",
                "clipIndex": 3,
                "downloadUrl": "clip-3.mp4",
                "extra": {"hasAudio": True},
            },
        ],
        "attempts": [],
        "trace": [],
        "stage_runs": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_diagnosis_service_delegates_a_normalized_snapshot_to_rules() -> None:
    class RecordingRules(TaskDiagnosisRules):
        snapshot = None

        def diagnose(self, snapshot):
            self.snapshot = snapshot
            return {"status": snapshot.status}

    rules = RecordingRules()
    result = TaskDiagnosisService(rules).diagnose(_task(monitoring={"resumeFromStage": "join"}))

    assert result == {"status": "RENDERING"}
    assert rules.snapshot is not None
    assert rules.snapshot.rendered_clip_indices == [1, 3]
    assert rules.snapshot.monitoring["resumeFromStage"] == "join"


def test_diagnosis_rules_report_continuity_and_join_risks() -> None:
    service = TaskDiagnosisService()

    diagnosis = service.diagnose(_task())

    assert diagnosis["severity"] == "medium"
    assert [finding["code"] for finding in diagnosis["findings"]] == ["missing_clips", "join_missing"]
    assert diagnosis["continuity"] == {
        "plannedClipCount": 3,
        "renderedClipIndices": [1, 3],
        "contiguousRenderedClipCount": 1,
        "missingClipIndices": [2],
        "latestRenderedClipIndex": 3,
        "latestJoinName": "",
        "latestJoinClipIndex": 0,
        "latestJoinClipIndices": [],
    }
    assert diagnosis["recovery"]["recommendedAction"].startswith("Check join worker trace")


def test_diagnosis_rules_preserve_failed_and_healthy_outcomes() -> None:
    service = TaskDiagnosisService()
    failed = service.diagnose(_task(status="FAILED", error_message="provider failed"))
    healthy = service.diagnose(
        _task(
            status="COMPLETED",
            execution_context={"plannedClipCount": 1},
            outputs=[
                {
                    "resultType": "video",
                    "clipIndex": 1,
                    "downloadUrl": "clip.mp4",
                    "extra": {"hasAudio": True},
                }
            ],
        )
    )

    assert failed["severity"] == "high"
    assert failed["findings"][0]["detail"] == "provider failed"
    assert service.severity(_task(status="FAILED")) == "high"
    assert healthy["findings"][0]["code"] == "healthy"
    assert healthy["severity"] == "info"
