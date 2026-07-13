"""Fault-tolerant workflow material thumbnail resolution."""

from __future__ import annotations

import logging
from typing import Any

from backend.shared import trim

logger = logging.getLogger(__name__)


class WorkflowThumbnailResolver:
    def __init__(self, media_service: Any | None) -> None:
        self._media_service = media_service

    def resolve(
        self,
        media_type: str,
        public_url: str,
        candidate_image_urls: list[str] | None = None,
    ) -> str:
        if self._media_service is None or not public_url:
            return ""
        try:
            return trim(
                self._media_service.ensure_media_thumbnail(
                    media_type,
                    public_url,
                    candidate_image_urls or [],
                    480,
                )
            )
        except Exception as exc:
            logger.warning("Failed to generate %s thumbnail for workflow material: %s", media_type, exc)
            return ""
