from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from backend.services.model_response_parsing import (
    extract_first_string,
    extract_text_response,
    extract_video_task_id,
    extract_video_task_message,
    extract_video_task_status,
    extract_video_url,
    map_value,
)


def test_extract_text_response_prefers_responses_api_output_text() -> None:
    assert extract_text_response({"output_text": " direct ", "text": "fallback"}) == "direct"


def test_extract_text_response_reads_responses_output_content_parts() -> None:
    response = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "first"},
                    {"type": "text", "text": "second"},
                ],
            }
        ]
    }

    assert extract_text_response(response) == "first\nsecond"


def test_extract_text_response_reads_chat_completion_choices() -> None:
    response = {"choices": [{"message": {"content": [{"type": "text", "text": "chat text"}]}}]}

    assert extract_text_response(response) == "chat text"


def test_extract_first_string_recurses_and_respects_key_order() -> None:
    payload = {
        "data": [
            {"fileUrl": ""},
            {"nested": {"imageUrl": "https://example.test/image.png"}},
        ]
    }

    assert extract_first_string(payload, "fileUrl", "imageUrl") == "https://example.test/image.png"


def test_video_response_parsing_supports_common_provider_shapes() -> None:
    payload = {
        "output": {"taskId": "remote-task", "state": "succeeded"},
        "data": {"mediaUrl": "https://example.test/video.mp4"},
        "error": {"message": "ignored"},
    }

    assert extract_video_task_id(payload) == "remote-task"
    assert extract_video_task_status(payload) == "SUCCEEDED"
    assert extract_video_url(payload) == "https://example.test/video.mp4"
    assert extract_video_task_message(payload) == "ignored"


def test_map_value_normalizes_only_mapping_shapes() -> None:
    assert map_value({1: "one", "two": 2}) == {"1": "one", "two": 2}
    assert map_value(["bad"]) == {}
