"""Generation catalog endpoint tests."""
from __future__ import annotations


async def test_generation_catalog_uses_configured_models(client):
    response = await client.get("/api/v3/generation/catalog")

    assert response.status_code == 200
    data = response.json()
    assert data["defaultAspectRatio"] == "16:9"
    assert data["defaultImageSize"] == "1824x1024"
    assert data["defaultVideoSize"] == "1280*720"
    assert data["defaultVideoDurationSeconds"] == 10
    assert any(model["value"] == "deepseek-v4-flash" for model in data["textAnalysisModels"])
    assert any(model["value"] == "Doubao-Seedream-4.5" for model in data["imageModels"])
    assert any(model["value"] == "seedance-1.5-pro" for model in data["videoModels"])


async def test_generation_options_matches_catalog(client):
    catalog = await client.get("/api/v3/generation/catalog")
    options = await client.get("/api/v3/generation/options")

    assert options.status_code == 200
    assert options.json() == catalog.json()
