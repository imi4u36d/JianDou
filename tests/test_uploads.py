"""Upload endpoint tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api
from io import BytesIO

import pytest


@pytest.mark.asyncio
async def test_upload_text(client):
    response = await client.post(
        "/api/v3/uploads/texts",
        files={"file": ("test.txt", BytesIO(b"Hello, World!"), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "asset_id" in data
    assert data["file_name"] == "test.txt"


@pytest.mark.asyncio
async def test_upload_image(client):
    response = await client.post(
        "/api/v3/uploads/images",
        files={"file": ("photo.png", BytesIO(b"fake-image-data"), "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "asset_id" in data


@pytest.mark.asyncio
async def test_upload_video(client):
    response = await client.post(
        "/api/v3/uploads/videos",
        files={"file": ("clip.mp4", BytesIO(b"fake-video-data"), "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "asset_id" in data


@pytest.mark.asyncio
async def test_upload_without_file_returns_422(client):
    response = await client.post("/api/v3/uploads/texts")
    assert response.status_code == 422
