"""Render prompt-card image artifacts for the local media facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from backend.services.media_artifacts import ImageArtifact


class LocalMediaPromptCardRenderer:
    """Own Pillow drawing and text layout for generated prompt cards."""

    def __init__(self, media_service: Any) -> None:
        self._media_service = media_service

    def write_prompt_card(
        self,
        relative_dir: str,
        file_name: str,
        width: int,
        height: int,
        title: str,
        subtitle: str,
        body_text: str,
    ) -> ImageArtifact:
        try:
            output_dir = self._media_service._ensure_directory(relative_dir)
            output = output_dir / file_name
            image = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(image)
            self._draw_gradient(draw, width, height)

            margin = max(24, min(width, height) // 20)
            card_width = max(180, width - margin * 2)
            card_top = margin
            card_height = max(112, height // 8)
            draw.rounded_rectangle(
                [margin, card_top, margin + card_width, card_top + card_height],
                radius=24,
                fill=(255, 255, 255, 228),
            )

            title_font_size = max(20, min(width // 18, 42))
            title_font = self._font("DejaVuSans-Bold.ttf", title_font_size)
            draw.text(
                (margin + 24, card_top + 24),
                title.strip() if title else "MEDIA PLACEHOLDER",
                fill=(15, 23, 42),
                font=title_font,
            )

            subtitle_font_size = max(14, min(width // 34, 24))
            subtitle_font = self._font("DejaVuSans.ttf", subtitle_font_size)
            draw.text(
                (margin + 24, card_top + card_height - subtitle_font_size - 12),
                subtitle.strip() if subtitle else "Python local render",
                fill=(15, 23, 42),
                font=subtitle_font,
            )

            lines = self._wrap_text(body_text, max(18, width // 24))
            line_height = max(24, min(height // 18, 34))
            body_font = self._font("DejaVuSans.ttf", max(12, min(width // 34, 18)))
            start_y = margin + card_height + 24
            for index, line in enumerate(lines[:8]):
                draw.text(
                    (margin + 24, start_y + index * line_height),
                    line,
                    fill=(241, 245, 249),
                    font=body_font,
                )

            image.save(output, "PNG")
            return self._image_artifact(output, relative_dir, file_name, width, height)
        except Exception as ex:
            raise RuntimeError(f"image artifact write failed: {ex}") from ex

    @staticmethod
    def _draw_gradient(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        for y in range(height):
            ratio = y / max(height, 1)
            color = (
                int(12 + (32 - 12) * ratio),
                int(20 + (74 - 20) * ratio),
                int(36 + (135 - 36) * ratio),
            )
            draw.line((0, y, width, y), fill=color)

    @staticmethod
    def _font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    @staticmethod
    def _wrap_text(text: str, max_chars_per_line: int) -> list[str]:
        normalized = (text or "").replace("\n", " ").strip()
        if not normalized:
            return ["placeholder output"]
        width = max(12, max_chars_per_line)
        return [normalized[index : index + width] for index in range(0, len(normalized), width)]

    def _image_artifact(
        self,
        output: Path,
        relative_dir: str,
        file_name: str,
        width: int,
        height: int,
    ) -> ImageArtifact:
        return ImageArtifact(
            file_name=file_name,
            absolute_path=str(output.resolve()),
            public_url=self._media_service._publish_path(
                output, relative_dir, file_name, "image/png"
            ),
            size_bytes=output.stat().st_size,
            width=width,
            height=height,
            mime_type="image/png",
        )
