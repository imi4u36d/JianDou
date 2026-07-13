from __future__ import annotations

import json

import httpx
import pytest

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_invocation_image_contracts import MultipartFilePart
from backend.services.model_invocation_image_transport import ImageProviderTransport

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_image_transport_sends_json_and_downloads_binary() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, content=b"image", headers={"content-type": "image/png"})
        return httpx.Response(200, json={"data": [{"b64_json": "aW1hZ2U="}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = ImageProviderTransport(client)
        response = await transport.send_json("https://image.example/v1", "secret", {"prompt": "rain"}, 10)
        binary = await transport.download_binary("https://cdn.example/image.png", 10)

    assert json.loads(requests[0].content) == {"prompt": "rain"}
    assert requests[0].headers["authorization"] == "Bearer secret"
    assert response.status_code == 200
    assert binary.data == b"image"
    assert binary.mime_type == "image/png"


@pytest.mark.asyncio
async def test_image_transport_classifies_non_retryable_quota_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text='{"error":"quota"}')

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GenerationProviderException, match="rate limit / quota exceeded"):
            await ImageProviderTransport(client).send_json(
                "https://image.example/v1", "secret", {"prompt": "rain"}, 30
            )


def test_image_transport_builds_multipart_fields_and_files() -> None:
    body = ImageProviderTransport._multipart_body(
        "boundary",
        {"prompt": "rain"},
        [MultipartFilePart("image[]", "reference.png", "image/png", b"png-data")],
    )

    assert b'name="prompt"' in body
    assert b"rain" in body
    assert b'filename="reference.png"' in body
    assert b"Content-Type: image/png" in body
    assert b"png-data" in body
    assert body.endswith(b"--boundary--\r\n")
