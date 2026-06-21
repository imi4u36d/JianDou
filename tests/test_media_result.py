from __future__ import annotations

import pytest
pytestmark = pytest.mark.domain
from backend.domain.media_result import (
    media_output_url,
    remote_source_url,
    result_metadata,
    thumbnail_candidate,
)


def test_result_metadata_rejects_non_object_metadata() -> None:
    assert result_metadata({"metadata": "bad"}) == {}
    assert result_metadata(None) == {}


def test_media_output_url_prefers_direct_output_url() -> None:
    assert (
        media_output_url(
            {
                "outputUrl": "/direct.mp4",
                "metadata": {
                    "outputUrl": "/metadata.mp4",
                    "fileUrl": "/file.mp4",
                    "remoteSourceUrl": "https://provider.example/video.mp4",
                },
            }
        )
        == "/direct.mp4"
    )


def test_media_output_url_falls_back_through_metadata_urls() -> None:
    assert media_output_url({"metadata": {"outputUrl": "/metadata.png"}}) == "/metadata.png"
    assert media_output_url({"metadata": {"fileUrl": "/file.png"}}) == "/file.png"
    assert (
        media_output_url({"metadata": {"remoteSourceUrl": "https://provider.example/image.png"}})
        == "https://provider.example/image.png"
    )


def test_remote_source_url_trims_missing_and_present_values() -> None:
    assert remote_source_url(None) == ""
    assert remote_source_url({"remoteSourceUrl": " https://provider.example/file.png "}) == "https://provider.example/file.png"


def test_thumbnail_candidate_prefers_explicit_thumbnail_then_poster_then_frames() -> None:
    assert thumbnail_candidate({"thumbnailUrl": "/thumb.png", "posterUrl": "/poster.png"}) == "/thumb.png"
    assert thumbnail_candidate({"posterUrl": "/poster.png", "firstFrameUrl": "/first.png"}) == "/poster.png"
    assert thumbnail_candidate({"firstFrameUrl": "/first.png", "startFrameUrl": "/start.png"}) == "/first.png"
    assert thumbnail_candidate({"startFrameUrl": "/start.png"}) == "/start.png"
