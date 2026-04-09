from __future__ import annotations

from dataclasses import dataclass
from array import array
from pathlib import Path
import json
import math
import re
import shutil
import subprocess
import tempfile
from typing import Iterable
import wave

from ai_cut_shared.schemas import MediaProbe


class MediaToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    duration_seconds: float


@dataclass(frozen=True)
class VideoFrameSample:
    timestamp_seconds: float
    image_path: Path


@dataclass(frozen=True)
class AudioPeakSample:
    timestamp_seconds: float
    energy: float


@dataclass(frozen=True)
class SceneChangeSample:
    timestamp_seconds: float


@dataclass(frozen=True)
class RenderSegmentSpec:
    source_path: Path
    start_seconds: float
    end_seconds: float
    has_audio: bool
    segment_kind: str = "video"
    frame_timestamp_seconds: float | None = None
    hold_seconds: float | None = None


def _spread_samples(samples: list[SceneChangeSample], limit: int) -> list[SceneChangeSample]:
    if limit <= 0 or not samples:
        return []
    if len(samples) <= limit:
        return samples

    picked: list[SceneChangeSample] = []
    used: set[int] = set()
    for index in range(limit):
        raw_position = ((index + 0.5) / limit) * len(samples) - 0.5
        normalized = min(len(samples) - 1, max(0, int(round(raw_position))))
        while normalized in used and normalized + 1 < len(samples):
            normalized += 1
        if normalized in used:
            normalized = max(0, normalized - 1)
            while normalized in used and normalized - 1 >= 0:
                normalized -= 1
        used.add(normalized)
        picked.append(samples[normalized])
    return sorted(picked, key=lambda item: item.timestamp_seconds)


def _quantile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, ratio)) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _run_command(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        tool_name = command[0] if command else "media tool"
        raise MediaToolError(f"{tool_name} is not installed or not available in PATH") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "media command failed"
        raise MediaToolError(stderr)
    return completed.stdout


def _move_output_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    shutil.move(str(source), str(destination))


def probe_media(path: str | Path) -> MediaProbe:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    raw = _run_command(command)
    payload = json.loads(raw)
    streams = payload.get("streams", [])
    fmt = payload.get("format", {})

    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)

    fps = None
    rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
    if isinstance(rate, str) and rate not in {"0/0", "0"} and "/" in rate:
        numerator, denominator = rate.split("/", 1)
        try:
            fps = float(numerator) / float(denominator)
        except Exception:
            fps = None

    return MediaProbe(
        durationSeconds=duration,
        width=int(video_stream.get("width") or 0),
        height=int(video_stream.get("height") or 0),
        hasAudio=audio_stream is not None,
        fps=fps,
    )


def sample_video_frames(
    source_path: str | Path,
    output_dir: str | Path,
    duration_seconds: float,
    frame_count: int = 6,
    max_width: int = 576,
    timestamps: list[float] | None = None,
) -> list[VideoFrameSample]:
    source = Path(source_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_duration = max(0.6, float(duration_seconds))
    if timestamps:
        raw_timestamps = [
            min(max(0.0, float(timestamp)), max(0.0, safe_duration - 0.2))
            for timestamp in timestamps[:12]
        ]
    else:
        normalized_count = max(1, min(frame_count, 12))
        raw_timestamps = [
            min(max(0.0, safe_duration * ((index + 0.5) / normalized_count)), max(0.0, safe_duration - 0.2))
            for index in range(normalized_count)
        ]

    samples: list[VideoFrameSample] = []
    seen: set[float] = set()
    for index, timestamp in enumerate(raw_timestamps, start=1):
        rounded = round(timestamp, 3)
        if rounded in seen:
            continue
        seen.add(rounded)
        image_path = target_dir / f"frame_{index:02d}.jpg"
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{rounded:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            f"scale={max_width}:-2:force_original_aspect_ratio=decrease",
            "-q:v",
            "5",
            str(image_path),
        ]
        _run_command(command)
        if image_path.exists():
            samples.append(VideoFrameSample(timestamp_seconds=rounded, image_path=image_path))
    return samples


def sample_audio_peaks(
    source_path: str | Path,
    duration_seconds: float,
    peak_count: int = 6,
    sample_rate: int = 16000,
    window_seconds: float = 1.0,
) -> list[AudioPeakSample]:
    safe_duration = max(0.6, float(duration_seconds))
    normalized_count = max(1, min(peak_count, 12))
    with tempfile.TemporaryDirectory(prefix="ai-cut-audio-") as temp_dir:
        wav_path = Path(temp_dir) / "mono.wav"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-acodec",
            "pcm_s16le",
            str(wav_path),
        ]
        _run_command(command)

        with wave.open(str(wav_path), "rb") as handle:
            frames = handle.readframes(handle.getnframes())
            rate = handle.getframerate()

    samples = array("h")
    samples.frombytes(frames)
    if not samples:
        return []

    window_size = max(1, int(rate * max(0.4, window_seconds)))
    minimum_gap = max(2.5, safe_duration / max(4.0, normalized_count * 1.4))
    windows: list[AudioPeakSample] = []
    for start in range(0, len(samples), window_size):
        chunk = samples[start : start + window_size]
        if not chunk:
            continue
        squares = sum(int(sample) * int(sample) for sample in chunk)
        rms = math.sqrt(squares / max(1, len(chunk))) / 32768.0
        timestamp = min(max(0.0, (start / rate) + (len(chunk) / rate) / 2), max(0.0, safe_duration - 0.2))
        windows.append(AudioPeakSample(timestamp_seconds=round(timestamp, 3), energy=round(rms, 6)))

    energies = [item.energy for item in windows]
    median_energy = _quantile(energies, 0.5)
    high_energy = _quantile(energies, 0.78)
    adaptive_floor = max(median_energy * 1.22, high_energy * 0.92)

    ranked = sorted(windows, key=lambda item: item.energy, reverse=True)
    candidate_pool = [item for item in ranked if item.energy >= adaptive_floor]
    if len(candidate_pool) < normalized_count:
        candidate_pool = ranked
    selected: list[AudioPeakSample] = []
    for peak in candidate_pool:
        if peak.energy <= 0:
            continue
        if any(abs(peak.timestamp_seconds - item.timestamp_seconds) < minimum_gap for item in selected):
            continue
        selected.append(peak)
        if len(selected) >= normalized_count:
            break
    return sorted(selected, key=lambda item: item.timestamp_seconds)


def detect_scene_changes(
    source_path: str | Path,
    duration_seconds: float,
    max_changes: int = 12,
    threshold: float = 0.32,
) -> list[SceneChangeSample]:
    safe_duration = max(0.6, float(duration_seconds))
    normalized_count = max(1, min(max_changes, 16))
    threshold_candidates = [threshold, max(0.24, threshold - 0.05), max(0.18, threshold - 0.1)]
    minimum_gap = max(1.0, safe_duration / max(6.0, normalized_count * 1.25))
    desired_min = max(2, min(normalized_count, int(max(2.0, safe_duration / 24.0))))
    desired_max = max(normalized_count, int(max(4.0, safe_duration / 5.5)))

    best: list[SceneChangeSample] = []
    for candidate_threshold in threshold_candidates:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(source_path),
            "-filter:v",
            f"select='gt(scene,{candidate_threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            continue

        matches = re.findall(r"pts_time:(\d+(?:\.\d+)?)", completed.stderr)
        if not matches:
            continue

        selected: list[SceneChangeSample] = []
        for raw in matches:
            try:
                timestamp = min(max(0.0, float(raw)), max(0.0, safe_duration - 0.2))
            except Exception:
                continue
            rounded = round(timestamp, 3)
            if any(abs(rounded - item.timestamp_seconds) < minimum_gap for item in selected):
                continue
            selected.append(SceneChangeSample(timestamp_seconds=rounded))
            if len(selected) >= desired_max:
                break

        if desired_min <= len(selected) <= desired_max:
            return _spread_samples(selected, normalized_count)
        if len(selected) > len(best):
            best = selected

    return _spread_samples(best, normalized_count)


def target_resolution(aspect_ratio: str) -> tuple[int, int]:
    if aspect_ratio == "16:9":
        return 1920, 1080
    return 1080, 1920


def template_color(name: str) -> str:
    palette = {
        "hook": "#ff7a18",
        "brand": "#0f766e",
        "call_to_action": "#16a34a",
        "cold_open": "#2563eb",
        "flash_hook": "#f97316",
        "pressure_build": "#7c3aed",
        "suspense_hold": "#0f172a",
        "follow_hook": "#1d4ed8",
        "question_freeze": "#9333ea",
        "transition_flash": "#f8fafc",
        "transition_black": "#020617",
        "none": "#111827",
    }
    return palette.get(name, "#334155")


def _render_slate(path: Path, name: str, duration: float, resolution: tuple[int, int]) -> None:
    width, height = resolution
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={template_color(name)}:s={width}x{height}:r=30:d={duration}",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        "-movflags",
        "+faststart",
        str(path),
    ]
    _run_command(command)


def _render_cut(
    path: Path,
    source_path: Path,
    start_seconds: float,
    end_seconds: float,
    resolution: tuple[int, int],
    has_audio: bool,
) -> None:
    width, height = resolution
    duration = max(0.5, end_seconds - start_seconds)
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p"
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(source_path),
        "-t",
        f"{duration:.3f}",
    ]
    if has_audio:
        command.extend(
            [
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                video_filter,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(path),
            ]
        )
    else:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-vf",
                video_filter,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-shortest",
                "-movflags",
                "+faststart",
                str(path),
            ]
        )
    _run_command(command)


def _render_frame_hold(
    path: Path,
    source_path: Path,
    timestamp_seconds: float,
    duration_seconds: float,
    resolution: tuple[int, int],
) -> None:
    width, height = resolution
    hold_duration = max(0.12, float(duration_seconds))
    frame_path = path.with_suffix(".jpg")
    capture_command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{max(0.0, timestamp_seconds):.3f}",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-q:v",
        "4",
        str(frame_path),
    ]
    _run_command(capture_command)

    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(frame_path),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        f"{hold_duration:.3f}",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        "-movflags",
        "+faststart",
        str(path),
    ]
    _run_command(command)


def _render_still_image(
    path: Path,
    image_path: Path,
    duration_seconds: float,
    resolution: tuple[int, int],
) -> None:
    width, height = resolution
    duration = max(0.18, float(duration_seconds))
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p"
    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        "-movflags",
        "+faststart",
        str(path),
    ]
    _run_command(command)


def _concat_segments(output_path: Path, segments: Iterable[Path]) -> None:
    segment_list = list(segments)
    if len(segment_list) == 1:
        _move_output_file(segment_list[0], output_path)
        return

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        list_file = Path(handle.name)
        for segment in segment_list:
            handle.write(f"file '{segment.as_posix()}'\n")

    try:
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        _run_command(command)
    finally:
        if list_file.exists():
            list_file.unlink()


def _render_crossfade_segments(
    segment_paths: list[Path],
    output_path: Path,
) -> float:
    if not segment_paths:
        raise MediaToolError("no renderable segments provided")
    if len(segment_paths) == 1:
        single = segment_paths[0]
        _move_output_file(single, output_path)
        return round(max(0.12, probe_media(output_path).durationSeconds), 3)

    def _render_crossfade_pair(left_path: Path, right_path: Path, pair_output: Path) -> float:
        left_duration = max(0.12, probe_media(left_path).durationSeconds)
        right_duration = max(0.12, probe_media(right_path).durationSeconds)
        transition_ceiling = min(left_duration, right_duration) * 0.35
        transition_duration = min(0.28, transition_ceiling)
        transition_duration = min(transition_duration, left_duration - 0.03, right_duration - 0.03)
        if transition_duration < 0.06:
            _concat_segments(pair_output, [left_path, right_path])
            return round(max(0.5, left_duration + right_duration), 3)

        offset = max(0.0, left_duration - transition_duration)
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(left_path),
            "-i",
            str(right_path),
            "-filter_complex",
            (
                f"[0:v][1:v]xfade=transition=fade:duration={transition_duration:.3f}:offset={offset:.3f}[v];"
                f"[0:a][1:a]acrossfade=d={transition_duration:.3f}[a]"
            ),
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(pair_output),
        ]
        _run_command(command)
        return round(max(0.5, left_duration + right_duration - transition_duration), 3)

    with tempfile.TemporaryDirectory(prefix="ai-cut-crossfade-") as temp_dir:
        temp_root = Path(temp_dir)
        current_path = segment_paths[0]
        current_duration = max(0.12, probe_media(current_path).durationSeconds)
        for index in range(1, len(segment_paths)):
            next_path = segment_paths[index]
            pair_output = temp_root / f"xfade_{index:02d}.mp4"
            current_duration = _render_crossfade_pair(current_path, next_path, pair_output)
            current_path = pair_output
        _move_output_file(current_path, output_path)
        return round(max(0.5, current_duration), 3)


def _concat_segments_with_crossfade(output_path: Path, segments: Iterable[Path], transition_duration: float = 0.35) -> None:
    segment_list = list(segments)
    if not segment_list:
        raise MediaToolError("no segments provided for crossfade")
    if len(segment_list) == 1:
        _move_output_file(segment_list[0], output_path)
        return

    durations: list[float] = [max(0.5, probe_media(path).durationSeconds) for path in segment_list]
    normalized_transition = max(0.08, min(float(transition_duration), 0.8))
    command = ["ffmpeg", "-y"]
    for segment in segment_list:
        command.extend(["-i", str(segment)])

    video_expr = "[0:v]"
    audio_expr = "[0:a]"
    accumulated_duration = durations[0]
    filter_parts: list[str] = []
    for index in range(1, len(segment_list)):
        video_input = f"[{index}:v]"
        audio_input = f"[{index}:a]"
        video_out = f"[vxf{index}]"
        audio_out = f"[axf{index}]"
        offset = max(0.0, accumulated_duration - normalized_transition)
        filter_parts.append(
            f"{video_expr}{video_input}xfade=transition=fade:duration={normalized_transition:.3f}:offset={offset:.3f}{video_out}"
        )
        filter_parts.append(
            f"{audio_expr}{audio_input}acrossfade=d={normalized_transition:.3f}:c1=tri:c2=tri{audio_out}"
        )
        video_expr = video_out
        audio_expr = audio_out
        accumulated_duration = accumulated_duration + durations[index] - normalized_transition

    filter_complex = ";".join(filter_parts)
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            video_expr,
            "-map",
            audio_expr,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_command(command)


def compose_source_timeline(
    source_paths: list[Path],
    output_path: Path,
    aspect_ratio: str,
) -> Path:
    if not source_paths:
        raise MediaToolError("no source paths provided")
    if len(source_paths) == 1:
        return source_paths[0]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolution = target_resolution(aspect_ratio)

    with tempfile.TemporaryDirectory(prefix="ai-cut-multisource-") as temp_dir:
        temp_root = Path(temp_dir)
        normalized_segments: list[Path] = []
        for index, source_path in enumerate(source_paths, start=1):
            probe = probe_media(source_path)
            segment_path = temp_root / f"segment_{index:02d}.mp4"
            _render_cut(
                path=segment_path,
                source_path=source_path,
                start_seconds=0.0,
                end_seconds=max(0.5, probe.durationSeconds),
                resolution=resolution,
                has_audio=probe.hasAudio,
            )
            normalized_segments.append(segment_path)
        _concat_segments(output_path, normalized_segments)

    return output_path


def render_output(
    source_path: Path,
    output_path: Path,
    start_seconds: float,
    end_seconds: float,
    aspect_ratio: str,
    intro_template: str,
    outro_template: str,
    has_audio: bool,
) -> RenderResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolution = target_resolution(aspect_ratio)
    duration = max(0.5, end_seconds - start_seconds)

    with tempfile.TemporaryDirectory(prefix="ai-cut-render-") as temp_dir:
        temp_root = Path(temp_dir)
        cut_path = temp_root / "cut.mp4"
        _render_cut(cut_path, source_path, start_seconds, end_seconds, resolution, has_audio)

        segments: list[Path] = []
        if intro_template and intro_template != "none":
            intro_path = temp_root / "intro.mp4"
            _render_slate(intro_path, intro_template, 1.2, resolution)
            segments.append(intro_path)
        segments.append(cut_path)
        if outro_template and outro_template != "none":
            outro_path = temp_root / "outro.mp4"
            _render_slate(outro_path, outro_template, 1.2, resolution)
            segments.append(outro_path)
        _concat_segments(output_path, segments)

    return RenderResult(output_path=output_path, duration_seconds=duration)


def render_output_segments(
    segments: Iterable[RenderSegmentSpec],
    output_path: Path,
    aspect_ratio: str,
    intro_template: str,
    outro_template: str,
    transition_style: str = "cut",
) -> RenderResult:
    segment_specs = [
        item
        for item in segments
        if (
            item.segment_kind == "frame"
            and (item.hold_seconds or 0.0) > 0.05
            and item.frame_timestamp_seconds is not None
        )
        or (item.segment_kind != "frame" and item.end_seconds > item.start_seconds)
    ]
    if not segment_specs:
        raise MediaToolError("no renderable segments provided")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolution = target_resolution(aspect_ratio)
    with tempfile.TemporaryDirectory(prefix="ai-cut-render-") as temp_dir:
        temp_root = Path(temp_dir)
        opening_segments: list[Path] = []
        video_segments: list[Path] = []
        total_duration = 0.0
        for index, segment in enumerate(segment_specs, start=1):
            segment_path = temp_root / f"segment_{index:02d}.mp4"
            if segment.segment_kind == "frame" and segment.frame_timestamp_seconds is not None:
                _render_frame_hold(
                    path=segment_path,
                    source_path=segment.source_path,
                    timestamp_seconds=segment.frame_timestamp_seconds,
                    duration_seconds=segment.hold_seconds or segment.end_seconds - segment.start_seconds,
                    resolution=resolution,
                )
                total_duration += max(0.12, float(segment.hold_seconds or 0.0))
                opening_segments.append(segment_path)
            else:
                _render_cut(
                    path=segment_path,
                    source_path=segment.source_path,
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    resolution=resolution,
                    has_audio=segment.has_audio,
                )
                total_duration += max(0.5, segment.end_seconds - segment.start_seconds)
                video_segments.append(segment_path)

        timeline_segments: list[Path] = []
        timeline_segments.extend(opening_segments)
        if intro_template and intro_template != "none":
            intro_path = temp_root / "intro.mp4"
            _render_slate(intro_path, intro_template, 1.2, resolution)
            timeline_segments.append(intro_path)
            total_duration += 1.2
        timeline_segments.extend(video_segments)
        if outro_template and outro_template != "none":
            outro_path = temp_root / "outro.mp4"
            _render_slate(outro_path, outro_template, 1.2, resolution)
            timeline_segments.append(outro_path)
            total_duration += 1.2

        if transition_style == "crossfade":
            total_duration = _render_crossfade_segments(timeline_segments, output_path)
        else:
            final_segments: list[Path] = []
            for index, timeline_segment in enumerate(timeline_segments):
                final_segments.append(timeline_segment)
                if index >= len(timeline_segments) - 1:
                    continue
                transition_template = ""
                transition_duration = 0.0
                if transition_style == "flash":
                    transition_template = "transition_flash"
                    transition_duration = 0.14
                elif transition_style == "fade_black":
                    transition_template = "transition_black"
                    transition_duration = 0.22
                if transition_template:
                    transition_path = temp_root / f"transition_{index + 1:02d}.mp4"
                    _render_slate(transition_path, transition_template, transition_duration, resolution)
                    final_segments.append(transition_path)
                    total_duration += transition_duration
            _concat_segments(output_path, final_segments)

    return RenderResult(output_path=output_path, duration_seconds=round(total_duration, 3))
