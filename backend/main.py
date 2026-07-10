"""FastAPI application entry point.

The assembly implementation lives in :mod:`backend.application`; this module
keeps the public ``backend.main:create_app`` and ``backend.main:app`` imports
stable for uvicorn, tests, and existing deployments.
"""

from __future__ import annotations

from backend.application import create_app

app = create_app()

__all__ = ["app", "create_app"]
