"""Standardised HTTP error helpers for router endpoints.

Instead of ad-hoc ``raise HTTPException(status_code=..., detail=...)``
spread across every router, endpoints call these factory functions.
The result is a consistent error-response shape and a single place
to change status codes / messages across the API.
"""
from __future__ import annotations

from fastapi import HTTPException
from starlette import status


def not_found(resource: str = "resource") -> HTTPException:
    """Return a 404 for a missing resource."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource}_not_found",
    )


def bad_request(detail: str) -> HTTPException:
    """Return a 400 with a human-readable detail string."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def unauthorized(detail: str = "unauthenticated") -> HTTPException:
    """Return a 401 for missing or invalid authentication."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def forbidden(detail: str = "insufficient_permissions") -> HTTPException:
    """Return a 403 for authorised-but-not-permitted requests."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def conflict(detail: str) -> HTTPException:
    """Return a 409 for conflicting resource state."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def internal_error(detail: str = "internal_error") -> HTTPException:
    """Return a 500 for unexpected server errors."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


def service_unavailable(detail: str = "service_unavailable") -> HTTPException:
    """Return a 503 when a downstream service is not ready."""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


def bad_gateway(detail: str) -> HTTPException:
    """Return a 502 for upstream model-service errors."""
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"模型服务请求失败：{detail}",
    )


def validation_error(detail: str) -> HTTPException:
    """Return a 422 for request-validation failures."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )
