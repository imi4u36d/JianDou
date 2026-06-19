from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler


def _task() -> TaskRecord:
    return TaskRecord(
        id="task_artifact",
        owner_user_id=7,
        title="Artifact Task",
        task_type="video_generation",
        request_snapshot={"assetType": "poster"},
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def test_create_video_material_uses_media_result_fallbacks_and_thumbnail_candidate(tmp_path: Path) -> None:
    media_service = _RecordingMediaService(tmp_path)
    assembler = TaskExecutionArtifactAssembler(media_service)

    material = assembler.create_video_material(
        _task(),
        {
            "id": "run_video",
            "result": {
                "modelInfo": {
                    "provider": "provider",
                    "resolvedModel": "video-model",
                },
            },
        },
        {
            "metadata": {
                "fileUrl": "https://provider.example/video.mp4",
                "remoteSourceUrl": "https://provider.example/source.mp4",
                "firstFrameUrl": "https://provider.example/first.png",
                "requestedLastFrameUrl": "https://provider.example/requested-last.png",
                "taskId": "remote_task",
            },
            "durationSeconds": "6.5",
            "width": "1280",
            "height": "720",
            "hasAudio": "true",
        },
        clip_index=2,
        fallback_duration_seconds=5,
    )

    assert media_service.materialized[0] == (
        "https://provider.example/video.mp4",
        "tasks/task_artifact/running",
        "clip2.mp4",
    )
    assert material["mediaType"] == "video"
    assert material["fileUrl"] == "/storage/clip2.mp4"
    assert material["remoteUrl"] == "https://provider.example/source.mp4"
    assert material["thumbnailUrl"] == "thumb-video-/storage/clip2.mp4"
    assert material["originProvider"] == "provider"
    assert material["originModel"] == "video-model"
    assert material["remoteTaskId"] == "remote_task"
    assert material["durationSeconds"] == 6.5
    assert material["width"] == 1280
    assert material["height"] == 720
    assert material["hasAudio"] is True
    assert material["metadata"]["lastFrameUrl"] == ""
    assert material["metadata"]["requestedLastFrameUrl"] == "https://provider.example/requested-last.png"


def test_extract_last_frame_url_reads_nested_role_image_url() -> None:
    assembler = TaskExecutionArtifactAssembler()

    assert (
        assembler.extract_last_frame_url({
            "frames": [
                {"role": "first_frame", "image_url": {"url": "https://example.test/first.png"}},
                {"role": "last_frame", "image_url": {"url": "https://example.test/last.png"}},
            ]
        })
        == "https://example.test/last.png"
    )


def test_create_image_result_preserves_remote_metadata_and_material_pointer(tmp_path: Path) -> None:
    media_service = _RecordingMediaService(tmp_path)
    assembler = TaskExecutionArtifactAssembler(media_service)
    image_file = tmp_path / "workspace.png"
    image_file.write_bytes(b"image")

    result = assembler.create_image_result(
        _task(),
        {"id": "run_image"},
        {
            "metadata": {
                "remoteSourceUrl": "https://provider.example/image.png",
                "referenceImageUrls": ["https://provider.example/ref.png"],
            },
            "width": 512,
            "height": 768,
        },
        {
            "id": "asset_1",
            "fileUrl": str(image_file),
            "previewUrl": "/storage/workspace.png",
        },
        {"modelCallId": "model_call_1"},
    )

    assert result["resultType"] == "image"
    assert result["materialAssetId"] == "asset_1"
    assert result["sourceModelCallId"] == "model_call_1"
    assert result["remoteUrl"] == "https://provider.example/image.png"
    assert result["sizeBytes"] == 5
    assert result["extra"]["assetType"] == "poster"
    assert result["extra"]["referenceImageUrls"] == ["https://provider.example/ref.png"]


class _StoredArtifact:
    def __init__(self, public_url: str, absolute_path: str) -> None:
        self._public_url = public_url
        self._absolute_path = absolute_path

    def public_url(self) -> str:
        return self._public_url

    def absolute_path(self) -> str:
        return self._absolute_path


class _RecordingMediaService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.materialized: list[tuple[str, str, str]] = []

    def materialize_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> _StoredArtifact:
        self.materialized.append((source_url, relative_dir, target_file_name))
        path = self.root / target_file_name
        path.write_bytes(b"artifact")
        return _StoredArtifact(f"/storage/{target_file_name}", str(path))

    def ensure_media_thumbnail(
        self,
        media_type: str,
        public_url: str,
        candidate_image_urls: list[str],
        max_width: int,
    ) -> str:
        assert max_width == 480
        assert candidate_image_urls == ["https://provider.example/first.png"]
        return f"thumb-{media_type}-{public_url}"

    def resolve_absolute_path(self, file_url: str) -> str:
        if file_url.startswith("/storage/"):
            return str(self.root / file_url.removeprefix("/storage/"))
        return file_url

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Unexpected media service call: {name}")
