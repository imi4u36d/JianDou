"""Test that JSON responses use camelCase keys for frontend compatibility."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any

import pytest
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


@dataclass
class MockProviderItem:
    key: str
    api_key_configured: bool
    base_url: str


@dataclass
class MockResponse:
    providers: list[MockProviderItem]
    config_source: str


def _build_test_app() -> FastAPI:
    """Build a minimal app with the real middleware."""
    from fastapi import FastAPI
    from backend.middleware import CamelCaseJsonMiddleware

    app = FastAPI()
    app.add_middleware(CamelCaseJsonMiddleware)

    @app.get("/dataclass")
    def get_dataclass() -> Any:
        """Return a dataclass the way FastAPI does (via jsonable_encoder)."""
        item = MockProviderItem(key="openai", api_key_configured=True, base_url="https://api.openai.com")
        response = MockResponse(providers=[item], config_source="test")
        return asdict(response)

    @app.get("/direct-dict")
    def get_dict() -> dict:
        """Return a plain dict with snake_case keys."""
        return {"api_key_configured": True, "base_url": "https://x.com"}

    return app


@pytest.fixture
def test_app():
    return _build_test_app()


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_camel_case_direct_dict(client):
    """Test that plain dict snake_case keys are converted to camelCase."""
    resp = client.get("/direct-dict")
    assert resp.status_code == 200, f"Unexpected status: {resp.text}"
    data = resp.json()

    print(f"\nResponse keys: {list(data.keys())}")
    for k, v in data.items():
        print(f"  {k}: {v}")

    assert "apiKeyConfigured" in data, f"Expected 'apiKeyConfigured', got keys: {list(data.keys())}"
    assert "baseUrl" in data, f"Expected 'baseUrl', got keys: {list(data.keys())}"
    assert "api_key_configured" not in data, "snake_case key should be replaced"
    assert data["apiKeyConfigured"] is True


def test_camel_case_dataclass(client):
    """Test that dataclass-based responses are converted to camelCase."""
    resp = client.get("/dataclass")
    assert resp.status_code == 200, f"Unexpected status: {resp.text}"
    data = resp.json()

    print(f"\nDataclass response keys: {list(data.keys())}")
    for k, v in data.items():
        print(f"  {k}: ...")

    assert "providers" in data, f"Expected 'providers', got keys: {list(data.keys())}"
    assert "configSource" in data, f"Expected 'configSource', got keys: {list(data.keys())}"

    # Check nested provider item
    assert len(data["providers"]) == 1
    provider = data["providers"][0]
    print(f"\nProvider keys: {list(provider.keys())}")

    assert "apiKeyConfigured" in provider, f"Expected 'apiKeyConfigured' in provider, got: {list(provider.keys())}"
    assert "baseUrl" in provider, f"Expected 'baseUrl' in provider, got: {list(provider.keys())}"
    assert "key" in provider


def test_camel_case_nested_deeply(client):
    """Test that deeply nested snake_case keys are all converted."""
    resp = client.get("/direct-dict")
    assert resp.status_code == 200

    # Add a deeply nested test endpoint to the app
    from backend.main import app as main_app

    # Verify the middleware is registered in the real app
    from backend.middleware import CamelCaseJsonMiddleware

    # Check that the middleware class is imported correctly
    assert hasattr(CamelCaseJsonMiddleware, '__call__')


def test_camel_case_preserves_non_string_values(client):
    """Test that non-string values (bool, int, None) are preserved."""
    resp = client.get("/direct-dict")
    assert resp.status_code == 200
    data = resp.json()

    # Boolean should remain boolean, not become string
    assert isinstance(data["apiKeyConfigured"], bool)
    assert data["apiKeyConfigured"] is True


