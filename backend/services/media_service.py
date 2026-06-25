"""Local media artifact service - translated from Java.

Handles local media file operations using ffmpeg and PIL/Pillow:
- Thumbnail generation for images (local and remote)
- Video frame extraction for thumbnails
- Video concatenation
- Silent video generation from a poster image
- Text/image/binary artifact storage
- Image data URI generation
- Artifact copy/materialize from URL
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Configuration (simplified — replace with your own config as needed)
# ---------------------------------------------------------------------------


class JiandouStorageProperties:
    """Storage properties, mirroring the Java JiandouStorageProperties."""

    def __init__(
        self,
        root_dir: str | Path = "./storage",
        public_base_url: str = "",
        externally_accessible_base_url: str = "",
        storage_key_prefix: str = "",
    ):
        self._root_dir = Path(root_dir).resolve()
        self._public_base_url = public_base_url.rstrip("/")
        self._externally_accessible_base_url = externally_accessible_base_url.rstrip("/")
        self._storage_key_prefix = self._clean_prefix(storage_key_prefix)

    def resolve_root_dir(self) -> Path:
        return self._root_dir

    def build_public_url(self, relative_path: str) -> str:
        relative = relative_path.lstrip("/")
        return f"/storage/{relative}"

    def build_externally_accessible_url(self, public_url: str) -> str:
        normalized = (public_url or "").replace("\\", "/").strip()
        if normalized.startswith("/storage/") and self._public_base_url:
            return f"{self._public_base_url}/{self._prefixed_key(normalized[len('/storage/') :].lstrip('/'))}"
        if self._externally_accessible_base_url:
            return f"{self._externally_accessible_base_url}{normalized}"
        return normalized

    def resolve_public_url(self, public_url: str) -> Path | None:
        """Resolve a public URL (/storage/...) to an absolute filesystem path."""
        normalized = public_url.replace("\\", "/").strip()
        if normalized.startswith("/storage/"):
            resolved = self._root_dir / normalized[len("/storage/") :].lstrip("/")
            return resolved.resolve()
        # If it starts with our public base URL prefix, resolve relative to root
        prefix = self._public_base_url if self._public_base_url else "/storage"
        if normalized.startswith(prefix):
            relative = normalized[len(prefix) :].lstrip("/")
            local_key = self._local_key_from_public_relative(relative)
            if local_key is None:
                return None
            resolved = self._root_dir / local_key
            return resolved.resolve()
        return None

    def _prefixed_key(self, relative_path: str) -> str:
        key = relative_path.lstrip("/")
        if not self._storage_key_prefix:
            return key
        if key == self._storage_key_prefix or key.startswith(f"{self._storage_key_prefix}/"):
            return key
        return f"{self._storage_key_prefix}/{key}" if key else self._storage_key_prefix

    def _local_key_from_public_relative(self, relative_path: str) -> str | None:
        key = relative_path.lstrip("/")
        if not self._storage_key_prefix:
            return key
        if key.startswith(f"{self._storage_key_prefix}/"):
            return key[len(self._storage_key_prefix) + 1 :]
        return None

    @staticmethod
    def _clean_prefix(value: str) -> str:
        return "/".join(part for part in (value or "").replace("\\", "/").split("/") if part and part != ".")


# ---------------------------------------------------------------------------
# Artifact DTOs (mirroring Java records)
# ---------------------------------------------------------------------------


@dataclass
class TextArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int
    mime_type: str


@dataclass
class ImageArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int
    width: int
    height: int
    mime_type: str


@dataclass
class VideoArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int
    width: int
    height: int
    duration_seconds: int
    has_audio: bool
    mime_type: str


@dataclass
class StoredArtifact:
    file_name: str
    absolute_path: str
    public_url: str
    size_bytes: int


# ---------------------------------------------------------------------------
# LocalMediaArtifactService
# ---------------------------------------------------------------------------


class LocalMediaArtifactService:
    """Handles local media file operations.

    Mirrors the Java LocalMediaArtifactService, including:
    - Writing text/image/video artifacts to local storage
    - Generating thumbnails for images (local and remote URLs)
    - Extracting video frames via ffmpeg
    - Concat videos via ffmpeg
    - Generating image data URIs
    - Copying / materializing artifacts
    """

    def __init__(
        self,
        storage_properties: JiandouStorageProperties,
        ffmpeg_bin: str = "ffmpeg",
        remote_object_store: object | None = None,
    ):
        self._storage_properties = storage_properties
        self._storage_root = storage_properties.resolve_root_dir()
        self._ffmpeg_bin = ffmpeg_bin.strip() if ffmpeg_bin else "ffmpeg"
        self._remote_object_store = remote_object_store
        self._http_session = requests.Session()
        self._http_session.max_redirects = 10

    # ---- Public high-level API -------------------------------------------

    def write_text(self, relative_dir: str, file_name: str, content: str) -> TextArtifact:
        """Write a text artifact to storage.

        Args:
            relative_dir: Directory relative to storage root.
            file_name: Output file name.
            content: Text content to write.

        Returns:
            TextArtifact describing the written file.
        """
        try:
            output_dir = self._ensure_directory(relative_dir)
            output = output_dir / file_name
            output.write_text(content if content else "", encoding="utf-8")
            return TextArtifact(
                file_name=file_name,
                absolute_path=str(output.resolve()),
                public_url=self._publish_path(output, relative_dir, file_name, "text/markdown"),
                size_bytes=output.stat().st_size,
                mime_type="text/markdown",
            )
        except OSError as ex:
            raise RuntimeError(f"text artifact write failed: {ex}") from ex

    def write_prompt_card(
        self,
        relative_dir: str,
        file_name: str,
        width: int,
        height: int,
        title: str,
        subtitle: str,
        body_text: str,
    ) -> ImageArtifact:
        """Generate a PNG prompt card image with gradient background and text.

        Args:
            relative_dir: Directory relative to storage root.
            file_name: Output file name (should end in .png).
            width: Image width in pixels.
            height: Image height in pixels.
            title: Title text.
            subtitle: Subtitle text.
            body_text: Body text (will be wrapped).

        Returns:
            ImageArtifact describing the written image.
        """
        try:
            output_dir = self._ensure_directory(relative_dir)
            output = output_dir / file_name

            img = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(img)

            # Gradient background (dark blue)
            for y in range(height):
                ratio = y / max(height, 1)
                r = int(12 + (32 - 12) * ratio)
                g = int(20 + (74 - 20) * ratio)
                b = int(36 + (135 - 36) * ratio)
                for x in range(width):
                    draw.point((x, y), fill=(r, g, b))

            margin = max(24, min(width, height) // 20)
            card_width = max(180, width - margin * 2)

            # Card background (semi-transparent white)
            card_top = margin
            card_height = max(112, height // 8)
            draw.rounded_rectangle(
                [margin, card_top, margin + card_width, card_top + card_height],
                radius=24,
                fill=(255, 255, 255, 228),
            )

            # Title
            title_font_size = max(20, min(width // 18, 42))
            try:
                title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", title_font_size)
            except OSError:
                title_font = ImageFont.load_default()
            safe_title = title.strip() if title else "MEDIA PLACEHOLDER"
            draw.text(
                (margin + 24, card_top + 24),
                safe_title,
                fill=(15, 23, 42),
                font=title_font,
            )

            # Subtitle
            sub_font_size = max(14, min(width // 34, 24))
            try:
                sub_font = ImageFont.truetype("DejaVuSans.ttf", sub_font_size)
            except OSError:
                sub_font = ImageFont.load_default()
            safe_subtitle = subtitle.strip() if subtitle else "Python local render"
            draw.text(
                (margin + 24, card_top + card_height - sub_font_size - 12),
                safe_subtitle,
                fill=(15, 23, 42),
                font=sub_font,
            )

            # Body text
            max_chars = max(18, width // 24)
            lines = self._wrap_text(body_text, max_chars)
            line_height = max(24, min(height // 18, 34))
            try:
                body_font = ImageFont.truetype("DejaVuSans.ttf", max(12, min(width // 34, 18)))
            except OSError:
                body_font = ImageFont.load_default()
            start_y = margin + card_height + 24
            text_color = (241, 245, 249)
            for i, line in enumerate(lines[:8]):
                draw.text(
                    (margin + 24, start_y + i * line_height),
                    line,
                    fill=text_color,
                    font=body_font,
                )

            img.save(output, "PNG")
            return ImageArtifact(
                file_name=file_name,
                absolute_path=str(output.resolve()),
                public_url=self._publish_path(output, relative_dir, file_name, "image/png"),
                size_bytes=output.stat().st_size,
                width=width,
                height=height,
                mime_type="image/png",
            )
        except Exception as ex:
            raise RuntimeError(f"image artifact write failed: {ex}") from ex

    def write_silent_video(
        self,
        relative_dir: str,
        file_name: str,
        width: int,
        height: int,
        duration_seconds: int,
        poster: ImageArtifact,
    ) -> VideoArtifact:
        """Create a silent video from a poster image using ffmpeg.

        Args:
            relative_dir: Directory relative to storage root.
            file_name: Output file name (should end in .mp4).
            width: Video width in pixels.
            height: Video height in pixels.
            duration_seconds: Duration of the video.
            poster: ImageArtifact of the poster image to loop.

        Returns:
            VideoArtifact describing the created video.
        """
        try:
            output_dir = self._ensure_directory(relative_dir)
            output = output_dir / file_name

            cmd = [
                self._ffmpeg_bin,
                "-y",
                "-loop",
                "1",
                "-i",
                poster.absolute_path,
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t",
                str(max(1, duration_seconds)),
                "-vf",
                f"scale={width}:{height},format=yuv420p",
                "-r",
                "24",
                "-shortest",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(output),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0 or not output.exists():
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg failed")

            return VideoArtifact(
                file_name=file_name,
                absolute_path=str(output.resolve()),
                public_url=self._publish_path(output, relative_dir, file_name, "video/mp4"),
                size_bytes=output.stat().st_size,
                width=width,
                height=height,
                duration_seconds=max(1, duration_seconds),
                has_audio=True,
                mime_type="video/mp4",
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg timed out")
        except Exception as ex:
            raise RuntimeError(f"video artifact write failed: {ex}") from ex

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

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        """Convert a local storage image to a data URI for video model compatibility.

        Args:
            public_url: Local /storage path.

        Returns:
            Data URI string, or raises if invalid.
        """
        abs_path = self._resolve_absolute_path(public_url)
        if not abs_path:
            raise ValueError("source public url is not a local storage path")

        source = Path(abs_path).resolve()
        if not source.is_file():
            raise RuntimeError("source image does not exist")

        size_bytes = source.stat().st_size
        if size_bytes > 30 * 1024 * 1024:
            raise RuntimeError("source image exceeds 30 MB")

        mime_type = self._image_mime_type(source)
        if not mime_type.startswith("image/"):
            raise RuntimeError("source file is not an image")

        import base64

        encoded = base64.b64encode(source.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def copy_artifact(self, source_public_url: str, relative_dir: str, file_name: str) -> StoredArtifact:
        """Copy a local storage artifact to a new location.

        Args:
            source_public_url: Public URL of the source artifact.
            relative_dir: Destination directory relative to storage root.
            file_name: Destination file name.

        Returns:
            StoredArtifact describing the copy.
        """
        abs_path = self._resolve_absolute_path(source_public_url)
        if not abs_path:
            raise ValueError("source public url is not a local storage path")

        source = Path(abs_path).resolve()
        if not source.exists():
            raise RuntimeError("source artifact does not exist")

        output_dir = self._ensure_directory(relative_dir)
        target = (output_dir / file_name).resolve()
        if source != target:
            shutil.copy2(source, target)

        return StoredArtifact(
            file_name=file_name,
            absolute_path=str(target),
            public_url=self._publish_path(target, relative_dir, file_name),
            size_bytes=target.stat().st_size,
        )

    def materialize_artifact(self, source_url: str, relative_dir: str, file_name: str) -> StoredArtifact:
        """Materialize an artifact from URL (local or remote).

        If the URL is a local storage path, copies it.
        Otherwise downloads from the remote URL.

        Args:
            source_url: Source URL (local or remote).
            relative_dir: Destination directory relative to storage root.
            file_name: Destination file name.

        Returns:
            StoredArtifact describing the materialized file.
        """
        abs_path = self._resolve_absolute_path(source_url)
        if abs_path:
            return self.copy_artifact(source_url, relative_dir, file_name)

        normalized = (source_url or "").strip()
        if not normalized:
            raise ValueError("source url is required")

        output_dir = self._ensure_directory(relative_dir)
        target = (output_dir / file_name).resolve()

        try:
            resp = self._http_session.get(normalized, timeout=120)
            resp.raise_for_status()
            target.write_bytes(resp.content)
            return StoredArtifact(
                file_name=file_name,
                absolute_path=str(target),
                public_url=self._publish_path(target, relative_dir, file_name),
                size_bytes=target.stat().st_size,
            )
        except Exception as ex:
            raise RuntimeError(f"artifact materialize failed: {ex}") from ex

    def write_binary(self, relative_dir: str, file_name: str, data: bytes) -> StoredArtifact:
        """Write binary data to storage.

        Args:
            relative_dir: Directory relative to storage root.
            file_name: Output file name.
            data: Binary data to write.

        Returns:
            StoredArtifact describing the written file.
        """
        output_dir = self._ensure_directory(relative_dir)
        target = (output_dir / file_name).resolve()
        target.write_bytes(data if data else b"")
        return StoredArtifact(
            file_name=file_name,
            absolute_path=str(target),
            public_url=self._publish_path(target, relative_dir, file_name),
            size_bytes=target.stat().st_size,
        )

    def concat_videos(self, relative_dir: str, file_name: str, source_public_urls: list[str]) -> StoredArtifact:
        """Concatenate multiple local video files using ffmpeg.

        Tries ``-c copy`` (fast, stream-copy) first.  If that fails — typically
        because source videos have incompatible codecs / resolutions — falls
        back to re-encoding every input to H.264 + AAC before concatenation so
        the result is always playable.

        Args:
            relative_dir: Output directory relative to storage root.
            file_name: Output file name.
            source_public_urls: Public URLs of source videos (at least 2).

        Returns:
            StoredArtifact describing the concatenated video.
        """
        if not source_public_urls or len(source_public_urls) < 2:
            raise ValueError("at least two source videos are required")

        source_paths: list[Path] = []
        for url in source_public_urls:
            abs_path = self._resolve_absolute_path(url)
            if not abs_path:
                raise ValueError("source public url is not a local storage path")
            source = Path(abs_path).resolve()
            if not source.exists():
                raise RuntimeError("source video does not exist")
            source_paths.append(source)

        output_dir = self._ensure_directory(relative_dir)
        output = (output_dir / file_name).resolve()

        # Create a temp concat list file
        tmp_list = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        try:
            for sp in source_paths:
                escaped = str(sp).replace("'", "'\\''")
                tmp_list.write(f"file '{escaped}'\n")
            tmp_list.close()

            # --- Fast path: stream copy (no re-encode) ---
            copy_cmd = [
                self._ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                tmp_list.name,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ]

            result = subprocess.run(
                copy_cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0 or not output.exists():
                # Stream-copy failed (likely codec mismatch).  Re-encode.
                import logging

                logging.getLogger(__name__).info(
                    "concat -c copy failed (%s), retrying with re-encode",
                    result.stderr.strip()[:200],
                )
                if output.exists():
                    output.unlink()

                reencode_cmd = [
                    self._ffmpeg_bin,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    tmp_list.name,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-movflags",
                    "+faststart",
                    str(output),
                ]
                result = subprocess.run(
                    reencode_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode != 0 or not output.exists():
                    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg concat failed")

            return StoredArtifact(
                file_name=file_name,
                absolute_path=str(output),
                public_url=self._publish_path(output, relative_dir, file_name),
                size_bytes=output.stat().st_size,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg concat timed out")
        finally:
            os.unlink(tmp_list.name)

    def build_externally_accessible_url(self, public_url: str) -> str:
        return self._storage_properties.build_externally_accessible_url(public_url)

    def resolve_absolute_path(self, public_url: str) -> str:
        return self._resolve_absolute_path(public_url)

    # ---- Private helpers --------------------------------------------------

    def _ensure_directory(self, relative_dir: str) -> Path:
        directory = (self._storage_root / relative_dir).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _build_public_url(self, relative_dir: str, file_name: str) -> str:
        normalized_dir = (relative_dir or "").replace("\\", "/")
        return self._storage_properties.build_public_url(f"{normalized_dir}/{file_name}")

    def _publish_path(self, path: Path, relative_dir: str, file_name: str, content_type: str = "") -> str:
        """Return a stable local URL for generated task artifacts."""
        local_public_url = self._build_public_url(relative_dir, file_name)
        return local_public_url

    def _resolve_absolute_path(self, public_url: str) -> str:
        resolved = self._storage_properties.resolve_public_url(public_url)
        return str(resolved) if resolved else ""

    def _public_url_for_storage_path(self, path: Path) -> str:
        relative = path.resolve().relative_to(self._storage_root.resolve())
        storage_key = str(relative).replace("\\", "/")
        return self._publish_path(path, str(Path(storage_key).parent), Path(storage_key).name)

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

    @staticmethod
    def _image_mime_type(source: Path) -> str:
        """Determine MIME type from file extension (os independent)."""
        name = source.name.lower()
        if name.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if name.endswith(".webp"):
            return "image/webp"
        if name.endswith(".bmp"):
            return "image/bmp"
        if name.endswith((".tiff", ".tif")):
            return "image/tiff"
        if name.endswith(".gif"):
            return "image/gif"
        if name.endswith(".heic"):
            return "image/heic"
        if name.endswith(".heif"):
            return "image/heif"
        return "image/png"

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

    @staticmethod
    def _is_http_url(value: str) -> bool:
        try:
            parsed = urlparse(value.strip())
            return parsed.scheme in ("http", "https") and bool(parsed.hostname)
        except Exception:
            return False

    @staticmethod
    def _wrap_text(text: str, max_chars_per_line: int) -> list[str]:
        normalized = (text or "").replace("\n", " ").strip()
        if not normalized:
            return ["placeholder output"]
        lines: list[str] = []
        cursor = 0
        while cursor < len(normalized):
            end = min(len(normalized), cursor + max(12, max_chars_per_line))
            lines.append(normalized[cursor:end])
            cursor = end
        return lines

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        for v in values:
            if v and v.strip():
                return v.strip()
        return ""
