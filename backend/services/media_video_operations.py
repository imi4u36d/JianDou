"""FFmpeg-backed video operations for the local media service."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.services.media_service import ImageArtifact, StoredArtifact, VideoArtifact


class LocalMediaVideoService:
    """Generate and concatenate videos while the owner handles storage policy."""

    def __init__(self, owner: Any):
        self._owner = owner

    def write_silent_video(
        self,
        relative_dir: str,
        file_name: str,
        width: int,
        height: int,
        duration_seconds: int,
        poster: ImageArtifact,
    ) -> VideoArtifact:
        from backend.services.media_service import VideoArtifact

        try:
            output_dir = self._owner._ensure_directory(relative_dir)
            output = output_dir / file_name
            cmd = [
                self._owner._ffmpeg_bin,
                "-y",
                "-loop",
                "1",
                "-i",
                poster.absolute_path,
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t",
                str(max(1, duration_seconds)),
                "-vf",
                f"scale={width}:{height},format=yuv420p",
                "-r",
                "24",
                "-shortest",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(output),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0 or not output.exists():
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg failed")
            return VideoArtifact(
                file_name=file_name,
                absolute_path=str(output.resolve()),
                public_url=self._owner._publish_path(output, relative_dir, file_name, "video/mp4"),
                size_bytes=output.stat().st_size,
                width=width,
                height=height,
                duration_seconds=max(1, duration_seconds),
                has_audio=True,
                mime_type="video/mp4",
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg timed out")
        except Exception as ex:
            raise RuntimeError(f"video artifact write failed: {ex}") from ex

    def concat_videos(
        self,
        relative_dir: str,
        file_name: str,
        source_public_urls: list[str],
    ) -> StoredArtifact:
        from backend.services.media_service import StoredArtifact

        source_paths = self._resolve_video_paths(source_public_urls)
        output_dir = self._owner._ensure_directory(relative_dir)
        output = (output_dir / file_name).resolve()
        tmp_list = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        try:
            for source in source_paths:
                escaped = str(source).replace("'", "'\\''")
                tmp_list.write(f"file '{escaped}'\n")
            tmp_list.close()
            result = subprocess.run(
                self._concat_command(tmp_list.name, output, reencode=False),
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0 or not output.exists():
                logging.getLogger(__name__).info(
                    "concat -c copy failed (%s), retrying with re-encode",
                    result.stderr.strip()[:200],
                )
                if output.exists():
                    output.unlink()
                result = subprocess.run(
                    self._concat_command(tmp_list.name, output, reencode=True),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode != 0 or not output.exists():
                    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg concat failed")
            return StoredArtifact(
                file_name=file_name,
                absolute_path=str(output),
                public_url=self._owner._publish_path(output, relative_dir, file_name),
                size_bytes=output.stat().st_size,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg concat timed out")
        finally:
            tmp_list.close()
            os.unlink(tmp_list.name)

    def _resolve_video_paths(self, source_public_urls: list[str]) -> list[Path]:
        if not source_public_urls or len(source_public_urls) < 2:
            raise ValueError("at least two source videos are required")
        paths: list[Path] = []
        for url in source_public_urls:
            absolute_path = self._owner._resolve_absolute_path(url)
            if not absolute_path:
                raise ValueError("source public url is not a local storage path")
            source = Path(absolute_path).resolve()
            if not source.exists():
                raise RuntimeError("source video does not exist")
            paths.append(source)
        return paths

    def _concat_command(self, list_path: str, output: Path, *, reencode: bool) -> list[str]:
        command = [self._owner._ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", list_path]
        if reencode:
            command.extend(
                ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "128k"]
            )
        else:
            command.extend(["-c", "copy"])
        command.extend(["-movflags", "+faststart", str(output)])
        return command
