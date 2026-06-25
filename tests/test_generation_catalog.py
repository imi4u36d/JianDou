"""Generation catalog endpoint tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.service

async def test_generation_catalog_uses_configured_models(client):
    response = await client.get("/api/v3/generation/catalog")

    assert response.status_code == 200
    data = response.json()
    assert data["defaultAspectRatio"] == "16:9"
    assert data["defaultImageSize"] == "2560x1440"
    assert data["defaultVideoSize"] == "1280*720"
    assert data["defaultVideoDurationSeconds"] == 10
    assert any(model["value"] == "gpt-5.5" for model in data["textAnalysisModels"])
    assert any(model["value"] == "gpt-image-2" for model in data["imageModels"])
    assert any(model["value"] == "seedance-1.5-pro" for model in data["videoModels"])
    assert all(model["provider"] == "openai" for model in data["textAnalysisModels"])
    assert all(model["provider"] == "openai" for model in data["imageModels"])


async def test_generation_options_matches_catalog(client):
    catalog = await client.get("/api/v3/generation/catalog")
    options = await client.get("/api/v3/generation/options")

    assert options.status_code == 200
    assert options.json() == catalog.json()
