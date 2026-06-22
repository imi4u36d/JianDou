from __future__ import annotations

import pytest

pytestmark = pytest.mark.domain
from backend.domain.media_artifacts import (
    file_ext,
    file_ext_or_default,
    file_name_from_url,
    image_mime_type,
)


def test_file_name_from_url_strips_query_fragment_and_trailing_slash() -> None:
    assert file_name_from_url("https://cdn.example.test/path/video.mp4?token=secret") == "video.mp4"
    assert file_name_from_url("/storage/tasks/task_1/clip1.png#preview") == "clip1.png"
    assert file_name_from_url("https://cdn.example.test/path/") == "path"


def test_file_ext_accepts_safe_short_extensions() -> None:
    assert file_ext("clip1.MP4?download=1") == "mp4"
    assert file_ext("image.profile.png") == "png"
    assert file_ext("no-extension") == ""
    assert file_ext("unsafe.toolongextension") == ""
    assert file_ext("unsafe.bad-ext") == ""


def test_file_ext_or_default_uses_fallback_for_missing_or_unsafe_extension() -> None:
    assert file_ext_or_default("clip1.mp4", "bin") == "mp4"
    assert file_ext_or_default("clip1", "bin") == "bin"
    assert file_ext_or_default("clip1.bad-ext", "bin") == "bin"


def test_image_mime_type_from_extension() -> None:
    assert image_mime_type("photo.jpg") == "image/jpeg"
    assert image_mime_type("photo.jpeg") == "image/jpeg"
    assert image_mime_type("photo.webp") == "image/webp"
    assert image_mime_type("photo.png") == "image/png"
    assert image_mime_type("photo") == "image/png"
