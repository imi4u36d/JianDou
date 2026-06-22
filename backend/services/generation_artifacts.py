"""Artifact storage helpers for generation runs."""

from __future__ import annotations

import logging
import os
from typing import Any

from backend.domain.generation_run import GenerationModelKinds
from backend.shared import map_value, string_value

logger = logging.getLogger(__name__)

class GenerationArtifactStore:
    def __init__(self, storage_root: str, web_origin: str) -> None:
        self._storage_root = storage_root
        self._web_origin = web_origin

    def storage_relative_dir(self, request: dict[str, Any], run_id: str) -> str:
        storage = map_value(request.get("storage"))
        configured = string_value(storage.get("relativeDir"))
        return configured if configured else f"gen/_runs/{run_id}"

    def storage_file_stem(self, request: dict[str, Any], fallback: str) -> str:
        storage = map_value(request.get("storage"))
        configured = string_value(storage.get("fileStem"))
        return configured if configured else fallback

    def storage_file_name(self, request: dict[str, Any], fallback: str) -> str:
        storage = map_value(request.get("storage"))
        configured = string_value(storage.get("fileName"))
        return configured if configured else fallback

    def write_text_artifact(
        self, run_id: str, request: dict[str, Any], file_name: str, content: str
    ) -> dict[str, Any]:
        relative_dir = self.storage_relative_dir(request, run_id)
        actual_name = self.storage_file_name(request, file_name)
        file_path = os.path.join(self._storage_root, relative_dir, actual_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as output:
            output.write(content)
        public_url = f"/storage/{relative_dir}/{actual_name}"
        return {
            "absolutePath": os.path.abspath(file_path),
            "publicUrl": public_url,
            "fileName": actual_name,
        }

    def write_binary_artifact(
        self,
        run_id: str,
        request: dict[str, Any],
        file_stem: str,
        extension: str,
        data: bytes,
    ) -> dict[str, Any]:
        relative_dir = self.storage_relative_dir(request, run_id)
        ext = extension if extension else "bin"
        file_name = f"{self.storage_file_stem(request, file_stem)}.{ext}"
        file_path = os.path.join(self._storage_root, relative_dir, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as output:
            output.write(data)
        public_url = f"/storage/{relative_dir}/{file_name}"
        return {
            "fileName": file_name,
            "absolutePath": os.path.abspath(file_path),
            "publicUrl": public_url,
            "sizeBytes": len(data),
            "mimeType": mime_from_name(file_name),
        }

    def materialize_binary_artifact(
        self, run_id: str, relative_dir: str, file_stem: str, source_url: str
    ) -> dict[str, Any]:
        ext = extension_from_mime_or_url("", source_url, GenerationModelKinds.VIDEO)
        file_name = f"{file_stem}.{ext}"
        file_path = os.path.join(self._storage_root, relative_dir, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        size_bytes = 0
        try:
            import httpx

            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                response = client.get(source_url)
                response.raise_for_status()
                with open(file_path, "wb") as output:
                    output.write(response.content)
                size_bytes = len(response.content)
        except Exception as ex:
            logger.warning("Failed to download from %s: %s", source_url, ex)
            with open(file_path, "wb") as output:
                output.write(b"")
        public_url = f"/storage/{relative_dir}/{file_name}"
        return {
            "fileName": file_name,
            "absolutePath": os.path.abspath(file_path),
            "publicUrl": public_url,
            "sizeBytes": size_bytes,
            "mimeType": mime_from_name(file_name),
        }

    def build_externally_accessible_url(self, public_url: str) -> str:
        if public_url and public_url.startswith("/"):
            return f"{self._web_origin.rstrip('/')}{public_url}"
        return public_url or ""

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        return ""

def extension_from_mime_or_url(mime_type: str, source_url: str, media_type: str) -> str:
    normalized_mime = mime_type.lower() if mime_type else ""
    if normalized_mime.startswith("image/png"):
        return "png"
    if normalized_mime.startswith("image/jpeg"):
        return "jpg"
    if normalized_mime.startswith("image/webp"):
        return "webp"
    if normalized_mime.startswith("video/mp4"):
        return "mp4"
    if normalized_mime.startswith("video/webm"):
        return "webm"
    if source_url:
        path = source_url.split("?")[0]
        dot = path.rfind(".")
        if dot >= 0 and dot < len(path) - 1:
            return path[dot + 1 :].lower()
    return "png" if media_type == GenerationModelKinds.IMAGE else "mp4"

def mime_from_name(file_name: str) -> str:
    lower = file_name.lower() if file_name else ""
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".webm"):
        return "video/webm"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"

