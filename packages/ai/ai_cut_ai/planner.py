from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Callable, Protocol
import json
import re

from ai_cut_ai.generation_v2 import PlannerModelGateway
from ai_cut_ai.providers import ModelRouter
from ai_cut_shared.config import Settings
from ai_cut_media.media import detect_scene_changes, sample_audio_peaks, sample_video_frames
from ai_cut_shared.schemas import ClipPlan, MediaProbe, TaskSpec
from ai_cut_shared.utils import (
    clamp,
    describe_json_error_context,
    extract_llm_text_response,
    parse_json_object,
    truncate_text,
)


@dataclass(frozen=True)
class PlannerContext:
    task: TaskSpec
    source: MediaProbe
    transcriptText: str | None = None
    sourcePath: str | None = None
    sourceTimeline: list[dict[str, object]] | None = None
    workDir: str | None = None
    trace: Callable[[str, str, str, dict[str, object] | None, str], None] | None = None


@dataclass(frozen=True)
class TranscriptCue:
    startSeconds: float
    endSeconds: float
    text: str


@dataclass(frozen=True)
class DialogueBlock:
    startSeconds: float
    endSeconds: float
    text: str
    cues: list[TranscriptCue]


@dataclass(frozen=True)
class VisualInsight:
    title: str
    reason: str
    focusSeconds: float
    confidence: float | None = None
    eventType: str | None = None
    relatedSubtitle: str | None = None


@dataclass(frozen=True)
class VisualShot:
    sourceAssetId: str
    sourceFileName: str
    shotIndex: int
    localStartSeconds: float
    localEndSeconds: float
    timelineStartSeconds: float
    timelineEndSeconds: float
    summary: str
    subjects: list[str]
    action: str | None = None
    emotion: str | None = None
    location: str | None = None
    visualHook: str | None = None
    dialogueHint: str | None = None
    storyRole: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class VisionSourceAnalysis:
    sourceAssetId: str
    sourceFileName: str
    sourceDurationSeconds: float
    timelineStartOffset: float
    timelineEndOffset: float
    shots: list[VisualShot]
    events: list[VisualInsight]


@dataclass(frozen=True)
class SignalBundle:
    transcriptCues: list[TranscriptCue]
    selectedTranscriptCues: list[TranscriptCue]
    transcriptTimestamps: list[float]
    audioPeaks: list[tuple[float, float]]
    sceneChanges: list[float]


@dataclass(frozen=True)
class VisionAnalysisResult:
    modelName: str
    sources: list[VisionSourceAnalysis]
    shots: list[VisualShot]
    events: list[VisualInsight]
    frameTimestamps: list[float]
    signals: SignalBundle


class Planner(Protocol):
    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        raise NotImplementedError


class VisionSourceParseError(RuntimeError):
    pass


def _image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _cue_signal_score(cue: TranscriptCue) -> float:
    emphasis_keywords = [
        "不要",
        "不行",
        "住手",
        "为什么",
        "怎么会",
        "竟然",
        "离婚",
        "结婚",
        "杀",
        "死",
        "滚",
        "完了",
        "求你",
        "真相",
        "秘密",
        "反转",
    ]
    score = min(len(cue.text) / 18.0, 3.0)
    if any(token in cue.text for token in emphasis_keywords):
        score += 2.5
    if any(token in cue.text for token in ["！", "!", "？", "?"]):
        score += 1.5
    if len(cue.text) >= 18:
        score += 0.5
    return score


def select_transcript_signal_cues(
    transcript_cues: list[TranscriptCue],
    duration_seconds: float,
    frame_count: int,
) -> list[TranscriptCue]:
    cue_limit = max(1, frame_count)
    if not transcript_cues:
        return []

    minimum_gap = max(3.0, duration_seconds / max(4.0, frame_count * 1.6))
    ranked = sorted(
        transcript_cues,
        key=lambda cue: (_cue_signal_score(cue), cue.endSeconds - cue.startSeconds),
        reverse=True,
    )

    selected: list[TranscriptCue] = []
    for cue in ranked:
        center = (cue.startSeconds + cue.endSeconds) / 2
        if any(abs(center - ((item.startSeconds + item.endSeconds) / 2)) < minimum_gap for item in selected):
            continue
        selected.append(cue)
        if len(selected) >= cue_limit:
            break

    if len(selected) < cue_limit:
        for cue in transcript_cues:
            if cue in selected:
                continue
            selected.append(cue)
            if len(selected) >= cue_limit:
                break

    return selected[:cue_limit]


def select_signal_timestamps(context: PlannerContext, frame_count: int) -> tuple[list[float], list[TranscriptCue]]:
    transcript_cues = parse_transcript_cues(context.transcriptText)
    selected = select_transcript_signal_cues(
        transcript_cues=transcript_cues,
        duration_seconds=context.source.durationSeconds,
        frame_count=frame_count,
    )
    timestamps = [round((cue.startSeconds + cue.endSeconds) / 2, 3) for cue in selected]
    return timestamps, selected


def select_audio_signal_timestamps(context: PlannerContext, frame_count: int) -> list[tuple[float, float]]:
    if not context.sourcePath or not context.source.hasAudio:
        return []
    try:
        peaks = sample_audio_peaks(
            source_path=context.sourcePath,
            duration_seconds=context.source.durationSeconds,
            peak_count=frame_count,
        )
    except Exception:
        return []
    return [(peak.timestamp_seconds, peak.energy) for peak in peaks]


def merge_signal_timestamps(
    transcript_timestamps: list[float],
    audio_peak_timestamps: list[tuple[float, float]],
    scene_change_timestamps: list[float],
    duration_seconds: float,
    limit: int,
) -> list[float]:
    safe_duration = max(0.6, duration_seconds)
    minimum_gap = max(2.5, safe_duration / max(4.0, limit * 1.4))
    candidates: list[tuple[float, float]] = []
    for timestamp in transcript_timestamps:
        candidates.append((timestamp, 4.0))
    for timestamp, energy in audio_peak_timestamps:
        candidates.append((timestamp, 1.5 + min(energy * 12.0, 3.0)))
    for timestamp in scene_change_timestamps:
        candidates.append((timestamp, 2.6))
    if not candidates:
        return []

    selected: list[tuple[float, float]] = []
    for timestamp, weight in sorted(candidates, key=lambda item: item[1], reverse=True):
        if any(abs(timestamp - existing[0]) < minimum_gap for existing in selected):
            continue
        selected.append((timestamp, weight))
        if len(selected) >= limit:
            break
    return sorted(round(timestamp, 3) for timestamp, _ in selected)


def collect_signal_bundle(context: PlannerContext, frame_count: int) -> SignalBundle:
    transcript_cues = parse_transcript_cues(context.transcriptText)
    selected_transcript_cues = select_transcript_signal_cues(
        transcript_cues=transcript_cues,
        duration_seconds=context.source.durationSeconds,
        frame_count=frame_count,
    )
    transcript_timestamps = [
        round((cue.startSeconds + cue.endSeconds) / 2, 3)
        for cue in selected_transcript_cues
    ]
    audio_peaks = select_audio_signal_timestamps(context, frame_count)
    scene_changes: list[float] = []
    if context.sourcePath:
        try:
            scene_changes = [item.timestamp_seconds for item in detect_scene_changes(context.sourcePath, context.source.durationSeconds, max_changes=frame_count)]
        except Exception:
            scene_changes = []
    return SignalBundle(
        transcriptCues=transcript_cues,
        selectedTranscriptCues=selected_transcript_cues,
        transcriptTimestamps=transcript_timestamps,
        audioPeaks=audio_peaks,
        sceneChanges=scene_changes,
    )


def _signal_sources(context: PlannerContext, signals: SignalBundle) -> list[str]:
    return [
        "video_frames",
        "timed_transcript" if signals.transcriptCues else ("creative_prompt" if context.task.creativePrompt else "no_transcript"),
        "audio_peaks" if signals.audioPeaks else "no_audio_signal",
        "scene_boundaries" if signals.sceneChanges else "no_scene_signal",
    ]


def _nearest_dialogue_block(signals: SignalBundle, timestamp_seconds: float) -> DialogueBlock | None:
    blocks = build_dialogue_blocks(signals.transcriptCues)
    if not blocks:
        return None
    return min(
        blocks,
        key=lambda block: abs(((block.startSeconds + block.endSeconds) / 2) - timestamp_seconds),
    )


def _suggest_event_window(
    *,
    focus_seconds: float,
    signals: SignalBundle,
    source_duration: float,
    min_duration: float,
    max_duration: float,
) -> tuple[float, float]:
    boundaries = [0.0, *signals.sceneChanges, source_duration]
    block = _nearest_dialogue_block(signals, focus_seconds)
    local_window = max(min_duration * 0.92, min(max_duration * 0.72, 4.2))
    start_seconds = max(0.0, focus_seconds - local_window * 0.42)
    end_seconds = min(source_duration, focus_seconds + local_window * 0.58)

    if block is not None and block.startSeconds <= focus_seconds <= block.endSeconds:
        start_seconds = min(start_seconds, max(0.0, block.startSeconds - 0.35))
        end_seconds = max(end_seconds, min(source_duration, block.endSeconds + 0.3))

    nearby_start_boundaries = [item for item in boundaries if abs(item - start_seconds) <= 1.2]
    nearby_end_boundaries = [item for item in boundaries if abs(item - end_seconds) <= 1.2]
    if nearby_start_boundaries:
        start_seconds = min(nearby_start_boundaries, key=lambda item: abs(item - start_seconds))
    if nearby_end_boundaries:
        end_seconds = min(nearby_end_boundaries, key=lambda item: abs(item - end_seconds))

    if end_seconds - start_seconds < min_duration:
        deficit = min_duration - (end_seconds - start_seconds)
        start_seconds = max(0.0, start_seconds - deficit * 0.45)
        end_seconds = min(source_duration, end_seconds + deficit * 0.55)

    if end_seconds - start_seconds > max_duration:
        overflow = (end_seconds - start_seconds) - max_duration
        start_seconds += overflow * 0.45
        end_seconds -= overflow * 0.55

    start_seconds = clamp(start_seconds, 0.0, max(0.0, source_duration - 0.5))
    end_seconds = clamp(end_seconds, start_seconds + 0.5, source_duration)
    return round(start_seconds, 3), round(end_seconds, 3)


def _source_entries(context: PlannerContext) -> list[dict[str, object]]:
    entries = context.sourceTimeline or []
    normalized: list[dict[str, object]] = []
    for index, entry in enumerate(entries):
        source_path = entry.get("source_path")
        if source_path is None:
            continue
        normalized.append(
            {
                "asset_id": str(entry.get("asset_id") or f"source-{index + 1}"),
                "file_name": str(entry.get("file_name") or f"素材 {index + 1}"),
                "source_path": Path(str(source_path)),
                "duration_seconds": max(0.6, float(entry.get("duration_seconds") or context.source.durationSeconds)),
                "start_offset": float(entry.get("start_offset") or 0.0),
                "end_offset": float(entry.get("end_offset") or context.source.durationSeconds),
            }
        )
    if normalized:
        return normalized
    if context.sourcePath:
        return [
            {
                "asset_id": context.task.sourceAssetIds[0] if context.task.sourceAssetIds else "source-1",
                "file_name": context.task.sourceFileNames[0] if context.task.sourceFileNames else context.task.title,
                "source_path": Path(context.sourcePath),
                "duration_seconds": max(0.6, float(context.source.durationSeconds)),
                "start_offset": 0.0,
                "end_offset": float(context.source.durationSeconds),
            }
        ]
    return []


def _uniform_shot_windows(duration_seconds: float, segment_count: int) -> list[tuple[float, float]]:
    safe_duration = max(0.6, float(duration_seconds))
    normalized_count = max(1, min(segment_count, 18))
    step = safe_duration / normalized_count
    windows: list[tuple[float, float]] = []
    for index in range(normalized_count):
        start = round(step * index, 3)
        end = round(safe_duration if index == normalized_count - 1 else step * (index + 1), 3)
        if end - start < 0.45:
            end = round(min(safe_duration, start + 0.45), 3)
        windows.append((start, end))
    return windows


def _shot_windows_for_source(
    source_path: Path,
    duration_seconds: float,
    desired_count: int,
) -> list[tuple[float, float]]:
    safe_duration = max(0.6, float(duration_seconds))
    scene_candidates: list[float] = []
    try:
        scene_candidates = [
            item.timestamp_seconds
            for item in detect_scene_changes(
                source_path,
                safe_duration,
                max_changes=max(6, min(24, desired_count * 2)),
            )
        ]
    except Exception:
        scene_candidates = []

    if not scene_candidates:
        return _uniform_shot_windows(safe_duration, max(4, min(desired_count, 12)))

    boundaries = [0.0]
    for timestamp in scene_candidates:
        bounded = round(min(max(0.0, float(timestamp)), max(0.0, safe_duration - 0.2)), 3)
        if bounded <= boundaries[-1] + 0.25:
            continue
        boundaries.append(bounded)
    boundaries.append(round(safe_duration, 3))

    windows: list[tuple[float, float]] = []
    for index in range(len(boundaries) - 1):
        start = boundaries[index]
        end = boundaries[index + 1]
        if end - start < 0.45 and windows:
            previous_start, _ = windows[-1]
            windows[-1] = (previous_start, round(end, 3))
            continue
        if end - start < 0.45:
            end = round(min(safe_duration, start + 0.45), 3)
        windows.append((round(start, 3), round(end, 3)))

    if len(windows) > max(6, min(24, desired_count * 2)):
        stride = max(1, round(len(windows) / max(6, min(24, desired_count * 2))))
        windows = [window for idx, window in enumerate(windows) if idx % stride == 0][: max(6, min(24, desired_count * 2))]
        if windows[-1][1] < safe_duration:
            windows[-1] = (windows[-1][0], round(safe_duration, 3))
    return windows


def _shot_frame_requests(shot_windows: list[tuple[float, float]]) -> list[tuple[int, str, float]]:
    requests: list[tuple[int, str, float]] = []
    for shot_index, (start_seconds, end_seconds) in enumerate(shot_windows, start=1):
        duration_seconds = max(0.45, end_seconds - start_seconds)
        midpoint = round(start_seconds + duration_seconds * 0.5, 3)
        requests.append((shot_index, "中段画面", midpoint))
        if duration_seconds >= 5.2:
            requests.append((shot_index, "前段画面", round(start_seconds + duration_seconds * 0.28, 3)))
            requests.append((shot_index, "后段画面", round(end_seconds - duration_seconds * 0.22, 3)))
    return requests


def _vision_shot_payload(result: VisionAnalysisResult | None) -> list[dict[str, object]]:
    if result is None:
        return []
    payload: list[dict[str, object]] = []
    for source in result.sources:
        payload.append(
            {
                "sourceAssetId": source.sourceAssetId,
                "sourceFileName": source.sourceFileName,
                "sourceDurationSeconds": round(source.sourceDurationSeconds, 3),
                "timelineStartOffset": round(source.timelineStartOffset, 3),
                "timelineEndOffset": round(source.timelineEndOffset, 3),
                "shots": [
                    {
                        "shotIndex": shot.shotIndex,
                        "localStartSeconds": round(shot.localStartSeconds, 3),
                        "localEndSeconds": round(shot.localEndSeconds, 3),
                        "timelineStartSeconds": round(shot.timelineStartSeconds, 3),
                        "timelineEndSeconds": round(shot.timelineEndSeconds, 3),
                        "summary": truncate_text(shot.summary, 120),
                        "subjects": shot.subjects[:4],
                        "action": truncate_text(shot.action or "", 64) or None,
                        "emotion": truncate_text(shot.emotion or "", 48) or None,
                        "location": truncate_text(shot.location or "", 48) or None,
                        "visualHook": truncate_text(shot.visualHook or "", 72) or None,
                        "dialogueHint": truncate_text(shot.dialogueHint or "", 72) or None,
                        "storyRole": truncate_text(shot.storyRole or "", 40) or None,
                        "confidence": shot.confidence,
                    }
                    for shot in source.shots
                ],
            }
        )
    return payload


class VisionEventAnalyzer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.gateway = PlannerModelGateway(settings)
        self.router = ModelRouter(settings)

    def _build_messages(
        self,
        context: PlannerContext,
        model_name: str,
        signals: SignalBundle,
        source_entry: dict[str, object],
    ) -> tuple[list[dict[str, object]], list[float], dict[str, object], list[dict[str, float | int | str]]]:
        source_path = Path(str(source_entry["source_path"]))
        source_duration = float(source_entry["duration_seconds"])
        desired_shot_count = max(
            self.settings.model.vision_frame_count * 2,
            min(18, max(6, int(source_duration / 4.0))),
        )
        shot_windows = _shot_windows_for_source(source_path, source_duration, desired_shot_count)
        shot_requests = _shot_frame_requests(shot_windows)
        if not shot_requests:
            raise RuntimeError("no visual shot windows extracted")

        with tempfile.TemporaryDirectory(prefix="ai-cut-vision-") as temp_dir:
            samples = sample_video_frames(
                source_path=source_path,
                output_dir=temp_dir,
                duration_seconds=source_duration,
                frame_count=len(shot_requests),
                timestamps=[timestamp for _, _, timestamp in shot_requests],
            )
            if not samples:
                raise RuntimeError("no visual samples extracted")

            shot_payload = [
                {
                    "shotIndex": shot_index,
                    "localStartSeconds": round(start_seconds, 3),
                    "localEndSeconds": round(end_seconds, 3),
                    "timelineStartSeconds": round(float(source_entry["start_offset"]) + start_seconds, 3),
                    "timelineEndSeconds": round(float(source_entry["start_offset"]) + end_seconds, 3),
                }
                for shot_index, (start_seconds, end_seconds) in enumerate(shot_windows, start=1)
            ]

            editing_mode = context.task.editingMode or "drama"
            vision_role_prompt = (
                "你是短剧逐镜头内容分析助手，只输出 JSON。"
                if editing_mode == "drama"
                else "你是混剪逐镜头内容分析助手，只输出 JSON。"
            )
            vision_goal_prompt = (
                "请覆盖这个视频中的每一个镜头段，描述镜头里发生了什么、人物状态、动作、情绪和最适合承担的剧情作用。"
                if editing_mode == "drama"
                else "请覆盖这个视频中的每一个镜头段，描述镜头里发生了什么、景别、动作、氛围和最适合承担的分镜作用。"
            )

            content: list[dict[str, object]] = [
                {
                    "type": "text",
                    "text": (
                        f"{vision_role_prompt}"
                        "当前只分析这一个源视频，必须覆盖下方给出的每个镜头段，不能只挑高点。"
                        "镜头边界只是分段依据，不代表重要性排序。"
                        f"{vision_goal_prompt}"
                        "不要直接输出最终剪辑时间点。"
                        "输出格式必须为："
                        '{"shots":[{"shotIndex":1,"summary":"...","subjects":["..."],"action":"...","emotion":"...","location":"...","visualHook":"...","dialogueHint":"...","storyRole":"...","confidence":0.88}],"events":[{"eventIndex":1,"title":"...","reason":"...","timestampSeconds":12.3,"confidence":0.92,"eventType":"...","relatedSubtitle":"..."}]}\n'
                        f"任务要求：{json.dumps(context.task.model_dump(), ensure_ascii=False)}\n"
                        f"当前源视频：{json.dumps({'sourceAssetId': source_entry['asset_id'], 'sourceFileName': source_entry['file_name'], 'sourceDurationSeconds': source_duration, 'timelineStartOffset': float(source_entry['start_offset']), 'timelineEndOffset': float(source_entry['end_offset'])}, ensure_ascii=False)}\n"
                        f"镜头段清单：{json.dumps(shot_payload, ensure_ascii=False)}\n"
                        f"创意补充：{json.dumps((context.task.creativePrompt or '').strip(), ensure_ascii=False)}\n"
                        f"字幕摘录：{json.dumps(truncate_transcript(context.transcriptText, 320), ensure_ascii=False)}\n"
                        "要求："
                        "1. shots 必须尽量覆盖镜头段清单中的每个 shotIndex，不要遗漏。"
                        "2. summary 要概括镜头内实际内容，不要写抽象空话。"
                        "3. storyRole 要写成类似 起势/对白推进/反应镜头/氛围建立/动作推进/收束/插叙 的短标签。"
                        "4. 如果能归纳更高层的事件，再额外输出 events；events 可以为空。"
                    ),
                }
            ]
            timestamps: list[float] = []
            sample_index = 0
            for shot_index, frame_label, timestamp in shot_requests:
                if sample_index >= len(samples):
                    break
                sample = samples[sample_index]
                sample_index += 1
                timestamps.append(sample.timestamp_seconds)
                shot_window = shot_windows[shot_index - 1]
                content.append(
                    {
                        "type": "text",
                        "text": (
                            f"镜头 {shot_index}，局部时间 {shot_window[0]:.1f}-{shot_window[1]:.1f} 秒，"
                            f"合成时间轴 {float(source_entry['start_offset']) + shot_window[0]:.1f}-{float(source_entry['start_offset']) + shot_window[1]:.1f} 秒，"
                            f"{frame_label}，采样时间 {timestamp:.1f} 秒。"
                        ),
                    }
                )
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _image_data_url(sample.image_path),
                        },
                    }
                )
            messages = [
                {"role": "system", "content": self.settings.prompts.planner_shot_analysis_json_only},
                {"role": "user", "content": content},
            ]
        signal_meta = {
            "audio_peak_count": len(signals.audioPeaks),
            "transcript_cue_count": len(signals.transcriptCues),
            "scene_change_count": len(signals.sceneChanges),
            "signal_sources": _signal_sources(context, signals),
            "source_asset_id": str(source_entry["asset_id"]),
            "source_file_name": str(source_entry["file_name"]),
            "shot_count": len(shot_windows),
        }
        return messages, timestamps, signal_meta, shot_payload

    def _call_model(
        self,
        model_name: str,
        context: PlannerContext,
        signals: SignalBundle,
        source_entry: dict[str, object],
    ) -> VisionSourceAnalysis:
        messages, frame_timestamps, signal_meta, shot_payload = self._build_messages(context, model_name, signals, source_entry)
        if context.trace is not None:
            context.trace(
                "vision",
                "vision.request",
                f"已向视觉模型 {model_name} 发送完整镜头分析请求。",
                {
                    "model": model_name,
                    "source_asset_id": str(source_entry["asset_id"]),
                    "source_file_name": str(source_entry["file_name"]),
                    "frame_count": len(frame_timestamps),
                    "frame_timestamps": frame_timestamps,
                    "shot_count": len(shot_payload),
                    "has_transcript": bool(signals.transcriptCues),
                    "editing_mode": "drama",
                    **signal_meta,
                },
                "INFO",
            )
        try:
            body, raw = self.gateway.invoke_vision(
                model_name=model_name,
                messages=messages,
                temperature=self.settings.model.temperature,
                max_tokens=self.settings.model.max_tokens,
            )
        except RuntimeError as exc:
            if context.trace is not None:
                context.trace(
                    "vision",
                    "vision.request_error",
                    f"视觉模型 {model_name} 请求失败。",
                    {
                        "model": model_name,
                        "source_asset_id": str(source_entry["asset_id"]),
                        "source_file_name": str(source_entry["file_name"]),
                        "error": str(exc),
                    },
                    "ERROR",
                )
            raise RuntimeError(f"Vision request failed ({model_name}): {exc}") from exc
        content = ""
        if isinstance(body, dict):
            if "choices" in body and body["choices"]:
                message = body["choices"][0].get("message", {})
                content = message.get("content", "")
            elif "output" in body:
                output = body["output"]
                if isinstance(output, dict):
                    content = output.get("text", "") or output.get("content", "")
        try:
            parsed, json_repairs = parse_json_object(content or raw)
        except (json.JSONDecodeError, ValueError) as exc:
            error_payload: dict[str, object] = {
                "model": model_name,
                "source_asset_id": str(source_entry["asset_id"]),
                "source_file_name": str(source_entry["file_name"]),
                "error": str(exc),
                "content_excerpt": truncate_transcript(content or raw, 1200),
            }
            if isinstance(exc, json.JSONDecodeError):
                error_payload.update(
                    {
                        "line": exc.lineno,
                        "column": exc.colno,
                        "char": exc.pos,
                        "error_context": truncate_transcript(
                            describe_json_error_context(exc.doc, exc.pos, 180),
                            500,
                        ),
                    }
                )
            if context.trace is not None:
                context.trace(
                    "vision",
                    "vision.parse_error",
                    f"视觉模型 {model_name} 返回的 JSON 无法解析。",
                    error_payload,
                    "WARN",
                )
            raise VisionSourceParseError(str(exc)) from exc
        shot_items = parsed.get("shots", [])
        events = parsed.get("events", [])
        if context.trace is not None:
            context.trace(
                "vision",
                "vision.response",
                f"视觉模型 {model_name} 已返回完整镜头分析结果。",
                {
                    "model": model_name,
                    "source_asset_id": str(source_entry["asset_id"]),
                    "source_file_name": str(source_entry["file_name"]),
                    "frame_count": len(frame_timestamps),
                    "frame_timestamps": frame_timestamps,
                    "shot_count": len(shot_payload),
                    "parsed_shot_count": len(shot_items) if isinstance(shot_items, list) else 0,
                    "parsed_event_count": len(events) if isinstance(events, list) else 0,
                    "event_titles": [
                        str(event.get("title", f"事件 {index + 1}"))[:80]
                        for index, event in enumerate(events[:6] if isinstance(events, list) else [])
                    ],
                    "event_types": [
                        str(event.get("eventType", ""))[:32]
                        for event in (events[:6] if isinstance(events, list) else [])
                        if str(event.get("eventType", "")).strip()
                    ],
                    "json_repairs": json_repairs,
                    "content_excerpt": truncate_transcript(content or raw, 1000),
                },
                "INFO",
            )
        shot_map = {
            int(item.get("shotIndex", index)): item
            for index, item in enumerate(shot_items if isinstance(shot_items, list) else [], start=1)
            if isinstance(item, dict)
        }
        shots: list[VisualShot] = []
        for shot in shot_payload:
            shot_index = int(shot["shotIndex"])
            shot_item = shot_map.get(shot_index, {})
            subjects = shot_item.get("subjects", [])
            if not isinstance(subjects, list):
                subjects = []
            shots.append(
                VisualShot(
                    sourceAssetId=str(source_entry["asset_id"]),
                    sourceFileName=str(source_entry["file_name"]),
                    shotIndex=shot_index,
                    localStartSeconds=float(shot["localStartSeconds"]),
                    localEndSeconds=float(shot["localEndSeconds"]),
                    timelineStartSeconds=float(shot["timelineStartSeconds"]),
                    timelineEndSeconds=float(shot["timelineEndSeconds"]),
                    summary=truncate_text(str(shot_item.get("summary", f"镜头 {shot_index} 内容待补充")), 160),
                    subjects=[truncate_text(str(item), 32) for item in subjects[:4] if str(item).strip()],
                    action=truncate_text(str(shot_item.get("action", "")).strip(), 80) or None,
                    emotion=truncate_text(str(shot_item.get("emotion", "")).strip(), 48) or None,
                    location=truncate_text(str(shot_item.get("location", "")).strip(), 48) or None,
                    visualHook=truncate_text(str(shot_item.get("visualHook", "")).strip(), 96) or None,
                    dialogueHint=truncate_text(str(shot_item.get("dialogueHint", "")).strip(), 96) or None,
                    storyRole=truncate_text(str(shot_item.get("storyRole", "")).strip(), 40) or None,
                    confidence=float(shot_item.get("confidence")) if shot_item.get("confidence") is not None else None,
                )
            )
        result: list[VisualInsight] = []
        for index, event in enumerate(events, start=1):
            result.append(
                VisualInsight(
                    title=str(event.get("title", f"事件 {index}")),
                    reason=str(event.get("reason", "由视觉模型识别到的剧情高点")),
                    focusSeconds=float(event.get("timestampSeconds", event.get("focusSeconds", 0.0))),
                    confidence=float(event.get("confidence")) if event.get("confidence") is not None else None,
                    eventType=str(event.get("eventType", "")).strip() or None,
                    relatedSubtitle=str(event.get("relatedSubtitle", "")).strip() or None,
                )
            )
        return VisionSourceAnalysis(
            sourceAssetId=str(source_entry["asset_id"]),
            sourceFileName=str(source_entry["file_name"]),
            sourceDurationSeconds=float(source_entry["duration_seconds"]),
            timelineStartOffset=float(source_entry["start_offset"]),
            timelineEndOffset=float(source_entry["end_offset"]),
            shots=shots,
            events=result,
        )

    def analyze(self, context: PlannerContext, signals: SignalBundle) -> VisionAnalysisResult | None:
        source_entries = _source_entries(context)
        if not source_entries:
            return None

        vision_target = self.router.resolve(capability="vision_analysis", kind="vision")
        model_name = vision_target.model_name

        collected_sources: list[VisionSourceAnalysis] = []
        all_frame_timestamps: list[float] = []
        if context.trace is not None:
            context.trace(
                "vision",
                "vision.attempt",
                f"开始调用视觉模型 {model_name} 逐素材分析完整镜头内容。",
                {
                    "model": model_name,
                    "source_count": len(source_entries),
                    "frame_budget_per_source": self.settings.model.vision_frame_count,
                },
                "INFO",
            )

        for source_entry in source_entries:
            source_label = str(source_entry["file_name"])
            source_analysis: VisionSourceAnalysis | None = None
            last_exc: Exception | None = None
            for attempt in range(2):
                try:
                    source_analysis = self._call_model(model_name, context, signals, source_entry)
                    break
                except VisionSourceParseError as exc:
                    last_exc = exc
                    if attempt == 0:
                        if context.trace is not None:
                            context.trace(
                                "vision",
                                "vision.source_retry_scheduled",
                                f"素材 {source_label} 的视觉 JSON 解析失败，准备重试一次。",
                                {
                                    "model": model_name,
                                    "source_asset_id": str(source_entry["asset_id"]),
                                    "source_file_name": source_label,
                                    "attempt": attempt + 1,
                                    "max_attempts": 2,
                                    "error": str(exc),
                                },
                                "WARN",
                            )
                        continue
                    raise RuntimeError(
                        f"视觉模型返回非法 JSON，素材 {source_label} 连续两次解析失败: {exc}"
                    ) from exc
            if source_analysis is None:
                if last_exc is not None:
                    raise RuntimeError(f"视觉模型分析失败，素材 {source_label}: {last_exc}") from last_exc
                raise RuntimeError(f"视觉模型分析失败，素材 {source_label} 未返回结果")

            collected_sources.append(source_analysis)
            all_frame_timestamps.extend([shot.timelineStartSeconds for shot in source_analysis.shots])

        if not collected_sources:
            raise RuntimeError(f"Vision model {model_name} produced no source analysis")

        analysis = VisionAnalysisResult(
            modelName=model_name,
            sources=collected_sources,
            shots=[shot for source in collected_sources for shot in source.shots],
            events=[event for source in collected_sources for event in source.events],
            frameTimestamps=sorted(round(timestamp, 3) for timestamp in all_frame_timestamps),
            signals=signals,
        )
        if context.workDir:
            output_path = Path(context.workDir) / "vision_analysis.json"
            output_path.write_text(
                json.dumps(
                    {
                        "model": model_name,
                        "editingMode": context.task.editingMode,
                        "sources": _vision_shot_payload(analysis),
                        "events": [
                            {
                                "title": event.title,
                                "reason": event.reason,
                                "timestampSeconds": event.focusSeconds,
                                "confidence": event.confidence,
                                "eventType": event.eventType,
                                "relatedSubtitle": event.relatedSubtitle,
                            }
                            for event in analysis.events
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            if context.trace is not None:
                context.trace(
                    "vision",
                    "vision.analysis_saved",
                    "完整镜头分析 JSON 已写入任务工作目录。",
                    {
                        "analysis_path": output_path.as_posix(),
                        "source_count": len(analysis.sources),
                        "shot_count": len(analysis.shots),
                    },
                    "INFO",
                )
        return analysis


class FusionPlanner:
    def __init__(self, settings: Settings, vision_analyzer: VisionEventAnalyzer | None = None):
        self.settings = settings
        self.vision_analyzer = vision_analyzer
        self.gateway = PlannerModelGateway(settings)
        self.router = ModelRouter(settings)

    def _trace_signal_candidates(self, context: PlannerContext, signals: SignalBundle) -> None:
        if context.trace is None:
            return
        if signals.sceneChanges:
            context.trace(
                "scene",
                "scene.changes_detected",
                "已检测到镜头切换边界，加入切点候选。",
                {
                    "scene_change_count": len(signals.sceneChanges),
                    "timestamps": signals.sceneChanges[:16],
                },
                "INFO",
            )
        if signals.audioPeaks:
            context.trace(
                "audio",
                "audio.peaks_detected",
                "已检测到音频峰值卡点，加入切点候选。",
                {
                    "peak_count": len(signals.audioPeaks),
                    "audio_peak_count": len(signals.audioPeaks),
                    "peaks": [
                        {"timestamp_seconds": timestamp, "energy": round(energy, 4)}
                        for timestamp, energy in signals.audioPeaks[:12]
                    ],
                },
                "INFO",
            )
        if signals.selectedTranscriptCues:
            context.trace(
                "planning",
                "planning.subtitle_signals",
                "已提取字幕强信号时间轴，加入切点候选。",
                {
                    "transcript_cue_count": len(signals.selectedTranscriptCues),
                    "signal_timestamps": signals.transcriptTimestamps[:12],
                },
                "INFO",
            )

    def _build_prompt(
        self,
        context: PlannerContext,
        signals: SignalBundle,
        vision_analysis: VisionAnalysisResult | None,
    ) -> str:
        task = context.task.model_dump()
        source = context.source.model_dump()
        transcript_excerpt = truncate_transcript(context.transcriptText)
        transcript_payload = [cue.__dict__ for cue in signals.transcriptCues[:48]]
        signal_transcript_payload = [cue.__dict__ for cue in signals.selectedTranscriptCues[:12]]
        audio_peaks_payload = [
            {"timestampSeconds": timestamp, "energy": round(energy, 4)}
            for timestamp, energy in signals.audioPeaks[:12]
        ]
        scene_changes_payload = signals.sceneChanges[:12]
        visual_shot_payload = _vision_shot_payload(vision_analysis)
        visual_events_payload = [
            {
                "eventIndex": index,
                "title": event.title,
                "reason": event.reason,
                "timestampSeconds": event.focusSeconds,
                "confidence": event.confidence,
                "eventType": event.eventType,
                "relatedSubtitle": event.relatedSubtitle,
                "suggestedWindow": {
                    "startSeconds": suggested_window[0],
                    "endSeconds": suggested_window[1],
                },
            }
            for index, event in enumerate(vision_analysis.events[:8], start=1)
            for suggested_window in [
                _suggest_event_window(
                    focus_seconds=event.focusSeconds,
                    signals=signals,
                    source_duration=context.source.durationSeconds,
                    min_duration=float(context.task.minDurationSeconds),
                    max_duration=float(context.task.maxDurationSeconds),
                )
            ]
        ] if vision_analysis else []
        role_header = "你是一个短剧剪辑规划引擎，只输出 JSON，不要解释。"
        goal_header = "目标：基于视觉事件理解、字幕时间轴、音频卡点和镜头切换信号，输出更容易停留、对白更完整、情绪爆点更准确的短剧切条方案。"
        mode_rules = "当前是短剧模式，请优先围绕高燃卡点、对白完整、反转、冲突升级和情绪爆点来决定切点。\n"
        reason_rule = "4. title 要像投放素材标题，reason 要说明这是哪个冲突/反转/高燃卡点。\n"
        mode_tail_rules = "8. 当前是短剧模式，优先围绕剧情高点和对白边界取点。\n"
        return (
            f"{role_header}\n"
            f"{goal_header}\n"
            "你必须先阅读上游 VL 给出的逐素材、逐镜头完整分析 JSON，再决定分镜脚本或剪辑时间点。\n"
            "字幕、音频卡点和镜头切换点只作为辅助微调信号，不能覆盖掉逐镜头内容理解。\n"
            "如果视觉事件里带了 suggestedWindow，可以把它当作参考，但最终应服从完整镜头分析 JSON。\n"
            f"{mode_rules}"
            "任务要求如下：\n"
            f"{json.dumps(task, ensure_ascii=False)}\n"
            "视频信息如下：\n"
            f"{json.dumps(source, ensure_ascii=False)}\n"
            f"素材文件列表：{json.dumps(context.task.sourceFileNames[:8], ensure_ascii=False)}\n"
            f"VL 逐镜头完整分析 JSON（优先阅读）：\n{json.dumps(visual_shot_payload, ensure_ascii=False)}\n"
            f"视觉事件理解结果（若为空表示视觉模型未返回可用事件）：\n{json.dumps(visual_events_payload, ensure_ascii=False)}\n"
            f"视觉事件来源模型：{json.dumps(vision_analysis.modelName if vision_analysis else '', ensure_ascii=False)}\n"
            f"强信号字幕时间轴：\n{json.dumps(signal_transcript_payload, ensure_ascii=False)}\n"
            f"音频峰值时间点：\n{json.dumps(audio_peaks_payload, ensure_ascii=False)}\n"
            f"镜头切换时间点：\n{json.dumps(scene_changes_payload, ensure_ascii=False)}\n"
            "如果提供了带时间戳字幕/台词，请将切点尽量贴近字幕时间边界，并确保不要把人物对白从中间截断。"
            "开头和结尾尽量贴近动作、句子、镜头切换或情绪落点边界，不要从连续动作的半截突然切入或切出。"
            "同时尽量把切点放在自然的声音衔接处，避免上一段声音戛然而止、下一段声音立即硬切。\n"
            "请基于上述信号直接推理并输出，输出格式必须为："
            '{"clips":[{"clipIndex":1,"title":"...","reason":"...","startSeconds":0,"endSeconds":10,"durationSeconds":10}]}\n'
            "带时间戳字幕/台词（若为空则表示未提供）：\n"
            f"{json.dumps(transcript_payload, ensure_ascii=False)}\n"
            "原始文本摘录（若为空则表示未提供）：\n"
            f"{json.dumps(transcript_excerpt, ensure_ascii=False)}\n"
            "要求：\n"
            "1. 输出 clips 数量必须为 1。\n"
            "2. startSeconds/endSeconds 必须先尊重逐镜头完整分析 JSON，再结合字幕/音频/镜头切换微调，不要均匀平铺。\n"
            "3. durationSeconds 必须等于 endSeconds-startSeconds，且满足时长区间。\n"
            f"{reason_rule}"
            "5. 优先完整保留一句关键对白或一个完整动作，不要切断句子中段。\n"
            "6. 如果镜头切换时间点足够接近 clip 边界，优先把边界贴近镜头切换点。\n"
            "7. clip 边界应尽量落在自然声学边界，避免明显音频断裂感。\n"
            f"{mode_tail_rules}"
        )

    def _call_model(
        self,
        model_name: str,
        context: PlannerContext,
        signals: SignalBundle,
        vision_analysis: VisionAnalysisResult | None,
    ) -> list[ClipPlan]:
        prompt = self._build_prompt(context, signals, vision_analysis)
        if context.trace is not None:
            context.trace(
                "fusion",
                "fusion.request",
                f"已向融合规划模型 {model_name} 发送最终剪辑规划请求。",
                {
                    "model": model_name,
                    "temperature": self.settings.model.temperature,
                    "max_tokens": self.settings.model.max_tokens,
                    "prompt_length": len(prompt),
                    "prompt_excerpt": truncate_transcript(prompt, 1200),
                    "has_transcript": bool(signals.transcriptCues),
                    "transcript_cue_count": len(signals.transcriptCues),
                    "audio_peak_count": len(signals.audioPeaks),
                    "scene_change_count": len(signals.sceneChanges),
                    "visual_source_count": len(vision_analysis.sources) if vision_analysis else 0,
                    "visual_shot_count": len(vision_analysis.shots) if vision_analysis else 0,
                    "visual_event_count": len(vision_analysis.events) if vision_analysis else 0,
                    "used_visual_events": bool(vision_analysis and vision_analysis.events),
                    "visual_model": vision_analysis.modelName if vision_analysis else "",
                    "signal_sources": _signal_sources(context, signals),
                    "editing_mode": "drama",
                    "source_asset_count": len(context.task.sourceAssetIds),
                    "source_file_names": context.task.sourceFileNames[:8],
                },
                "INFO",
            )
        try:
            body, raw = self.gateway.invoke_text_analysis(
                model_name=model_name,
                system_prompt=self.settings.prompts.planner_fusion_json_only,
                user_prompt=prompt,
                temperature=self.settings.model.temperature,
                max_tokens=self.settings.model.max_tokens,
            )
        except RuntimeError as exc:
            if context.trace is not None:
                context.trace(
                    "fusion",
                    "fusion.request_error",
                    f"融合规划模型 {model_name} 请求失败。",
                    {
                        "model": model_name,
                        "error": str(exc),
                    },
                    "ERROR",
                )
            raise RuntimeError(f"Fusion request failed ({model_name}): {exc}") from exc
        content = extract_llm_text_response(body if isinstance(body, dict) else {}, raw)
        try:
            parsed, json_repairs = parse_json_object(content or raw)
        except (json.JSONDecodeError, ValueError) as exc:
            error_payload: dict[str, object] = {
                "model": model_name,
                "error": str(exc),
                "content_excerpt": truncate_transcript(content or raw, 1400),
            }
            if isinstance(exc, json.JSONDecodeError):
                error_payload.update(
                    {
                        "line": exc.lineno,
                        "column": exc.colno,
                        "char": exc.pos,
                        "error_context": truncate_transcript(
                            describe_json_error_context(exc.doc, exc.pos, 180),
                            500,
                        ),
                    }
                )
            if context.trace is not None:
                context.trace(
                    "fusion",
                    "fusion.parse_error",
                    f"融合规划模型 {model_name} 返回的 JSON 无法解析。",
                    error_payload,
                    "WARN",
                )
            raise
        clips = parsed.get("clips", [])
        if context.trace is not None:
            context.trace(
                "fusion",
                "fusion.response",
                f"融合规划模型 {model_name} 已返回最终剪辑方案。",
                {
                    "model": model_name,
                    "raw_length": len(raw),
                    "content_excerpt": truncate_transcript(content or raw, 1200),
                    "parsed_clip_count": len(clips) if isinstance(clips, list) else 0,
                    "visual_source_count": len(vision_analysis.sources) if vision_analysis else 0,
                    "visual_shot_count": len(vision_analysis.shots) if vision_analysis else 0,
                    "visual_event_count": len(vision_analysis.events) if vision_analysis else 0,
                    "used_visual_events": bool(vision_analysis and vision_analysis.events),
                    "visual_model": vision_analysis.modelName if vision_analysis else "",
                    "json_repairs": json_repairs,
                    "clip_titles": [
                        str(clip.get("title", f"素材 {index + 1}"))[:80]
                        for index, clip in enumerate(clips[:5] if isinstance(clips, list) else [])
                    ],
                },
                "INFO",
            )
        result: list[ClipPlan] = []
        for index, clip in enumerate(clips, start=1):
            result.append(
                ClipPlan(
                    clipIndex=int(clip.get("clipIndex", index)),
                    title=str(clip.get("title", f"素材 {index}")),
                    reason=str(clip.get("reason", "由模型规划生成")),
                    startSeconds=float(clip.get("startSeconds", 0.0)),
                    endSeconds=float(clip.get("endSeconds", 0.0)),
                    durationSeconds=float(clip.get("durationSeconds", 0.0)),
                )
            )
        return result

    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        text_model = self.router.resolve(capability="planner_fusion", kind="text")
        signals = collect_signal_bundle(context, self.settings.model.vision_frame_count)
        self._trace_signal_candidates(context, signals)

        vision_analysis: VisionAnalysisResult | None = None
        if self.vision_analyzer is not None and context.sourcePath:
            vision_analysis = self.vision_analyzer.analyze(context, signals)

        model_name = text_model.model_name
        if context.trace is not None:
            context.trace(
                "fusion",
                "fusion.attempt",
                f"开始调用融合规划模型 {model_name} 生成最终剪辑方案。",
                {
                    "model": model_name,
                    "provider": text_model.provider_name,
                    "mode": text_model.provider_name,
                    "visual_source_count": len(vision_analysis.sources) if vision_analysis else 0,
                    "visual_shot_count": len(vision_analysis.shots) if vision_analysis else 0,
                    "visual_event_count": len(vision_analysis.events) if vision_analysis else 0,
                    "used_visual_events": bool(vision_analysis and vision_analysis.events),
                    "visual_model": vision_analysis.modelName if vision_analysis else "",
                },
                "INFO",
            )
        clips = self._call_model(model_name, context, signals, vision_analysis)
        if not clips:
            raise RuntimeError("Fusion planner returned no clips")
        return clips


class PlannerChain:
    def __init__(self, planners: list[Planner]):
        self.planners = planners

    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        for planner in self.planners:
            clips = planner.plan(context)
            if clips:
                return clips
        raise RuntimeError("No planner produced clips")


def build_planner(settings: Settings) -> PlannerChain:
    planners: list[Planner] = [FusionPlanner(settings, vision_analyzer=VisionEventAnalyzer(settings))]
    return PlannerChain(planners)


_SRT_BLOCK_RE = re.compile(
    r"(?:^\s*\d+\s*$\n)?^\s*(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)\s*-->\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)\s*$\n(?P<text>.*?)(?=\n{2,}|\Z)",
    re.MULTILINE | re.DOTALL,
)


def parse_timestamp_to_seconds(value: str) -> float:
    normalized = value.strip().replace(",", ".")
    parts = normalized.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"invalid timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_transcript_cues(text: str | None) -> list[TranscriptCue]:
    if not text or not text.strip():
        return []

    cues: list[TranscriptCue] = []
    for match in _SRT_BLOCK_RE.finditer(text.strip()):
        raw_text = " ".join(line.strip() for line in match.group("text").splitlines() if line.strip())
        if not raw_text:
            continue
        try:
            start_seconds = parse_timestamp_to_seconds(match.group("start"))
            end_seconds = parse_timestamp_to_seconds(match.group("end"))
        except Exception:
            continue
        if end_seconds <= start_seconds:
            continue
        cues.append(
            TranscriptCue(
                startSeconds=round(start_seconds, 3),
                endSeconds=round(end_seconds, 3),
                text=raw_text[:500],
            )
        )
    return cues


def build_dialogue_blocks(cues: list[TranscriptCue], max_gap_seconds: float = 0.45) -> list[DialogueBlock]:
    if not cues:
        return []

    ordered = sorted(cues, key=lambda cue: (cue.startSeconds, cue.endSeconds))
    blocks: list[DialogueBlock] = []
    current: list[TranscriptCue] = [ordered[0]]

    for cue in ordered[1:]:
        previous = current[-1]
        if cue.startSeconds - previous.endSeconds <= max_gap_seconds:
            current.append(cue)
            continue
        blocks.append(
            DialogueBlock(
                startSeconds=current[0].startSeconds,
                endSeconds=current[-1].endSeconds,
                text=" ".join(item.text for item in current)[:800],
                cues=current[:],
            )
        )
        current = [cue]

    blocks.append(
        DialogueBlock(
            startSeconds=current[0].startSeconds,
            endSeconds=current[-1].endSeconds,
            text=" ".join(item.text for item in current)[:800],
            cues=current[:],
        )
    )
    return blocks


def truncate_transcript(text: str | None, limit: int = 4000) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."
