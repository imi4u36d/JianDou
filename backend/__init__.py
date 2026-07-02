"""JianDou - AI video generation platform.

Backend package providing the FastAPI application factory, service layer,
domain model, and infrastructure adapters.
"""
from __future__ import annotations

import importlib.metadata

try:
    __version__ = importlib.metadata.version("jiandou")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.2.0rc1"
