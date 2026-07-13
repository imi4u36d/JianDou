"""Artifact persistence and materialization for the local media facade."""

from __future__ import annotations

import base64
import mimetypes
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.services.media_service import StoredArtifact, TextArtifact


class LocalMediaArtifactStorageService:
    """Own local artifact I/O while delegating storage policy to the facade."""

    def __init__(self, owner: Any):
        self._owner = owner

    def write_text(self, relative_dir: str, file_name: str, content: str) -> TextArtifact:
        from backend.services.media_service import TextArtifact

        try:
            output = self._owner._ensure_directory(relative_dir) / file_name
            output.write_text(content if content else "", encoding="utf-8")
            return TextArtifact(
                file_name=file_name,
                absolute_path=str(output.resolve()),
                public_url=self._owner._publish_path(output, relative_dir, file_name, "text/markdown"),
                size_bytes=output.stat().st_size,
                mime_type="text/markdown",
            )
        except OSError as ex:
            raise RuntimeError(f"text artifact write failed: {ex}") from ex

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        absolute_path = self._owner._resolve_absolute_path(public_url)
        if not absolute_path:
            raise ValueError("source public url is not a local storage path")
        source = Path(absolute_path).resolve()
        if not source.is_file():
            raise RuntimeError("source image does not exist")
        if source.stat().st_size > 30 * 1024 * 1024:
            raise RuntimeError("source image exceeds 30 MB")
        mime_type = self._owner._image_mime_type(source)
        if not mime_type.startswith("image/"):
            raise RuntimeError("source file is not an image")
        encoded = base64.b64encode(source.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def publish_local_artifact(self, public_url: str, content_type: str = "", storage_key: str = "") -> str:
        normalized = (public_url or "").strip()
        if not normalized:
            return ""
        if self._owner._is_http_url(normalized):
            return normalized
        absolute_path = self._owner._resolve_absolute_path(normalized)
        if not absolute_path:
            return self._owner._storage_properties.build_externally_accessible_url(normalized)
        source = Path(absolute_path).resolve()
        if not source.is_file():
            raise RuntimeError("source artifact does not exist")
        remote_store = self._owner._remote_object_store
        if remote_store is not None and hasattr(remote_store, "put_object"):
            key = (storage_key or "").strip()
            if not key:
                key = str(source.relative_to(self._owner._storage_root.resolve())).replace("\\", "/")
            mime = content_type or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            stored = remote_store.put_object(key, source.read_bytes(), mime, source.name)
            return str(getattr(stored, "public_url", "") or "")
        return self._owner._storage_properties.build_externally_accessible_url(normalized)

    def copy_artifact(self, source_public_url: str, relative_dir: str, file_name: str) -> StoredArtifact:
        from backend.services.media_service import StoredArtifact

        absolute_path = self._owner._resolve_absolute_path(source_public_url)
        if not absolute_path:
            raise ValueError("source public url is not a local storage path")
        source = Path(absolute_path).resolve()
        if not source.exists():
            raise RuntimeError("source artifact does not exist")
        target = (self._owner._ensure_directory(relative_dir) / file_name).resolve()
        if source != target:
            shutil.copy2(source, target)
        return self._stored_artifact(StoredArtifact, target, relative_dir, file_name)

    def materialize_artifact(self, source_url: str, relative_dir: str, file_name: str) -> StoredArtifact:
        from backend.services.media_service import StoredArtifact

        if self._owner._resolve_absolute_path(source_url):
            return self.copy_artifact(source_url, relative_dir, file_name)
        normalized = (source_url or "").strip()
        if not normalized:
            raise ValueError("source url is required")
        target = (self._owner._ensure_directory(relative_dir) / file_name).resolve()
        try:
            response = self._owner._http_session.get(normalized, timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
            return self._stored_artifact(StoredArtifact, target, relative_dir, file_name)
        except Exception as ex:
            raise RuntimeError(f"artifact materialize failed: {ex}") from ex

    def write_binary(self, relative_dir: str, file_name: str, data: bytes) -> StoredArtifact:
        from backend.services.media_service import StoredArtifact

        target = (self._owner._ensure_directory(relative_dir) / file_name).resolve()
        target.write_bytes(data if data else b"")
        return self._stored_artifact(StoredArtifact, target, relative_dir, file_name)

    def _stored_artifact(self, artifact_type: Any, target: Path, relative_dir: str, file_name: str) -> Any:
        return artifact_type(
            file_name=file_name,
            absolute_path=str(target),
            public_url=self._owner._publish_path(target, relative_dir, file_name),
            size_bytes=target.stat().st_size,
        )
