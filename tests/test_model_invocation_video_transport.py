from __future__ import annotations

import json

import httpx
import pytest

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_invocation_video_transport import VideoProviderTransport

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_video_transport_sends_json_with_provider_headers() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"task_id": "remote-1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = VideoProviderTransport(client)
        response = await transport.send_json(
            "https://video.example/tasks",
            "secret",
            {"prompt": "rain"},
            10,
            {"X-Api-Key": "secret"},
        )

    assert response.status_code == 200
    assert captured["body"] == {"prompt": "rain"}
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert captured["headers"]["x-api-key"] == "secret"


@pytest.mark.asyncio
async def test_video_transport_classifies_quota_and_gateway_errors() -> None:
    async def assert_failure(status_code: int, body: str, expected: str) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, text=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GenerationProviderException, match=expected):
                await VideoProviderTransport(client).send_json(
                    "https://video.example/tasks", "secret", {"prompt": "rain"}, 30
                )

    await assert_failure(429, '{"error":"quota"}', "rate limit / quota exceeded")
    await assert_failure(502, "<html><body>Bad gateway</body></html>", "upstream gateway error")


def test_video_transport_normalizes_task_payload_helpers() -> None:
    transport = VideoProviderTransport()
    payload = {"data": {"task_id": "task-1", "status": "completed", "video_url": "https://cdn/video.mp4"}}

    assert transport.extract_task_id(payload) == "task-1"
    assert transport.extract_task_status(payload) == "COMPLETED"
    assert transport.extract_video_url(payload) == "https://cdn/video.mp4"
    assert transport.encode_path_segment("task/1") == "task%2F1"
