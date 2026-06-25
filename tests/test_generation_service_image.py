from __future__ import annotations

import base64
from typing import Any

import pytest

from backend.config import settings
from backend.domain.generation_run import GenerationModelKinds
from backend.services.generation_service import GenerationRunFactory, GenerationRunSupport

pytestmark = pytest.mark.service


_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@pytest.mark.asyncio
async def test_image_run_keeps_generated_artifact_urls_local(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    factory = _LocalImageFactory(GenerationRunSupport())

    run = await factory.create_image_run(
        "run_image_local",
        {
            "input": {"prompt": "雨夜社区药箱", "width": 1, "height": 1, "frameRole": "first"},
            "model": {"textAnalysisModel": "gpt-5.5", "providerModel": "gpt-image-2"},
            "storage": {"relativeDir": "tasks/task_image/running", "fileStem": "clip1-first"},
            "metadata": {"relatedTaskId": "task_image"},
        },
    )

    result = run["result"]
    metadata = result["metadata"]
    assert result["outputUrl"] == "/storage/tasks/task_image/running/clip1-first.png"
    assert metadata["fileUrl"] == result["outputUrl"]
    assert metadata["remoteSourceUrl"] == result["outputUrl"]
    assert metadata["artifactRemoteSourceUrl"] == result["outputUrl"]
    assert metadata["providerRemoteSourceUrl"] == "https://provider.example/image.png"


class _LocalImageFactory(GenerationRunFactory):
    def __init__(self, support: GenerationRunSupport) -> None:
        super().__init__(
            support=support,
            config_resolver=object(),
            text_provider=object(),
            prompt_resolver=object(),
            image_providers=[],
            video_provider=object(),
        )

    def _resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> dict[str, Any]:
        return {
            "requestedModel": requested_model,
            "modelName": requested_model,
            "provider": "openai",
            "endpointHost": "api.openai.test",
            "source": "test",
        }

    def _resolve_media_profile(
        self,
        requested_model: str,
        media_kind: str,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        assert media_kind == GenerationModelKinds.IMAGE
        return {
            "requestedModel": requested_model,
            "modelName": requested_model,
            "provider": "openai",
            "endpointHost": "api.openai.test",
            "taskEndpointHost": "api.openai.test",
            "source": "test",
            "supportsSeed": False,
        }

    async def _call_image_model(
        self,
        image_profile: dict[str, Any],
        prompt: str,
        width: int,
        height: int,
        reference_image_urls: list[str],
        seed: int | None,
    ) -> dict[str, Any]:
        return {
            "data": _PNG_1X1,
            "mimeType": "image/png",
            "remoteSourceUrl": "https://provider.example/image.png",
            "provider": image_profile["provider"],
            "providerModel": image_profile["modelName"],
            "endpointHost": image_profile["endpointHost"],
            "requestedSize": f"{width}x{height}",
            "providerRequest": {"prompt": prompt, "references": reference_image_urls, "seed": seed},
            "providerResponse": {"id": "img_provider_1"},
            "httpStatus": 200,
        }
