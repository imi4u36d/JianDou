"""Generation catalog endpoint tests."""

from __future__ import annotations

from math import gcd

import pytest

pytestmark = pytest.mark.service


GPT_IMAGE_2_SUPPORTED_SIZES = [
    "1280x720",
    "2048x1152",
    "3840x2160",
    "720x1280",
    "1152x2048",
    "2160x3840",
    "864x1920",
    "1296x2880",
    "1728x3840",
    "3808x1632",
    "3504x2336",
    "2336x3504",
    "3264x2448",
    "768x1024",
    "1536x2048",
    "2448x3264",
    "1024x1024",
    "2048x2048",
    "2880x2880",
]


async def test_generation_catalog_uses_configured_models(client):
    response = await client.get("/api/v3/generation/catalog")

    assert response.status_code == 200
    data = response.json()
    assert data["defaultAspectRatio"] == "9:16"
    assert data["defaultImageSize"] == "2160x3840"
    assert data["defaultVideoSize"] == "1280*720"
    assert data["defaultVideoDurationSeconds"] == 10
    assert any(model["value"] == "gpt-5.5" for model in data["textAnalysisModels"])
    assert any(model["value"] == "gpt-image-2" for model in data["imageModels"])
    assert any(model["value"] == "seedance-1.5-pro" for model in data["videoModels"])
    assert all(model["provider"] == "openai" for model in data["textAnalysisModels"])
    assert all(model["provider"] == "openai" for model in data["imageModels"])
    image_model = next(model for model in data["imageModels"] if model["value"] == "gpt-image-2")
    assert image_model["supportedSizes"] == GPT_IMAGE_2_SUPPORTED_SIZES
    assert {item["value"] for item in data["imageSizes"]} == set(GPT_IMAGE_2_SUPPORTED_SIZES)
    assert data["defaultImageSize"] in image_model["supportedSizes"]


async def test_gpt_image_2_sizes_match_openai_constraints(client):
    response = await client.get("/api/v3/generation/catalog")

    assert response.status_code == 200
    data = response.json()
    image_model = next(model for model in data["imageModels"] if model["value"] == "gpt-image-2")

    for size in image_model["supportedSizes"]:
        width, height = [int(value) for value in size.split("x")]
        long_edge = max(width, height)
        short_edge = min(width, height)
        assert width % 16 == 0
        assert height % 16 == 0
        assert long_edge <= 3840
        assert width * height >= 655_360
        assert width * height <= 8_294_400
        assert long_edge / short_edge <= 3
        divisor = gcd(width, height)
        assert f"{width // divisor}:{height // divisor}" in {
            "16:9",
            "9:16",
            "9:20",
            "21:9",
            "7:3",
            "3:2",
            "2:3",
            "4:3",
            "3:4",
            "1:1",
        }


async def test_generation_options_matches_catalog(client):
    catalog = await client.get("/api/v3/generation/catalog")
    options = await client.get("/api/v3/generation/options")

    assert options.status_code == 200
    assert options.json() == catalog.json()
