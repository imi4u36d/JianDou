from types import SimpleNamespace

import pytest

from backend.services.task_diagnosis_service import TaskRequestSnapshotFactory
from backend.services.task_request_snapshot_factory import TaskRequestSnapshotFactory as ExtractedFactory


class _Resolver:
    def value(self, section: str, key: str, fallback: str) -> str:
        assert (section, key) == ("catalog.defaults", "video_size")
        return "1920*1080" or fallback


def test_compatibility_export_points_to_extracted_snapshot_factory() -> None:
    assert TaskRequestSnapshotFactory is ExtractedFactory


def test_snapshot_factory_normalizes_models_duration_and_output_count() -> None:
    task = SimpleNamespace(
        task_type="video_generation",
        title="Rain",
        creative_prompt="Night street",
        aspect_ratio="16:9",
        task_seed=42,
        min_duration_seconds=5,
        max_duration_seconds=8,
        transcript_text="dialogue",
    )
    request = SimpleNamespace(
        task_type="video_generation",
        asset_type="workflow",
        image_size="2K",
        text_analysis_model="text-model",
        image_model="image-model",
        video_model="video-model",
        video_size="",
        video_duration_seconds="auto",
        output_count="3",
        stop_before_video_generation=True,
    )

    snapshot = ExtractedFactory(_Resolver()).create(request, task)

    assert snapshot.task_type == "video_generation"
    assert snapshot.video_size == "1920*1080"
    assert snapshot.output_count.count == 3
    assert snapshot.seed == 42
    assert snapshot.stop_before_video_generation is True


def test_snapshot_factory_rejects_non_positive_output_count() -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        ExtractedFactory(None)._normalize_output_count(0)
