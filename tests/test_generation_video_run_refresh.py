from __future__ import annotations

from typing import Any

import pytest

from backend.domain.generation_run import GenerationRunKinds, GenerationRunStatuses
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.generation_video_run_refresh import GenerationVideoRunRefresher


def _run() -> dict[str, Any]:
    result = {
        "metadata": {
            "taskId": "remote_1",
            "requestedModel": "video-model",
            "nextPollAt": 0,
            "generateAudio": True,
            "requestedLastFrameUrl": "/last.png",
        },
        "callChain": [],
    }
    return {
        "id": "run_1",
        "kind": GenerationRunKinds.VIDEO,
        "status": GenerationRunStatuses.RUNNING,
        "request": {"auth": {"userId": 7}},
        "result": result,
        "resultVideo": result,
    }


@pytest.mark.asyncio
async def test_refresher_materializes_successful_provider_video(monkeypatch) -> None:
    support = GenerationRunSupport()
    monkeypatch.setattr(
        support,
        "materialize_binary_artifact",
        lambda *_args: {"publicUrl": "/stored.mp4", "mimeType": "video/mp4"},
    )

    async def query(_profile: dict[str, Any], task_id: str) -> dict[str, Any]:
        assert task_id == "remote_1"
        return {
            "taskStatus": "SUCCEEDED",
            "videoUrl": "https://provider.example/video.mp4",
            "providerRequest": {"task_id": task_id},
            "providerResponse": {"status": "SUCCEEDED"},
            "httpStatus": 200,
        }

    refresher = GenerationVideoRunRefresher(
        support,
        lambda model, kind, user_id: {
            "model": model,
            "kind": kind,
            "userId": user_id,
            "taskEndpointHost": "provider.example",
        },
        query,
    )

    run = await refresher.refresh(_run())

    assert run["status"] == GenerationRunStatuses.SUCCEEDED
    assert run["result"]["outputUrl"] == "/stored.mp4"
    assert run["result"]["metadata"]["remoteSourceUrl"].startswith("https://provider.example")
    assert run["result"]["metadata"]["providerQueryHistory"][0]["success"] is True


@pytest.mark.asyncio
async def test_refresher_schedules_another_poll_for_running_provider_task() -> None:
    async def query(_profile: dict[str, Any], _task_id: str) -> dict[str, Any]:
        return {
            "taskStatus": "RUNNING",
            "videoUrl": "",
            "taskMessage": "processing",
            "providerResponse": {"status": "RUNNING"},
        }

    refresher = GenerationVideoRunRefresher(
        GenerationRunSupport(),
        lambda *_args: {},
        query,
    )

    run = await refresher.refresh(_run())

    assert run["status"] == GenerationRunStatuses.RUNNING
    assert run["result"]["metadata"]["nextPollAt"] > 0
    assert run["result"]["callChain"][-1]["event"] == "video.polling"
