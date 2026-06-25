from __future__ import annotations

import pytest

from backend.services.media_service import JiandouStorageProperties, LocalMediaArtifactService

pytestmark = pytest.mark.service


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


def test_media_service_publishes_written_binary_to_remote_store(tmp_path) -> None:
    remote = _FakeRemoteStore()
    service = LocalMediaArtifactService(
        JiandouStorageProperties(root_dir=tmp_path, public_base_url="/storage"),
        remote_object_store=remote,
    )

    artifact = service.write_binary("tasks/task_1/running", "clip1-first.png", b"image")

    assert artifact.public_url == "https://cdn.example.test/tasks/task_1/running/clip1-first.png"
    assert artifact.size_bytes == len(b"image")
    assert remote.puts == [
        ("tasks/task_1/running/clip1-first.png", b"image", "image/png", "clip1-first.png")
    ]
    assert (tmp_path / "tasks/task_1/running/clip1-first.png").read_bytes() == b"image"


def test_storage_properties_maps_prefixed_oss_urls_to_local_cache(tmp_path) -> None:
    props = JiandouStorageProperties(
        root_dir=tmp_path,
        public_base_url="https://cdn.example.test",
        storage_key_prefix="dev",
    )

    assert props.build_public_url("tasks/task_1/clip.png") == "https://cdn.example.test/dev/tasks/task_1/clip.png"
    assert props.build_externally_accessible_url("/storage/tasks/task_1/clip.png") == (
        "https://cdn.example.test/dev/tasks/task_1/clip.png"
    )
    assert props.resolve_public_url("https://cdn.example.test/dev/tasks/task_1/clip.png") == (
        tmp_path / "tasks/task_1/clip.png"
    ).resolve()
    assert props.resolve_public_url("https://cdn.example.test/tasks/task_1/clip.png") is None
