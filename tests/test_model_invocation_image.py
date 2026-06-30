from __future__ import annotations

import httpx
import pytest

from backend.services.model_config_service import (
    MediaProviderCapabilities,
    MediaProviderConfig,
    MediaProviderProfile,
)
from backend.services.model_invocation import ImageGenerationRequest, OpenAiImageModelProvider
from backend.services.model_response_parsing import extract_first_string

pytestmark = pytest.mark.service


def test_openai_image_provider_uses_auto_size_when_dimensions_are_zero() -> None:
    request = ImageGenerationRequest(width=0, height=0)

    assert OpenAiImageModelProvider._requested_image_size(request) == "auto"


def test_openai_image_provider_uses_explicit_size_when_dimensions_are_positive() -> None:
    request = ImageGenerationRequest(width=1024, height=1536)

    assert OpenAiImageModelProvider._requested_image_size(request) == "1024x1536"


@pytest.mark.asyncio
async def test_openai_image_to_image_sends_model_in_multipart_fields() -> None:
    transport = _ImageMultipartTransport()
    provider = OpenAiImageModelProvider(transport=transport)

    result = await provider.generate(
        _image_profile(),
        ImageGenerationRequest(
            requested_model="gpt-image-2",
            prompt="make it cinematic",
            width=1024,
            height=1024,
            reference_image_urls=["data:image/png;base64,cmVm"],
        ),
    )

    assert result.data == b"image"
    assert transport.sent_multipart is not None
    assert transport.sent_multipart["endpoint"] == "https://api.example.test/v1/images/edits"
    assert transport.sent_multipart["fields"]["model"] == "gpt-image-2"
    assert transport.sent_multipart["fields"]["prompt"] == "make it cinematic"
    assert transport.sent_multipart["files"][0].field_name == "image[]"
    assert transport.sent_multipart["files"][0].data == b"ref"


@pytest.mark.asyncio
async def test_openai_image_to_image_defaults_missing_model_to_gpt_image_2() -> None:
    transport = _ImageMultipartTransport()
    provider = OpenAiImageModelProvider(transport=transport)

    await provider.generate(
        _image_profile(model=""),
        ImageGenerationRequest(
            requested_model="",
            prompt="make it cinematic",
            width=1024,
            height=1024,
            reference_image_urls=["data:image/png;base64,cmVm"],
        ),
    )

    assert transport.sent_multipart is not None
    assert transport.sent_multipart["fields"]["model"] == "gpt-image-2"


def _image_profile(model: str = "gpt-image-2") -> MediaProviderProfile:
    return MediaProviderProfile(
        MediaProviderConfig(
            kind="image",
            model=model,
            provider="openai",
            provider_model=model,
            api_key="sk-test",
            base_url="https://api.example.test/v1",
            task_base_url="",
            timeout_seconds=120,
            source="unit-test",
        ),
        MediaProviderCapabilities(
            supports_seed=False,
            prompt_extend=False,
            camera_fixed=False,
            watermark=False,
            poll_interval_seconds=5,
            poll_timeout_seconds=300,
            generation_mode="",
            supported_sizes=[],
            supported_durations=[],
            supports_image_data_uri_references=True,
        ),
    )


class _ImageMultipartTransport:
    def __init__(self) -> None:
        self.sent_multipart: dict | None = None

    async def send_multipart(
        self,
        endpoint: str,
        api_key: str,
        fields: dict,
        files: list,
        timeout_seconds: int,
        request_payload: dict | None = None,
    ) -> httpx.Response:
        self.sent_multipart = {
            "endpoint": endpoint,
            "apiKey": api_key,
            "fields": fields,
            "files": files,
            "timeoutSeconds": timeout_seconds,
            "requestPayload": request_payload,
        }
        return httpx.Response(200, json={"data": [{"b64_json": "aW1hZ2U="}]})

    async def download_binary(self, *args, **kwargs) -> None:
        raise AssertionError("data URI references should not be downloaded")

    def decode(self, raw: str) -> dict:
        return httpx.Response(200, text=raw).json()

    def extract_first_string(self, raw: object, *keys: str) -> str:
        return extract_first_string(raw, *keys)
