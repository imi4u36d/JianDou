from __future__ import annotations

from typing import Any

import pytest

from backend.domain.generation_run import GenerationModelKinds, GenerationRunStatuses
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.generation_video_run_service import GenerationVideoRunService

pytestmark = pytest.mark.service


def _text_profile(requested_model: str, user_id: int | None = None) -> dict[str, Any]:
    return {
        "requestedModel": requested_model,
        "modelName": requested_model,
        "provider": "openai",
        "endpointHost": "text.example.test",
        "source": "test",
        "userId": user_id,
    }


def _media_profile(requested_model: str, media_kind: str, user_id: int | None = None) -> dict[str, Any]:
    assert media_kind == GenerationModelKinds.VIDEO
    return {
        "requestedModel": requested_model,
        "modelName": requested_model,
        "provider": "seedance",
        "endpointHost": "video.example.test",
        "taskEndpointHost": "video.example.test/tasks",
        "source": "test",
        "userId": user_id,
        "supportsSeed": True,
        "cameraFixed": False,
        "watermark": False,
        "supportedDurations": [5, 8, 10],
    }


async def _submit_video(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "provider": "seedance",
        "providerModel": "seedance-2.0",
        "taskId": "video-task-1",
        "endpointHost": "video.example.test",
        "taskEndpointHost": "video.example.test/tasks",
        "providerRequest": {"duration": args[4]},
        "providerResponse": {"task_id": "video-task-1"},
        "httpStatus": 200,
        "firstFrameUrl": args[5],
        "requestedLastFrameUrl": args[6],
        "returnLastFrame": args[10],
        "generateAudio": args[11],
    }


async def _query_video(profile: dict[str, Any], task_id: str) -> dict[str, Any]:
    raise AssertionError(f"unexpected query for {profile=} {task_id=}")


@pytest.mark.asyncio
async def test_video_run_service_builds_running_provider_run() -> None:
    service = GenerationVideoRunService(
        support=GenerationRunSupport(),
        resolve_text_profile=_text_profile,
        resolve_media_profile=_media_profile,
        call_video_submit=_submit_video,
        call_video_query=_query_video,
    )

    run = await service.create_video_run(
        "run-video-1",
        {
            "auth": {"userId": 7},
            "input": {
                "prompt": "雨夜街口，固定镜头",
                "width": 1280,
                "height": 720,
                "durationSeconds": 7,
                "minDurationSeconds": 5,
                "maxDurationSeconds": 10,
                "seed": 42,
                "generateAudio": True,
                "returnLastFrame": True,
            },
            "model": {"textAnalysisModel": "gpt-5.5", "providerModel": "seedance-2.0"},
            "metadata": {"relatedTaskId": "task-1"},
        },
    )

    result = run["resultVideo"]
    assert run["status"] == GenerationRunStatuses.RUNNING
    assert result["durationSeconds"] == 8
    assert result["metadata"]["taskId"] == "video-task-1"
    assert result["metadata"]["videoGenerationSeed"] == 42
    assert result["metadata"]["relatedTaskId"] == "task-1"


def test_video_frame_input_keeps_supported_remote_and_data_urls() -> None:
    service = GenerationVideoRunService(
        support=GenerationRunSupport(),
        resolve_text_profile=_text_profile,
        resolve_media_profile=_media_profile,
        call_video_submit=_submit_video,
        call_video_query=_query_video,
    )

    assert (
        service.resolve_frame_input("https://cdn.example.test/frame.png", "firstFrameUrl")
        == "https://cdn.example.test/frame.png"
    )
    assert service.resolve_frame_input("data:image/png;base64,abc", "firstFrameUrl") == "data:image/png;base64,abc"
    assert service.resolve_frame_input("file:///tmp/frame.png", "firstFrameUrl") == ""
