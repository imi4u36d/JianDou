"""Thumbnail generation and backfill for material assets.

Mirrors the Java MaterialAssetThumbnailService and
MaterialAssetThumbnailBackfillService (workflow/media module).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Port for media artifact operations (thin stub; the real implementation
# delegates to LocalMediaArtifactService / media_service.py)
# ---------------------------------------------------------------------------

class MediaThumbnailPort(Protocol):
    """Port for generating media thumbnails."""

    def ensure_media_thumbnail(
        self,
        media_type: str,
        media_url: str,
        candidate_image_urls: list[str],
        max_width: int,
    ) -> str:
        """Return a thumbnail URL for the given media, generating if needed."""
        ...


# ---------------------------------------------------------------------------
# MaterialAssetThumbnailService
# ---------------------------------------------------------------------------


class MaterialAssetThumbnailService:
    """Ensures material assets have thumbnail URLs.

    Mirrors the Java MaterialAssetThumbnailService.
    """

    def __init__(self, media_thumbnail_port: MediaThumbnailPort | None = None) -> None:
        self._media_thumbnail_port = media_thumbnail_port

    def ensure_thumbnail(self, asset: dict[str, Any]) -> str:
        """Return the thumbnail URL for *asset*, generating one if missing."""
        if asset is None:
            return ""
        existing = _normalize(asset.get("thumbnailUrl"))
        if existing:
            return existing
        generated = self.generate_thumbnail(asset)
        if generated:
            asset["thumbnailUrl"] = generated
        return generated

    def generate_thumbnail(self, asset: dict[str, Any]) -> str:
        """Generate a thumbnail URL for the given asset dict."""
        if asset is None:
            return ""
        metadata = _read_metadata(asset.get("metadataJson"))
        candidate = _first_non_blank(
            _str_value(metadata.get("thumbnailUrl")),
            _str_value(metadata.get("posterUrl")),
            _str_value(metadata.get("firstFrameUrl")),
            _str_value(metadata.get("startFrameUrl")),
        )
        candidate_urls = [candidate] if candidate else []
        if self._media_thumbnail_port is None:
            return ""
        return _str_value(self._media_thumbnail_port.ensure_media_thumbnail(
            _normalize(asset.get("mediaType")),
            _normalize(asset.get("publicUrl")),
            candidate_urls,
            480,
        ))

    def ensure_thumbnail_with_params(
        self,
        media_type: str,
        media_url: str,
        candidate_image_urls: list[str] | None,
    ) -> str:
        """Generate a thumbnail for the given media type and URL."""
        if self._media_thumbnail_port is None:
            return ""
        return _str_value(self._media_thumbnail_port.ensure_media_thumbnail(
            _normalize(media_type),
            _normalize(media_url),
            candidate_image_urls or [],
            480,
        ))


# ---------------------------------------------------------------------------
# MaterialAssetThumbnailBackfillService
# ---------------------------------------------------------------------------


class MaterialAssetThumbnailBackfillService:
    """Backfills missing thumbnails for historical material assets.

    Mirrors the Java MaterialAssetThumbnailBackfillService.
    Runs once at startup (or on demand) and processes assets in batches.
    """

    BATCH_SIZE = 50
    MAX_BATCHES = 200

    def __init__(
        self,
        workflow_repository: Any,
        thumbnail_service: MaterialAssetThumbnailService,
    ) -> None:
        self._workflow_repository = workflow_repository
        self._thumbnail_service = thumbnail_service

    def run_backfill(self) -> dict[str, int]:
        """Run the thumbnail backfill process.

        Returns a dict with ``scanned``, ``updated``, ``failed``, and
        ``elapsed_ms`` counts.
        """
        started_at = time.monotonic()
        scanned = 0
        updated = 0
        failed = 0
        after_id = 0

        for _batch in range(self.MAX_BATCHES):
            # The repository must expose this async-compatible method.
            assets = self._workflow_repository.list_material_assets_missing_thumbnails_after_id(
                after_id, self.BATCH_SIZE,
            )
            if not assets:
                break
            scanned += len(assets)
            for asset in assets:
                asset_id = asset.get("id")
                if asset_id is not None:
                    after_id = max(after_id, int(asset_id))
                try:
                    thumbnail_url = self._thumbnail_service.ensure_thumbnail(asset)
                    if thumbnail_url:
                        self._workflow_repository.update_material_asset_thumbnail(
                            asset.get("materialAssetId", ""),
                            thumbnail_url,
                        )
                        updated += 1
                    else:
                        failed += 1
                except Exception as ex:
                    failed += 1
                    logger.warning(
                        "material thumbnail backfill failed: assetId=%s",
                        asset.get("materialAssetId"),
                        exc_info=ex,
                    )

        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            "material thumbnail backfill finished: scanned=%d, updated=%d, failed=%d, elapsed_ms=%d",
            scanned, updated, failed, elapsed_ms,
        )
        return {
            "scanned": scanned,
            "updated": updated,
            "failed": failed,
            "elapsed_ms": elapsed_ms,
        }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _normalize(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _str_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _first_non_blank(*values: str) -> str:
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""


def _read_metadata(metadata_json: Any) -> dict[str, Any]:
    if metadata_json is None:
        return {}
    if isinstance(metadata_json, dict):
        return metadata_json
    if isinstance(metadata_json, str):
        try:
            return json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}
