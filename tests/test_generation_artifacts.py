from __future__ import annotations

from backend.domain.generation_run import GenerationModelKinds
from backend.services.generation_artifacts import (
    GenerationArtifactStore,
    extension_from_mime_or_url,
    mime_from_name,
)


def test_extension_from_mime_or_url_prefers_mime_then_url_then_media_default() -> None:
    assert extension_from_mime_or_url("image/png", "https://example.test/file.jpeg", GenerationModelKinds.IMAGE) == "png"
    assert extension_from_mime_or_url("image/jpeg", "", GenerationModelKinds.IMAGE) == "jpg"
    assert extension_from_mime_or_url("video/webm", "", GenerationModelKinds.VIDEO) == "webm"
    assert extension_from_mime_or_url("", "https://example.test/video.MP4?token=secret", GenerationModelKinds.VIDEO) == "mp4"
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


def test_artifact_store_uses_run_directory_defaults(tmp_path) -> None:
    store = GenerationArtifactStore(str(tmp_path), "https://app.example.test")
    artifact = store.write_binary_artifact("run_default", {}, "image", "", b"data")

    assert artifact["fileName"] == "image.bin"
    assert artifact["publicUrl"] == "/storage/gen/_runs/run_default/image.bin"
    assert artifact["mimeType"] == "application/octet-stream"
    assert (tmp_path / "gen/_runs/run_default/image.bin").read_bytes() == b"data"
