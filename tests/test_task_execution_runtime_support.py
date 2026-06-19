from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.services.task_execution_runtime_support import (
    ModelRuntimePropertiesResolverStub,
    TaskExecutionRuntimeSupport,
)
from backend.services.task_worker_status_stage_service import TaskExecutionAbortedException


def _task(**overrides: Any) -> TaskRecord:
    values = {
        "id": "task_runtime",
        "owner_user_id": 11,
        "title": "Runtime Task",
        "status": TaskStatus.RENDERING.value,
        "aspect_ratio": "16:9",
        "creative_prompt": "Create something",
        "transcript_text": "Transcript text",
        "task_type": "video_generation",
        "task_seed": None,
        "min_duration_seconds": 0,
        "max_duration_seconds": 0,
        "request_snapshot": {
            "textAnalysisModel": "text-model",
            "imageModel": "image-model",
            "videoModel": "video-model",
            "stylePreset": "noir",
        },
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    values.update(overrides)
    return TaskRecord(**values)


def test_resolve_dimensions_and_duration_prefers_explicit_snapshot_values() -> None:
    support = TaskExecutionRuntimeSupport(model_resolver=_Resolver(default_duration=9))
    task = _task(
        request_snapshot={
            "textAnalysisModel": "text-model",
            "imageModel": "image-model",
            "videoModel": "video-model",
            "imageSize": "640x360",
            "videoDuration": {"auto": False, "seconds": 7},
        }
    )

    assert support.resolve_dimensions(task) == [640, 360]
    assert support.resolve_duration_seconds(task) == 7


def test_build_image_request_keeps_single_reference_url_whole() -> None:
    support = TaskExecutionRuntimeSupport(model_resolver=_Resolver(supports_seed=True))
    task = _task(request_snapshot={**_task().request_snapshot, "seed": 123})

    request = support.build_image_run_request(
        task,
        clip_index=3,
        prompt="A frame",
        width=1280,
        height=720,
        reference_image_url="https://example.test/reference.png",
        duration_seconds=6,
        frame_role="last",
    )

    assert request["kind"] == "image"
    assert request["input"]["referenceImageUrl"] == "https://example.test/reference.png"
    assert request["input"]["referenceImageUrls"] == ["https://example.test/reference.png"]
    assert request["input"]["seed"] == 123
    assert request["input"]["frameRole"] == "last"
    assert request["storage"]["fileStem"] == "clip3-last"
    assert request["auth"] == {"userId": "11"}


def test_build_workspace_image_request_converts_storage_references_to_public_urls() -> None:
    media_service = _ReferenceMediaService(public_url="https://cdn.example.test/ref.png")
    support = TaskExecutionRuntimeSupport(
        model_resolver=_Resolver(supports_seed=True),
        local_media_artifact_service=media_service,
    )
    task = _task(
        task_type="character_sheet",
        execution_context={"referenceImageUrls": ["/storage/ref.png", "/storage/ref.png"]},
        request_snapshot={
            **_task().request_snapshot,
            "assetType": "character_sheet",
            "creativePrompt": "Hero character",
            "seed": 42,
        },
    )

    request = support.build_workspace_image_run_request(task, 1024, 1024)

    assert request["kind"] == "image"
    assert request["input"]["referenceImageUrls"] == ["https://cdn.example.test/ref.png"]
    assert request["input"]["referenceImageUrl"] == "https://cdn.example.test/ref.png"
    assert request["input"]["seed"] == 42
    assert request["metadata"]["referenceImageCount"] == 1
    assert "角色三视图设定图" in request["input"]["prompt"]


def test_build_workspace_image_request_uses_data_uri_when_public_url_missing() -> None:
    media_service = _ReferenceMediaService(public_url="", data_uri="data:image/png;base64,abc")
    support = TaskExecutionRuntimeSupport(
        model_resolver=_Resolver(),
        local_media_artifact_service=media_service,
    )
    task = _task(
        execution_context={"referenceImageUrls": ["/storage/ref.png"]},
        request_snapshot={**_task().request_snapshot, "imageModel": "seedream-v4"},
    )

    request = support.build_workspace_image_run_request(task, 512, 512)

    assert request["input"]["referenceImageUrls"] == ["data:image/png;base64,abc"]


def test_build_video_request_truncates_prompt_and_uses_audio_default() -> None:
    support = TaskExecutionRuntimeSupport(model_resolver=_Resolver(video_generate_audio="false"))

    request = support.build_video_run_request(
        _task(task_seed=77),
        clip_index=1,
        prompt="line\n" * 800,
        video_size="1280*720",
        duration_seconds=8,
        min_duration_seconds=5,
        max_duration_seconds=12,
        first_frame_url="https://example.test/first.png",
        last_frame_url="https://example.test/last.png",
    )

    assert request["kind"] == "video"
    assert len(request["input"]["prompt"]) <= 2203
    assert request["input"]["generateAudio"] is False
    assert request["input"]["seed"] == 77
    assert request["input"]["lastFrameUrl"] == "https://example.test/last.png"
    assert request["model"]["providerModel"] == "video-model"


def test_assert_task_still_active_raises_when_repository_is_present() -> None:
    support = TaskExecutionRuntimeSupport(task_repository=_UnexpectedRepository())

    with pytest.raises(TaskExecutionAbortedException) as exc:
        support.assert_task_still_active(_task(status=TaskStatus.FAILED.value, error_message="failed already"))

    assert exc.value.task_status == TaskStatus.FAILED.value


class _Resolver(ModelRuntimePropertiesResolverStub):
    def __init__(
        self,
        *,
        default_duration: int = 10,
        supports_seed: bool = False,
        video_generate_audio: str = "true",
    ) -> None:
        self.default_duration = default_duration
        self._supports_seed = supports_seed
        self.video_generate_audio = video_generate_audio

    def int_value(self, *keys: str, default: int = 0) -> int:
        return self.default_duration

    def value(self, *keys: str, default: str = "") -> str:
        return self.video_generate_audio

    def supports_seed(self, model: str) -> bool:
        return self._supports_seed


class _ReferenceMediaService:
    def __init__(self, *, public_url: str, data_uri: str = "") -> None:
        self.public_url = public_url
        self.data_uri = data_uri

    def build_externally_accessible_url(self, local_path: str) -> str:
        assert local_path == "/storage/ref.png"
        return self.public_url

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        assert public_url == "/storage/ref.png"
        return self.data_uri


class _UnexpectedRepository:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Unexpected repository call: {name}")
