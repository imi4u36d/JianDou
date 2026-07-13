"""Thumbnail generation collaborator for local media artifacts."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

if TYPE_CHECKING:
    from backend.services.media_service import LocalMediaArtifactService


class LocalMediaThumbnailService:
    """Generate and cache local, remote-image, and video thumbnails."""

    def __init__(self, media_service: LocalMediaArtifactService) -> None:
        self._media_service = media_service

    def __getattr__(self, name: str) -> Any:
        return getattr(self._media_service, name)

    def ensure_image_thumbnail(self, public_url: str, max_width: int) -> str:
        """Generate a thumbnail for a local storage image.

        Args:
            public_url: The public URL of the image (e.g., /storage/...).
            max_width: Maximum thumbnail width.

        Returns:
            Public URL of the thumbnail, or empty string if it cannot be generated.
        """
        absolute_source_path = self._resolve_absolute_path(public_url)
        if not absolute_source_path:
            return self._ensure_remote_image_thumbnail(public_url, max_width)

        source = Path(absolute_source_path).resolve()
        if not source.is_file() or not str(source).startswith(str(self._storage_root)):
            return ""

        mime_type = self._image_mime_type(source)
        if not mime_type.startswith("image/"):
            return ""

        try:
            original = Image.open(source)
        except Exception:
            return ""

        if original.width <= 0 or original.height <= 0:
            return ""

        bounded_width = max(120, max_width)
        target_width = min(bounded_width, original.width)
        target_height = max(1, round(original.height * (target_width / original.width)))
        target = self._thumbnail_path(source, bounded_width)

        if target.is_file() and not self._thumbnail_is_stale(source, target):
            return self._public_url_for_storage_path(target)

        target.parent.mkdir(parents=True, exist_ok=True)
        thumb = original.resize((target_width, target_height), Image.BILINEAR)
        thumb.save(target, "JPEG", quality=78)
        return self._public_url_for_storage_path(target)

    def ensure_media_thumbnail(
        self,
        media_type: str,
        media_url: str,
        candidate_image_urls: list[str] | None,
        max_width: int,
    ) -> str:
        """Generate a thumbnail for a media item (image or video).

        For images, generates directly. For videos, prefers candidate
        cover images, otherwise extracts a video frame.

        Args:
            media_type: "image" or "video".
            media_url: Public URL of the media.
            candidate_image_urls: Optional list of candidate cover image URLs.
            max_width: Maximum thumbnail width.

        Returns:
            Public URL of the thumbnail, or empty string.
        """
        normalized_type = (media_type or "").strip().lower()
        candidates = candidate_image_urls or []

        if normalized_type == "image":
            return self._first_non_blank(
                self._existing_thumbnail_url(media_url),
                self.ensure_image_thumbnail(media_url, max_width),
                self._ensure_first_image_thumbnail(candidates, max_width),
            )

        if normalized_type == "video":
            return self._first_non_blank(
                self._ensure_first_image_thumbnail(candidates, max_width),
                self._ensure_video_thumbnail(media_url, max_width),
            )

        return self._ensure_first_image_thumbnail(candidates, max_width)

    def _ensure_remote_image_thumbnail(self, public_url: str, max_width: int) -> str:
        normalized = (public_url or "").strip()
        if not self._is_http_url(normalized):
            return ""

        bounded_width = max(120, max_width)
        target = self._remote_image_thumbnail_path(normalized, bounded_width)
        if target.is_file():
            return self._public_url_for_storage_path(target)

        try:
            resp = self._http_session.get(normalized, timeout=30)
            resp.raise_for_status()
            if not resp.content:
                return ""

            with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            try:
                original = Image.open(tmp_path)
            except Exception:
                return ""
            finally:
                os.unlink(tmp_path)

            if original.width <= 0 or original.height <= 0:
                return ""

            target_width = min(bounded_width, original.width)
            target_height = max(1, round(original.height * (target_width / original.width)))
            target.parent.mkdir(parents=True, exist_ok=True)
            thumb = original.resize((target_width, target_height), Image.BILINEAR)
            thumb.save(target, "JPEG", quality=78)
            return self._public_url_for_storage_path(target)

        except Exception:
            return ""

    def _ensure_first_image_thumbnail(self, candidate_urls: list[str], max_width: int) -> str:
        for url in candidate_urls:
            thumbnail = self._first_non_blank(
                self._existing_thumbnail_url(url),
                self.ensure_image_thumbnail(url, max_width),
            )
            if thumbnail:
                return thumbnail
        return ""

    def _existing_thumbnail_url(self, public_url: str) -> str:
        normalized = (public_url or "").replace("\\", "/")
        return normalized if normalized.startswith("/storage/thumbs/") else ""

    def _ensure_video_thumbnail(self, public_url: str, max_width: int) -> str:
        abs_path = self._resolve_absolute_path(public_url)
        if not abs_path:
            return ""

        source = Path(abs_path).resolve()
        if not source.is_file() or not str(source).startswith(str(self._storage_root)):
            return ""

        target = self._video_thumbnail_path(source, max(120, max_width))
        if target.is_file() and not self._thumbnail_is_stale(source, target):
            return self._public_url_for_storage_path(target)

        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            frame_path = tmp.name

        try:
            self._extract_video_frame(source, Path(frame_path))
            try:
                frame = Image.open(frame_path)
            except Exception:
                return ""

            if frame.width <= 0 or frame.height <= 0:
                return ""

            bounded_width = max(120, max_width)
            target_width = min(bounded_width, frame.width)
            target_height = max(1, round(frame.height * (target_width / frame.width)))
            thumb = Image.new("RGB", (target_width, target_height), (0, 0, 0))
            resized = frame.resize((target_width, target_height), Image.BILINEAR)
            thumb.paste(resized, (0, 0))
            thumb.save(target, "JPEG", quality=78)
            return self._public_url_for_storage_path(target)
        finally:
            os.unlink(frame_path)

    def _extract_video_frame(self, source: Path, frame_path: Path) -> None:
        cmd = [
            self._ffmpeg_bin,
            "-y",
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(frame_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0 or not frame_path.is_file():
                raise RuntimeError(result.stderr.strip() or "ffmpeg frame extraction failed")
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg frame extraction timed out")

    def _thumbnail_path(self, source: Path, max_width: int) -> Path:
        relative = source.relative_to(self._storage_root)
        parent = relative.parent
        stem = source.stem
        version = self._thumbnail_version(source)
        name = f"{stem}-w{max_width}-{version}.jpg"
        return (self._storage_root / "thumbs" / parent / name).resolve()

    def _remote_image_thumbnail_path(self, source_url: str, max_width: int) -> Path:
        h = self._sha256_hex(source_url)[:24]
        name = f"{h}-w{max_width}.jpg"
        return (self._storage_root / "thumbs" / "remote" / name).resolve()

    def _video_thumbnail_path(self, source: Path, max_width: int) -> Path:
        relative = source.relative_to(self._storage_root)
        parent = relative.parent
        stem = source.stem
        version = self._thumbnail_version(source)
        name = f"{stem}-video-w{max_width}-{version}.jpg"
        return (self._storage_root / "thumbs" / parent / name).resolve()

    @staticmethod
    def _thumbnail_version(source: Path) -> str:
        try:
            mtime = source.stat().st_mtime_ns
            return str(mtime % (10**10))
        except OSError:
            return "v0"

    @staticmethod
    def _thumbnail_is_stale(source: Path, target: Path) -> bool:
        try:
            return target.stat().st_mtime < source.stat().st_mtime
        except OSError:
            return True

    @staticmethod
    def _sha256_hex(value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()
