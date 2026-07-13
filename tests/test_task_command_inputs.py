from __future__ import annotations

import pytest

from backend.domain.enums import AttemptTriggerType
from backend.domain.task_record import TaskRecord
from backend.services.task_command_inputs import (
    build_retry_payload,
    normalize_effect_rating,
    normalize_effect_rating_note,
    normalize_optional_seed,
    normalize_output_count,
    normalize_string_list,
    normalize_task_type,
)


def test_task_input_normalization_is_deterministic() -> None:
    assert normalize_string_list([" first ", "", "first", " second "]) == [
        "first",
        "second",
    ]
    assert normalize_task_type("generation", [" image.png "], None) == "image_to_image"
    assert normalize_task_type(None, None, "character_sheet") == "character_sheet"
    assert normalize_task_type(None, None, None) == "video_generation"
    assert normalize_output_count("auto") == {"auto": True}
    assert normalize_output_count({"count": "0"}) == {"auto": False, "count": 1}
    assert normalize_output_count("3") == {"auto": False, "count": 3}


def test_task_input_validation_rejects_invalid_scalar_values() -> None:
    with pytest.raises(ValueError, match="seed must be >= 0"):
        normalize_optional_seed(-1)
    with pytest.raises(ValueError, match="between 1 and 5"):
        normalize_effect_rating(6)
    with pytest.raises(ValueError, match="must not exceed 1000"):
        normalize_effect_rating_note("x" * 1001)


def test_retry_payload_preserves_contiguous_clip_resume_policy() -> None:
    task = TaskRecord(
        id="retry-policy",
        retry_count=2,
        storyboard_script="storyboard",
        outputs=[
            {"resultType": "video", "clipIndex": 1},
            {"resultType": "video", "clipIndex": 3},
        ],
    )

    assert build_retry_payload(task, AttemptTriggerType.RETRY) == {
        "triggerType": "retry",
        "retryCount": 2,
        "resumeFromStage": "render",
        "resumeFromClipIndex": 2,
        "completedClipCount": 1,
        "existingClipIndices": [1, 3],
        "reuseStoryboard": True,
    }
