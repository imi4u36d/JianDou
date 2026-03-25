from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
import json
import re
import urllib.error
import urllib.request

from .config import Settings
from .schemas import ClipPlan, MediaProbe, TaskSpec
from .utils import clamp, extract_json_object


@dataclass(frozen=True)
class PlannerContext:
    task: TaskSpec
    source: MediaProbe
    transcriptText: str | None = None
    trace: Callable[[str, str, str, dict[str, object] | None, str], None] | None = None


@dataclass(frozen=True)
class TranscriptCue:
    startSeconds: float
    endSeconds: float
    text: str


class Planner(Protocol):
    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        raise NotImplementedError


class HeuristicPlanner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        task = context.task
        source = context.source
        clip_count = max(1, min(task.outputCount, self.settings.pipeline.max_output_count))
        transcript_cues = parse_transcript_cues(context.transcriptText)
        if context.trace is not None:
            context.trace(
                "planning",
                "heuristic.start",
                "Using heuristic planner fallback.",
                {
                    "clip_count": clip_count,
                    "transcript_cue_count": len(transcript_cues),
                },
                "INFO",
            )
        target_duration = clamp(
            (task.minDurationSeconds + task.maxDurationSeconds) / 2,
            float(task.minDurationSeconds),
            float(task.maxDurationSeconds),
        )
        max_available = max(1.0, source.durationSeconds - 0.5)
        target_duration = min(target_duration, max_available)
        window = max(0.0, source.durationSeconds - target_duration)

        clips: list[ClipPlan] = []
        for index in range(clip_count):
            cue = _pick_cue(transcript_cues, index, clip_count)
            if cue is not None:
                cue_center = (cue.startSeconds + cue.endSeconds) / 2
                start_seconds = clamp(
                    cue_center - target_duration * 0.35,
                    0.0,
                    max(0.0, source.durationSeconds - target_duration),
                )
                title_hint = cue.text[:16]
                semantic_hint = f"参考字幕片段：{cue.text[:80]}"
            elif clip_count == 1:
                start_seconds = max(0.0, (source.durationSeconds - target_duration) / 2)
                title_hint = task.creativePrompt.strip() if task.creativePrompt else "高能切片"
                semantic_hint = ""
            else:
                ratio = index / max(1, clip_count - 1)
                start_seconds = window * ratio
                title_hint = task.creativePrompt.strip() if task.creativePrompt else "高能切片"
                semantic_hint = ""
            end_seconds = min(source.durationSeconds, start_seconds + target_duration)
            duration_seconds = max(1.0, end_seconds - start_seconds)
            title = f"{task.title[:18]} - {index + 1}"
            if title_hint:
                title = f"{title} / {title_hint[:12]}"
            reason = (
                f"基于时长区间 {task.minDurationSeconds}-{task.maxDurationSeconds} 秒自动生成，"
                f"适配 {task.platform} 投放。"
            )
            if task.creativePrompt:
                reason += f" 创意提示：{task.creativePrompt[:120]}"
            if semantic_hint:
                reason += f" {semantic_hint}"
            clips.append(
                ClipPlan(
                    clipIndex=index + 1,
                    title=title,
                    reason=reason,
                    startSeconds=round(start_seconds, 3),
                    endSeconds=round(end_seconds, 3),
                    durationSeconds=round(duration_seconds, 3),
                )
            )
        if context.trace is not None:
            context.trace(
                "planning",
                "heuristic.completed",
                "Heuristic planner produced candidate clips.",
                {
                    "clip_count": len(clips),
                },
                "INFO",
            )
        return clips


class QwenPlanner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _build_prompt(self, context: PlannerContext) -> str:
        task = context.task.model_dump()
        source = context.source.model_dump()
        candidates = HeuristicPlanner(self.settings).plan(context)
        transcript_cues = parse_transcript_cues(context.transcriptText)
        transcript_excerpt = truncate_transcript(context.transcriptText)
        transcript_payload = [cue.__dict__ for cue in transcript_cues[:120]]
        return (
            "你是一个短剧投放剪辑规划引擎，只输出 JSON，不要解释。\n"
            "目标：为短剧投放生成更容易停留、冲突更强、信息更完整的切条方案。\n"
            "你必须优先利用带时间戳字幕/台词来决定切点；如果没有时间戳文本，再退化为基于视频元信息和候选片段规划。\n"
            "任务要求如下：\n"
            f"{json.dumps(task, ensure_ascii=False)}\n"
            "视频信息如下：\n"
            f"{json.dumps(source, ensure_ascii=False)}\n"
            "如果提供了带时间戳字幕/台词，请将切点尽量贴近字幕时间边界，并确保理由体现剧情冲突、反转、情绪爆点或转化钩子。\n"
            "请在候选片段基础上优化标题和理由，输出格式必须为："
            '{"clips":[{"clipIndex":1,"title":"...","reason":"...","startSeconds":0,"endSeconds":10,"durationSeconds":10}]}\n'
            "候选片段：\n"
            f"{json.dumps([c.model_dump() for c in candidates], ensure_ascii=False)}\n"
            "带时间戳字幕/台词（若为空则表示未提供）：\n"
            f"{json.dumps(transcript_payload, ensure_ascii=False)}\n"
            "原始文本摘录（若为空则表示未提供）：\n"
            f"{json.dumps(transcript_excerpt, ensure_ascii=False)}\n"
            "要求：\n"
            "1. 输出 clips 数量必须等于 outputCount。\n"
            "2. startSeconds/endSeconds 必须落在视频时长内。\n"
            "3. durationSeconds 必须等于 endSeconds-startSeconds，且满足时长区间。\n"
            "4. title 要像投放素材标题，reason 要说明为什么这个片段值得切。\n"
        )

    def _call_model(self, model_name: str, context: PlannerContext) -> list[ClipPlan]:
        prompt = self._build_prompt(context)
        if context.trace is not None:
            context.trace(
                "llm",
                "qwen.request",
                f"Sending planning request to model {model_name}.",
                {
                    "model": model_name,
                    "temperature": self.settings.model.temperature,
                    "max_tokens": self.settings.model.max_tokens,
                    "prompt_length": len(prompt),
                    "prompt_excerpt": truncate_transcript(prompt, 1200),
                    "has_transcript": bool(context.transcriptText),
                    "transcript_cue_count": len(parse_transcript_cues(context.transcriptText)),
                },
                "INFO",
            )
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a precise JSON-only planning engine."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.settings.model.temperature,
            "max_tokens": self.settings.model.max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.settings.model.endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.model.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            if context.trace is not None:
                context.trace(
                    "llm",
                    "qwen.http_error",
                    f"Model request failed with HTTP {exc.code}.",
                    {
                        "model": model_name,
                        "status_code": exc.code,
                        "response_excerpt": truncate_transcript(body, 1200),
                    },
                    "ERROR",
                )
            raise RuntimeError(f"Qwen request failed ({model_name}): {exc.code} {body[:400]}") from exc
        except urllib.error.URLError as exc:
            if context.trace is not None:
                context.trace(
                    "llm",
                    "qwen.network_error",
                    "Model request failed before response was received.",
                    {
                        "model": model_name,
                        "error": str(exc),
                    },
                    "ERROR",
                )
            raise RuntimeError(f"Qwen request failed ({model_name}): {exc}") from exc

        body = json.loads(raw)
        content = ""
        if isinstance(body, dict):
            if "choices" in body and body["choices"]:
                message = body["choices"][0].get("message", {})
                content = message.get("content", "")
            elif "output" in body:
                output = body["output"]
                if isinstance(output, dict):
                    content = output.get("text", "") or output.get("content", "")
        json_text = extract_json_object(content or raw)
        parsed = json.loads(json_text)
        clips = parsed.get("clips", [])
        if context.trace is not None:
            context.trace(
                "llm",
                "qwen.response",
                f"Model {model_name} returned planning response.",
                {
                    "model": model_name,
                    "raw_length": len(raw),
                    "content_excerpt": truncate_transcript(content or raw, 1200),
                    "parsed_clip_count": len(clips) if isinstance(clips, list) else 0,
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
        if not self.settings.model.api_key or not self.settings.model.endpoint:
            raise RuntimeError("Qwen provider is not configured")

        model_names = [self.settings.model.model_name]
        if self.settings.model.fallback_model_name:
            model_names.append(self.settings.model.fallback_model_name)

        last_error: Exception | None = None
        for model_name in model_names:
            try:
                if context.trace is not None:
                    context.trace(
                        "llm",
                        "qwen.attempt",
                        f"Trying model {model_name}.",
                        {
                            "model": model_name,
                        },
                        "INFO",
                    )
                clips = self._call_model(model_name, context)
                if clips:
                    return clips
            except Exception as exc:
                if context.trace is not None:
                    context.trace(
                        "llm",
                        "qwen.attempt_failed",
                        f"Model {model_name} failed, trying next fallback if available.",
                        {
                            "model": model_name,
                            "error": str(exc),
                        },
                        "WARN",
                    )
                last_error = exc
        if last_error is not None:
            raise last_error
        return []


class PlannerChain:
    def __init__(self, planners: list[Planner]):
        self.planners = planners

    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        last_error: Exception | None = None
        for planner in self.planners:
            try:
                clips = planner.plan(context)
                if clips:
                    return clips
            except Exception as exc:  # noqa: PERF203 - planner fallback
                last_error = exc
        if last_error is not None:
            raise last_error
        return []


def build_planner(settings: Settings) -> PlannerChain:
    planners: list[Planner] = []
    if settings.model.provider.lower() == "qwen":
        planners.append(QwenPlanner(settings))
    planners.append(HeuristicPlanner(settings))
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


def truncate_transcript(text: str | None, limit: int = 4000) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."


def _pick_cue(cues: list[TranscriptCue], index: int, clip_count: int) -> TranscriptCue | None:
    if not cues:
        return None
    if clip_count <= 1:
        return cues[len(cues) // 2]
    position = round(index * (len(cues) - 1) / max(1, clip_count - 1))
    return cues[position]
