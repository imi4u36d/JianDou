"""Tests for backend/middleware/ — security, origin-guard, SPA fallback."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api
from starlette import status

from backend.middleware.origin import _normalize_origin
from backend.middleware.security import SECURITY_HEADERS


class TestNormalizeOrigin:
    def test_http_origin(self):
        assert _normalize_origin("http://example.com") == "http://example.com"

    def test_https_origin_with_port(self):
        assert _normalize_origin("HTTPS://Example.COM:443") == "https://example.com:443"

    def test_empty_origin(self):
        assert _normalize_origin("") == ""

    def test_none_origin(self):
        assert _normalize_origin(None) == ""

    def test_origin_without_scheme(self):
        assert _normalize_origin("example.com") == ""

    def test_whitespace_only(self):
        assert _normalize_origin("   ") == ""


class TestSecurityHeaders:
    def test_required_headers_present(self):
        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert "Referrer-Policy" in SECURITY_HEADERS
        assert "Permissions-Policy" in SECURITY_HEADERS
        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_all_values_are_non_empty(self):
        for key, value in SECURITY_HEADERS.items():
            assert value, f"Header {key} has empty value"


class TestSecurityMiddlewareApplied:
    """End-to-end: security middleware adds headers to responses."""

    async def test_response_includes_security_headers(self, client):
        response = await client.get("/api/v3/health")
        assert response.status_code == status.HTTP_200_OK
        for header, expected in SECURITY_HEADERS.items():
            assert response.headers.get(header) == expected, f"Missing header {header}"


class TestOriginGuardMiddleware:
    """End-to-end: state-changing requests from untrusted origins are rejected."""

    async def test_get_requests_pass_origin_guard(self, client):
        response = await client.get("/api/v3/health", headers={"origin": "http://evil.com"})
        assert response.status_code == status.HTTP_200_OK

    async def test_post_without_origin_passes(self, client):
        response = await client.post("/api/v3/auth/login", json={
            "username": "nonexistent",
            "password": "wrong",
        })
        # Should get 401 (bad credentials), not 403 (origin rejection)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    async def test_post_from_untrusted_origin_blocked(self, client):
        response = await client.post(
            "/api/v3/auth/login",
            json={"username": "admin", "password": "wrong"},
            headers={"origin": "http://evil.com"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "untrusted_origin"
