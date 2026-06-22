"""Tests for backend/errors.py — standardized HTTP error helpers."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api
from starlette import status

from backend.errors import (
    bad_gateway,
    bad_request,
    conflict,
    forbidden,
    internal_error,
    not_found,
    service_unavailable,
    unauthorized,
    validation_error,
)


class TestNotFound:
    def test_default_resource(self):
        exc = not_found()
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail == "resource_not_found"

    def test_custom_resource(self):
        exc = not_found("workflow")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail == "workflow_not_found"


class TestBadRequest:
    def test_returns_400_with_detail(self):
        exc = bad_request("invalid state")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.detail == "invalid state"


class TestUnauthorized:
    def test_default_detail(self):
        exc = unauthorized()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "unauthenticated"

    def test_custom_detail(self):
        exc = unauthorized("invalid_credentials")
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "invalid_credentials"


class TestForbidden:
    def test_default_detail(self):
        exc = forbidden()
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "insufficient_permissions"

    def test_custom_detail(self):
        exc = forbidden("not_admin")
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "not_admin"


class TestConflict:
    def test_returns_409_with_detail(self):
        exc = conflict("duplicate_name")
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert exc.detail == "duplicate_name"


class TestInternalError:
    def test_default_detail(self):
        exc = internal_error()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.detail == "internal_error"


class TestServiceUnavailable:
    def test_default_detail(self):
        exc = service_unavailable()
        assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exc.detail == "service_unavailable"


class TestBadGateway:
    def test_returns_502_with_chinese_prefix(self):
        exc = bad_gateway("timeout")
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.detail == "模型服务请求失败：timeout"


class TestValidationError:
    def test_returns_422_with_detail(self):
        exc = validation_error("missing_field")
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert exc.detail == "missing_field"


class TestAllHelpersAreHTTPExceptions:
    """Every helper returns a FastAPI HTTPException so FastAPI handles them natively."""

    @pytest.mark.parametrize("factory,args", [
        (not_found, ("task",)),
        (bad_request, ("bad input",)),
        (unauthorized, ()),
        (forbidden, ()),
        (conflict, ("duplicate",)),
        (internal_error, ()),
        (service_unavailable, ()),
        (bad_gateway, ("upstream error",)),
        (validation_error, ("invalid field",)),
    ])
    def test_all_return_http_exception(self, factory, args):
        from fastapi import HTTPException
        exc = factory(*args)
        assert isinstance(exc, HTTPException)
        assert 400 <= exc.status_code < 600
