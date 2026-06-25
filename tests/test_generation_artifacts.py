from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

pytestmark = pytest.mark.service
from backend.domain.generation_run import GenerationModelKinds
from backend.services.generation_artifacts import (
    GenerationArtifactStore,
    extension_from_mime_or_url,
    mime_from_name,
)


class _FakeRemoteStore:
    def __init__(self) -> None:
        self.puts: list[tuple[str, bytes, str, str]] = []

    def put_object(
        self,
        storage_key: str,
        content: bytes,
        content_type: str = "",
        file_name: str = "",
    ):
        self.puts.append((storage_key, content, content_type, file_name))

        class _Stored:
            public_url = f"https://cdn.example.test/{storage_key}"

        return _Stored()


def test_extension_from_mime_or_url_prefers_mime_then_url_then_media_default() -> None:
    assert (
        extension_from_mime_or_url("image/png", "https://example.test/file.jpeg", GenerationModelKinds.IMAGE) == "png"
    )
    assert extension_from_mime_or_url("image/jpeg", "", GenerationModelKinds.IMAGE) == "jpg"
    assert extension_from_mime_or_url("video/webm", "", GenerationModelKinds.VIDEO) == "webm"
    assert (
        extension_from_mime_or_url("", "https://example.test/video.MP4?token=secret", GenerationModelKinds.VIDEO)
        == "mp4"
    )
    assert extension_from_mime_or_url("", "", GenerationModelKinds.IMAGE) == "png"
    assert extension_from_mime_or_url("", "", GenerationModelKinds.VIDEO) == "mp4"


def test_mime_from_name_maps_known_media_extensions() -> None:
    assert mime_from_name("clip.mp4") == "video/mp4"
    assert mime_from_name("clip.webm") == "video/webm"
    assert mime_from_name("frame.png") == "image/png"
    assert mime_from_name("frame.jpeg") == "image/jpeg"
    assert mime_from_name("frame.webp") == "image/webp"
    assert mime_from_name("data.bin") == "application/octet-stream"


def test_artifact_store_resolves_storage_overrides_and_writes_files(tmp_path) -> None:
    store = GenerationArtifactStore(str(tmp_path), "https://app.example.test/")
    request = {
        "storage": {
            "relativeDir": "tasks/task_1/running",
            "fileName": "storyboard-custom.md",
            "fileStem": "clip-custom",
        }
    }

    text_artifact = store.write_text_artifact("run_1", request, "storyboard.md", "hello")
    binary_artifact = store.write_binary_artifact("run_1", request, "clip", "png", b"image-bytes")

    assert text_artifact["fileName"] == "storyboard-custom.md"
    assert text_artifact["publicUrl"] == "/storage/tasks/task_1/running/storyboard-custom.md"
    assert (tmp_path / "tasks/task_1/running/storyboard-custom.md").read_text() == "hello"
    assert binary_artifact["fileName"] == "clip-custom.png"
    assert binary_artifact["publicUrl"] == "/storage/tasks/task_1/running/clip-custom.png"
    assert binary_artifact["sizeBytes"] == len(b"image-bytes")
    assert binary_artifact["mimeType"] == "image/png"
    assert (tmp_path / "tasks/task_1/running/clip-custom.png").read_bytes() == b"image-bytes"
    assert store.build_externally_accessible_url(binary_artifact["publicUrl"]) == (
        "https://app.example.test/storage/tasks/task_1/running/clip-custom.png"
    )
    assert (
        store.image_data_uri_from_public_url(binary_artifact["publicUrl"]) == "data:image/png;base64,aW1hZ2UtYnl0ZXM="
    )


def test_artifact_store_uses_run_directory_defaults(tmp_path) -> None:
    store = GenerationArtifactStore(str(tmp_path), "https://app.example.test")
    artifact = store.write_binary_artifact("run_default", {}, "image", "", b"data")

    assert artifact["fileName"] == "image.bin"
    assert artifact["publicUrl"] == "/storage/tasks/_runs/run_default/image.bin"
    assert artifact["mimeType"] == "application/octet-stream"
    assert (tmp_path / "tasks/_runs/run_default/image.bin").read_bytes() == b"data"


def test_artifact_store_keeps_generated_binary_local_even_with_remote_store(tmp_path) -> None:
    remote = _FakeRemoteStore()
    store = GenerationArtifactStore(str(tmp_path), "https://app.example.test", remote)

    artifact = store.write_binary_artifact("run_remote", {}, "image", "png", b"image")

    assert artifact["publicUrl"] == "/storage/tasks/_runs/run_remote/image.png"
    assert remote.puts == []
    assert (tmp_path / "tasks/_runs/run_remote/image.png").read_bytes() == b"image"


def test_artifact_store_resizes_generated_image_to_requested_dimensions(tmp_path) -> None:
    remote = _FakeRemoteStore()
    store = GenerationArtifactStore(str(tmp_path), "https://app.example.test", remote)
    request = {
        "input": {"width": 3840, "height": 2160},
        "storage": {
            "relativeDir": "tasks/task_4k/running",
            "fileStem": "workspace-image",
        },
    }
    source = _png_bytes(1672, 941)

    artifact = store.write_binary_artifact("run_4k", request, "image", "png", source)

    assert artifact["width"] == 3840
    assert artifact["height"] == 2160
    assert artifact["sourceWidth"] == 1672
    assert artifact["sourceHeight"] == 941
    assert artifact["resizedToRequestedDimensions"] is True
    assert artifact["publicUrl"] == "/storage/tasks/task_4k/running/workspace-image.png"
    assert remote.puts == []
    assert _image_size((tmp_path / "tasks/task_4k/running/workspace-image.png").read_bytes()) == (3840, 2160)


def _png_bytes(width: int, height: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), (18, 52, 86)).save(output, "PNG")
    return output.getvalue()


def _image_size(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        return image.size
