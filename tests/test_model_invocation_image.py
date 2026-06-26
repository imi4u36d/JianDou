from __future__ import annotations

import pytest

from backend.services.model_invocation import ImageGenerationRequest, OpenAiImageModelProvider

pytestmark = pytest.mark.service


def test_openai_image_provider_uses_auto_size_when_dimensions_are_zero() -> None:
    request = ImageGenerationRequest(width=0, height=0)

    assert OpenAiImageModelProvider._requested_image_size(request) == "auto"


def test_openai_image_provider_uses_explicit_size_when_dimensions_are_positive() -> None:
    request = ImageGenerationRequest(width=1024, height=1536)

    assert OpenAiImageModelProvider._requested_image_size(request) == "1024x1536"
