from __future__ import annotations

import pytest

from backend.domain.video_run_monitor import (
    assert_video_run_succeeded,
    is_video_run_active,
    is_video_run_successful,
    normalized_video_run_status,
    video_run_failure,
)


def test_normalized_video_run_status_handles_missing_and_case() -> None:
    assert normalized_video_run_status(None) == ""
    assert normalized_video_run_status({"status": " Running "}) == "running"


def test_video_run_status_sets_match_worker_polling_contract() -> None:
    assert is_video_run_active("pending")
    assert is_video_run_active("queued")
    assert is_video_run_active("RUNNING")
    assert is_video_run_active("processing")
    assert not is_video_run_active("submitted")

    assert is_video_run_successful("completed")
    assert is_video_run_successful("SUCCESS")
    assert is_video_run_successful("succeeded")
    assert not is_video_run_successful("failed")


def test_video_run_failure_extracts_error_message_from_result_first() -> None:
    failure = video_run_failure(
        {
            "id": "run_1",
            "result": {
                "error": "provider error",
                "metadata": {
                    "taskMessage": "metadata task message",
                    "message": "metadata message",
                },
            },
        },
        "failed",
    )

    assert failure.run_id == "run_1"
    assert failure.status == "failed"
    assert failure.message == "provider error"
    assert failure.to_exception_message() == (
        "video run did not complete successfully: runId=run_1, status=failed, error=provider error"
    )


def test_assert_video_run_succeeded_raises_with_metadata_fallback_message() -> None:
    with pytest.raises(RuntimeError, match="runId=run_2, status=failed, error=metadata task message"):
        assert_video_run_succeeded(
            {
                "id": "run_2",
                "result": {
                    "metadata": {
                        "taskMessage": "metadata task message",
                    },
                },
            },
            "failed",
        )


def test_assert_video_run_succeeded_allows_success_aliases() -> None:
    assert_video_run_succeeded({"id": "run_3"}, "completed")
    assert_video_run_succeeded({"id": "run_3"}, "success")
    assert_video_run_succeeded({"id": "run_3"}, "succeeded")
