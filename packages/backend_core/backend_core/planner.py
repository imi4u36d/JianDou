from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import json
import urllib.error
import urllib.request

from .config import Settings
from .schemas import ClipPlan, MediaProbe, TaskSpec
from .utils import clamp, extract_json_object


@dataclass(frozen=True)
class PlannerContext:
    task: TaskSpec
    source: MediaProbe


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
            if clip_count == 1:
                start_seconds = max(0.0, (source.durationSeconds - target_duration) / 2)
            else:
                ratio = index / max(1, clip_count - 1)
                start_seconds = window * ratio
            end_seconds = min(source.durationSeconds, start_seconds + target_duration)
            duration_seconds = max(1.0, end_seconds - start_seconds)
            title_hint = task.creativePrompt.strip() if task.creativePrompt else "高能切片"
            title = f"{task.title[:18]} - {index + 1}"
            if title_hint:
                title = f"{title} / {title_hint[:12]}"
            reason = (
                f"基于时长区间 {task.minDurationSeconds}-{task.maxDurationSeconds} 秒自动生成，"
                f"适配 {task.platform} 投放。"
            )
            if task.creativePrompt:
                reason += f" 创意提示：{task.creativePrompt[:120]}"
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
        return clips


class QwenPlanner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _build_prompt(self, context: PlannerContext) -> str:
        task = context.task.model_dump()
        source = context.source.model_dump()
        candidates = HeuristicPlanner(self.settings).plan(context)
        return (
            "你是一个短剧剪辑规划引擎，只输出 JSON，不要解释。\n"
            "任务要求如下：\n"
            f"{json.dumps(task, ensure_ascii=False)}\n"
            "视频信息如下：\n"
            f"{json.dumps(source, ensure_ascii=False)}\n"
            "请在候选片段基础上优化标题和理由，输出格式必须为："
            '{"clips":[{"clipIndex":1,"title":"...","reason":"...","startSeconds":0,"endSeconds":10,"durationSeconds":10}]}\n'
            "候选片段：\n"
            f"{json.dumps([c.model_dump() for c in candidates], ensure_ascii=False)}\n"
        )

    def plan(self, context: PlannerContext) -> list[ClipPlan]:
        if not self.settings.model.api_key or not self.settings.model.endpoint:
            raise RuntimeError("Qwen provider is not configured")

        payload = {
            "model": self.settings.model.model_name,
            "messages": [
                {"role": "system", "content": "You are a precise JSON-only planning engine."},
                {"role": "user", "content": self._build_prompt(context)},
            ],
            "temperature": 0.2,
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
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Qwen request failed: {exc}") from exc

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
