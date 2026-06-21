from __future__ import annotations

import pytest
pytestmark = pytest.mark.domain
from backend.domain.generation_run import GenerationModelKinds, GenerationRunKinds, GenerationRunStatuses


def test_generation_run_status_classification_normalizes_case_and_whitespace() -> None:
    assert GenerationRunStatuses.is_active(" queued ")
    assert GenerationRunStatuses.is_active("SUBMITTED")
    assert GenerationRunStatuses.is_active("Running")
    assert GenerationRunStatuses.is_active("accepted")

    assert GenerationRunStatuses.is_successful(" succeeded ")
    assert GenerationRunStatuses.is_successful("COMPLETED")
    assert GenerationRunStatuses.is_successful("Success")

    assert not GenerationRunStatuses.is_active("failed")
    assert not GenerationRunStatuses.is_successful("failed")
    assert not GenerationRunStatuses.is_active("")
    assert not GenerationRunStatuses.is_successful("")


def test_generation_kind_and_model_kind_constants_are_canonical_strings() -> None:
    assert GenerationRunKinds.PROBE == "probe"
    assert GenerationRunKinds.SCRIPT == "script"
    assert GenerationRunKinds.SCRIPT_ADJUST == "script_adjust"
    assert GenerationRunKinds.IMAGE == "image"
    assert GenerationRunKinds.VIDEO == "video"

    assert GenerationModelKinds.TEXT == "text"
    assert GenerationModelKinds.IMAGE == "image"
    assert GenerationModelKinds.VIDEO == "video"
