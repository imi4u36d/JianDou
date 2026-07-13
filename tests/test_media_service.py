from __future__ import annotations

import pytest
from PIL import Image

from backend.services.media_artifact_storage import LocalMediaArtifactStorageService
from backend.services.media_prompt_cards import LocalMediaPromptCardRenderer
from backend.services.media_service import JiandouStorageProperties, LocalMediaArtifactService
from backend.services.media_thumbnails import LocalMediaThumbnailService
from backend.services.media_video_operations import LocalMediaVideoService

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


def test_media_service_keeps_written_binary_in_local_storage(tmp_path) -> None:
    remote = _FakeRemoteStore()
    service = LocalMediaArtifactService(
        JiandouStorageProperties(root_dir=tmp_path, public_base_url="/storage"),
        remote_object_store=remote,
    )

    artifact = service.write_binary("tasks/task_1/running", "clip1-first.png", b"image")

    assert artifact.public_url == "/storage/tasks/task_1/running/clip1-first.png"
    assert artifact.size_bytes == len(b"image")
    assert remote.puts == []
    assert (tmp_path / "tasks/task_1/running/clip1-first.png").read_bytes() == b"image"
    assert isinstance(service._artifact_storage_service(), LocalMediaArtifactStorageService)


def test_storage_properties_maps_prefixed_oss_urls_to_local_cache(tmp_path) -> None:
    props = JiandouStorageProperties(
        root_dir=tmp_path,
        public_base_url="https://cdn.example.test",
        storage_key_prefix="dev",
    )

    assert props.build_public_url("tasks/task_1/clip.png") == "/storage/tasks/task_1/clip.png"
    assert props.build_externally_accessible_url("/storage/tasks/task_1/clip.png") == (
        "https://cdn.example.test/dev/tasks/task_1/clip.png"
    )
    assert (
        props.resolve_public_url("https://cdn.example.test/dev/tasks/task_1/clip.png")
        == (tmp_path / "tasks/task_1/clip.png").resolve()
    )
    assert props.resolve_public_url("/storage/tasks/task_1/clip.png") == (tmp_path / "tasks/task_1/clip.png").resolve()
    assert props.resolve_public_url("https://cdn.example.test/tasks/task_1/clip.png") is None


def test_media_service_delegates_and_caches_local_image_thumbnail(tmp_path) -> None:
    props = JiandouStorageProperties(root_dir=tmp_path)
    service = LocalMediaArtifactService(props)
    source = tmp_path / "tasks" / "task_1" / "poster.png"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (320, 180), (32, 64, 128)).save(source)

    thumbnail_url = service.ensure_image_thumbnail("/storage/tasks/task_1/poster.png", 160)

    assert isinstance(service._thumbnail_service(), LocalMediaThumbnailService)
    assert thumbnail_url.startswith("/storage/thumbs/tasks/task_1/poster-w160-")
    thumbnail = props.resolve_public_url(thumbnail_url)
    assert thumbnail is not None and thumbnail.is_file()
    with Image.open(thumbnail) as image:
        assert image.size == (160, 90)
    assert service.ensure_image_thumbnail("/storage/tasks/task_1/poster.png", 160) == thumbnail_url


def test_media_service_delegates_ffmpeg_commands_to_video_service(tmp_path) -> None:
    service = LocalMediaArtifactService(JiandouStorageProperties(root_dir=tmp_path), ffmpeg_bin="custom-ffmpeg")
    video_service = service._video_service()

    assert isinstance(video_service, LocalMediaVideoService)
    assert video_service._concat_command("inputs.txt", tmp_path / "output.mp4", reencode=False) == [
        "custom-ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "inputs.txt",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(tmp_path / "output.mp4"),
    ]
    with pytest.raises(ValueError, match="at least two"):
        service.concat_videos("tasks/task_1", "output.mp4", [])


def test_media_service_delegates_prompt_card_rendering(tmp_path) -> None:
    service = LocalMediaArtifactService(JiandouStorageProperties(root_dir=tmp_path))

    artifact = service.write_prompt_card(
        "tasks/task_1",
        "prompt.png",
        320,
        180,
        "标题",
        "副标题",
        "用于验证提示卡渲染协作者",
    )

    assert isinstance(service._prompt_card_renderer(), LocalMediaPromptCardRenderer)
    assert artifact.public_url == "/storage/tasks/task_1/prompt.png"
    with Image.open(artifact.absolute_path) as image:
        assert image.size == (320, 180)
