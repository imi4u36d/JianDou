from __future__ import annotations

import pytest

from backend.services.generation_text_run_values import (
    invalid_storyboard_reason,
    request_metadata,
    text_provider_interaction,
    user_id_from_request,
)

pytestmark = pytest.mark.service


def test_text_run_values_normalize_request_context() -> None:
    assert user_id_from_request({"auth": {"userId": " 42 "}}) == 42
    assert user_id_from_request({"auth": {"userId": "invalid"}}) is None
    assert request_metadata({"metadata": {"trace": "one"}}) == {"trace": "one"}
    assert request_metadata({"metadata": []}) == {}


def test_text_run_values_project_provider_status_and_storyboard_validation() -> None:
    interaction = text_provider_interaction(
        "draft",
        {"httpStatus": 503, "responseId": "failed", "latencyMs": 20},
    )

    assert interaction["success"] is False
    assert interaction["responseId"] == "failed"
    assert invalid_storyboard_reason("") == "review output is blank"
    assert invalid_storyboard_reason("plain text") == "review output missing character definitions"
    assert invalid_storyboard_reason("【 】\n【 】") == ""
