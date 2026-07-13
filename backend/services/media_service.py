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

from pathlib import Path
from urllib.parse import urlparse

import requests

from backend.services.media_artifact_storage import LocalMediaArtifactStorageService
from backend.services.media_artifacts import ImageArtifact, StoredArtifact, TextArtifact, VideoArtifact
from backend.services.media_prompt_cards import LocalMediaPromptCardRenderer
from backend.services.media_thumbnails import LocalMediaThumbnailService
from backend.services.media_video_operations import LocalMediaVideoService

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

    def _thumbnail_service(self) -> LocalMediaThumbnailService:
        return LocalMediaThumbnailService(self)

    def _artifact_storage_service(self) -> LocalMediaArtifactStorageService:
        return LocalMediaArtifactStorageService(self)

    def _video_service(self) -> LocalMediaVideoService:
        return LocalMediaVideoService(self)

    def _prompt_card_renderer(self) -> LocalMediaPromptCardRenderer:
        return LocalMediaPromptCardRenderer(self)

    # ---- Public high-level API -------------------------------------------

    def write_text(self, relative_dir: str, file_name: str, content: str) -> TextArtifact:
        return self._artifact_storage_service().write_text(relative_dir, file_name, content)

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
        return self._prompt_card_renderer().write_prompt_card(
            relative_dir,
            file_name,
            width,
            height,
            title,
            subtitle,
            body_text,
        )

    def write_silent_video(
        self,
        relative_dir: str,
        file_name: str,
        width: int,
        height: int,
        duration_seconds: int,
        poster: ImageArtifact,
    ) -> VideoArtifact:
        return self._video_service().write_silent_video(
            relative_dir,
            file_name,
            width,
            height,
            duration_seconds,
            poster,
        )

    def ensure_image_thumbnail(self, public_url: str, max_width: int) -> str:
        return self._thumbnail_service().ensure_image_thumbnail(public_url, max_width)

    def ensure_media_thumbnail(
        self,
        media_type: str,
        media_url: str,
        candidate_image_urls: list[str] | None,
        max_width: int,
    ) -> str:
        return self._thumbnail_service().ensure_media_thumbnail(
            media_type,
            media_url,
            candidate_image_urls,
            max_width,
        )

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        return self._artifact_storage_service().image_data_uri_from_public_url(public_url)

    def publish_local_artifact(self, public_url: str, content_type: str = "", storage_key: str = "") -> str:
        return self._artifact_storage_service().publish_local_artifact(public_url, content_type, storage_key)

    def copy_artifact(self, source_public_url: str, relative_dir: str, file_name: str) -> StoredArtifact:
        return self._artifact_storage_service().copy_artifact(source_public_url, relative_dir, file_name)

    def materialize_artifact(self, source_url: str, relative_dir: str, file_name: str) -> StoredArtifact:
        return self._artifact_storage_service().materialize_artifact(source_url, relative_dir, file_name)

    def write_binary(self, relative_dir: str, file_name: str, data: bytes) -> StoredArtifact:
        return self._artifact_storage_service().write_binary(relative_dir, file_name, data)

    def concat_videos(self, relative_dir: str, file_name: str, source_public_urls: list[str]) -> StoredArtifact:
        return self._video_service().concat_videos(relative_dir, file_name, source_public_urls)

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

    @staticmethod
    def _is_http_url(value: str) -> bool:
        try:
            parsed = urlparse(value.strip())
            return parsed.scheme in ("http", "https") and bool(parsed.hostname)
        except Exception:
            return False

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        for v in values:
            if v and v.strip():
                return v.strip()
        return ""
