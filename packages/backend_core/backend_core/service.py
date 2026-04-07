from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import socket
import threading
import urllib.error
import urllib.request

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from .config import Settings
from .media import (
    RenderSegmentSpec,
    compose_source_timeline,
    detect_scene_changes,
    probe_media,
    render_output,
    render_output_segments,
)
from .models import SourceAsset, Task, TaskOutput
from .planner import PlannerChain, PlannerContext, build_dialogue_blocks, parse_transcript_cues
from .presets import get_task_presets
from .schemas import (
    AdminOverview,
    AdminOverviewCounts,
    AdminTaskActionFailure,
    AdminTaskBatchResult,
    AdminTraceEvent,
    ClipPlan,
    ClipSegment,
    CreateTaskRequest,
    GenerateCreativePromptRequest,
    GenerateCreativePromptResponse,
    GenerationOptionsResponse,
    MediaProbe,
    SourceAssetSummary,
    TaskDeleteResult,
    TaskDraft,
    TaskDetail,
    TaskListItem,
    TaskOutput as TaskOutputSchema,
    TaskTraceEvent,
    TaskSpec,
    TaskPreset,
    UploadResponse,
)
from .storage import MediaStorage
from .task_trace import TaskTraceWriter, read_task_trace
from .text_generation import (
    GenerationVersionInfo,
    GenerateTextMediaRequest,
    GenerateTextMediaResponse,
    GenerateTextScriptRequest,
    GenerateTextScriptResponse,
    TextGenerationEngine,
)
from .utils import clamp, isoformat_utc, new_id, parse_json_object, truncate_text, utcnow


def _iso(value: datetime | None) -> str:
    return isoformat_utc(value)


def _optional_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return isoformat_utc(value)


def _task_status(value: str) -> str:
    return value


def _timeline_segment_duration(segment: ClipSegment) -> float:
    return max(0.0, float(segment.endSeconds) - float(segment.startSeconds))


INTRO_TEMPLATE_LABELS = {
    "none": "不加片头",
    "cold_open": "冷开场直切",
    "flash_hook": "爆点闪切片头",
    "pressure_build": "情绪压迫片头",
    "hook": "开场冲突钩子",
    "cinematic": "情绪推进片头",
}

OUTRO_TEMPLATE_LABELS = {
    "none": "不加片尾",
    "suspense_hold": "悬念停顿片尾",
    "follow_hook": "追更钩子片尾",
    "question_freeze": "反问定格片尾",
    "brand": "品牌收束片尾",
    "call_to_action": "行动召唤片尾",
}

EDITING_MODE_LABELS = {
    "drama": "短剧剪辑",
    "mixcut": "混剪",
}

DRAMA_PROMPT_APPENDIX = (
    "短剧模式补充：请优先保留高燃卡点、对白完整、冲突升级、反转和情绪爆点，"
    "不要把一句对白或一组动作切断。"
)

MIXCUT_PROMPT_APPENDIX = (
    "混剪模式补充：请优先生成动态分镜脚本，可使用静帧快闪、插叙、回望镜头和对照镜头，"
    "从多素材中组织导演感编排，不要只围绕单一素材裁切。"
)

MIXCUT_CONTENT_TYPE_LABELS = {
    "generic": "通用混剪",
    "drama": "剧情混剪",
    "vlog": "Vlog 混剪",
    "food": "美食混剪",
    "fashion": "时尚混剪",
    "sports": "运动混剪",
}

MIXCUT_STYLE_PRESET_LABELS = {
    "director": "导演感推进",
    "music_sync": "音乐卡点",
}

EDITING_MODE_STYLE_HINTS = {
    "drama": "短剧高燃卡点",
    "mixcut": "分镜脚本编排",
}

MIXCUT_TRANSITION_STYLE_LABELS = {
    "cut": "硬切",
    "flash": "白闪转场",
    "fade_black": "黑场过渡",
    "crossfade": "叠化转场",
}

MIXCUT_LAYOUT_STYLE_LABELS = {
    "single_focus": "单素材聚焦",
    "director_story": "导演感拼接",
    "beat_montage": "节奏卡点拼接",
}

MIXCUT_EFFECT_STYLE_LABELS = {
    "none": "无额外特效",
    "crossfade": "叠化过渡",
    "flash_cut": "白闪卡点",
    "fade_black": "黑场收束",
}

MIXCUT_TEMPLATE_LABELS = {
    "single_focus_cut": "单素材直切模板",
    "director_crossfade_story": "导演感叠化混剪模板",
    "music_sync_flash_montage": "音乐白闪混剪模板",
}

DISABLED_MIXCUT_CONTENT_TYPES = {"travel"}
DISABLED_MIXCUT_STYLE_PRESETS = {
    "travel_citywalk",
    "travel_landscape",
    "travel_healing",
    "travel_roadtrip",
}


class TaskService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        storage: MediaStorage,
        planner: PlannerChain,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage = storage
        self.planner = planner
        self.text_generator = TextGenerationEngine(settings=settings, storage=storage)
        self.worker = None

    def set_worker(self, worker) -> None:
        self.worker = worker

    def session(self) -> Session:
        return self.session_factory()

    def upload_video(self, file_obj, original_name: str, mime_type: str | None = None) -> UploadResponse:
        stored = self.storage.save_upload(file_obj, original_name, mime_type)
        with self.session() as session:
            asset = SourceAsset(
                id=stored.asset_id,
                original_file_name=stored.original_file_name,
                stored_file_name=stored.stored_file_name,
                storage_path=stored.relative_path,
                mime_type=mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
            )
            session.add(asset)
            session.commit()
        return UploadResponse(
            assetId=stored.asset_id,
            fileName=stored.original_file_name,
            fileUrl=stored.public_url,
            sizeBytes=stored.size_bytes,
        )

    def list_task_presets(self) -> list[TaskPreset]:
        return get_task_presets()

    def list_generation_options(self) -> GenerationOptionsResponse:
        return self.text_generator.list_options()

    def list_generation_versions(self) -> list[GenerationVersionInfo]:
        return self.text_generator.list_versions()

    def generate_text_image(
        self,
        payload: GenerateTextMediaRequest | dict[str, object],
    ) -> GenerateTextMediaResponse:
        return self.text_generator.generate_text_image(payload)

    def generate_text_video(
        self,
        payload: GenerateTextMediaRequest | dict[str, object],
    ) -> GenerateTextMediaResponse:
        return self.text_generator.generate_text_video(payload)

    def generate_text_script(
        self,
        payload: GenerateTextScriptRequest | dict[str, object],
    ) -> GenerateTextScriptResponse:
        return self.text_generator.generate_text_script(payload)

    def _normalize_editing_mode(
        self,
        editing_mode: str | None,
        mixcut_enabled: bool | None = None,
    ) -> str:
        normalized = (editing_mode or "").strip().lower()
        if normalized in {"drama", "mixcut"}:
            return normalized
        if mixcut_enabled:
            return "mixcut"
        return "drama"

    def _normalize_mixcut_content_type(self, value: str | None) -> str | None:
        normalized = (value or "").strip()
        if not normalized or normalized in DISABLED_MIXCUT_CONTENT_TYPES:
            return None
        return normalized

    def _normalize_mixcut_style_preset(self, value: str | None) -> str | None:
        normalized = (value or "").strip()
        if not normalized or normalized in DISABLED_MIXCUT_STYLE_PRESETS:
            return None
        return normalized

    def _editing_mode_label(self, editing_mode: str | None) -> str:
        return EDITING_MODE_LABELS.get(self._normalize_editing_mode(editing_mode), "短剧剪辑")

    def generate_creative_prompt(self, payload: GenerateCreativePromptRequest) -> GenerateCreativePromptResponse:
        if payload.minDurationSeconds > payload.maxDurationSeconds:
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")

        editing_mode = self._normalize_editing_mode(payload.editingMode, payload.mixcutEnabled)
        if not self.settings.model.api_key or not self.settings.model.endpoint:
            raise RuntimeError("creative prompt provider is not configured")

        model_name = self.settings.model.model_name
        generated = self._call_creative_prompt_model(model_name, payload)
        if not generated:
            raise RuntimeError("creative prompt model returned empty prompt")
        return GenerateCreativePromptResponse(
            prompt=self._append_editing_mode_prompt(
                generated,
                editing_mode=editing_mode,
                source_count=len(payload.sourceFileNames),
                source_names=payload.sourceFileNames,
                mixcut_content_type=payload.mixcutContentType,
                mixcut_style_preset=payload.mixcutStylePreset,
            ),
            source=model_name,
        )

    def _call_creative_prompt_model(
        self,
        model_name: str,
        payload: GenerateCreativePromptRequest,
    ) -> str:
        transcript_excerpt = truncate_text((payload.transcriptText or "").strip(), 1400) or ""
        editing_mode = self._normalize_editing_mode(payload.editingMode, payload.mixcutEnabled)
        mode_label = self._editing_mode_label(editing_mode)
        mode_hint = (
            "短剧模式强调高燃卡点、对白完整、冲突升级和反转情绪。"
            if editing_mode == "drama"
            else "混剪模式强调分镜脚本、静帧快闪、插叙、对照镜头和素材编排。"
        )
        request_prompt = (
            "你是视频混剪策划，请只输出 JSON，不要解释。\n"
            "目标：生成一段适合视频剪辑规划的大模型提示词，给后续剪辑模型使用。\n"
            "这段提示词必须是中文，长度控制在 70 到 140 个字。"
            f"当前编辑模式：{mode_label}。\n"
            f"{mode_hint}\n"
            "不要重复参数，不要写成说明文，不要出现序号。\n"
            f"任务标题：{payload.title}\n"
            f"平台：{payload.platform}\n"
            f"画幅：{payload.aspectRatio}\n"
            f"时长区间：{payload.minDurationSeconds}-{payload.maxDurationSeconds} 秒\n"
            f"输出数量：{payload.outputCount}\n"
            f"片头模板：{INTRO_TEMPLATE_LABELS.get(payload.introTemplate, payload.introTemplate)}\n"
            f"片尾模板：{OUTRO_TEMPLATE_LABELS.get(payload.outroTemplate, payload.outroTemplate)}\n"
            f"素材文件：{json.dumps(getattr(payload, 'sourceFileNames', [])[:6], ensure_ascii=False)}\n"
            f"混剪模式：{'开启' if editing_mode == 'mixcut' else '关闭'}\n"
            f"混剪题材：{MIXCUT_CONTENT_TYPE_LABELS.get((self._normalize_mixcut_content_type(payload.mixcutContentType) or ''), payload.mixcutContentType or '未指定')}\n"
            f"混剪风格：{MIXCUT_STYLE_PRESET_LABELS.get((self._normalize_mixcut_style_preset(payload.mixcutStylePreset) or ''), payload.mixcutStylePreset or '未指定')}\n"
            f"字幕/台词摘录：{json.dumps(transcript_excerpt, ensure_ascii=False)}\n"
            '输出格式：{"prompt":"..."}'
        )
        body = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a precise JSON-only creative prompt generator."},
                {"role": "user", "content": request_prompt},
            ],
            "temperature": min(0.55, max(0.18, self.settings.model.temperature + 0.08)),
            "max_tokens": min(500, self.settings.model.max_tokens),
        }
        request = urllib.request.Request(
            self.settings.model.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.model.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"creative prompt timed out: {exc}") from exc
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"creative prompt failed: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"creative prompt network failed: {exc}") from exc

        parsed = json.loads(raw)
        content = ""
        if isinstance(parsed, dict):
            if "choices" in parsed and parsed["choices"]:
                content = parsed["choices"][0].get("message", {}).get("content", "")
            elif "output" in parsed:
                output = parsed["output"]
                if isinstance(output, dict):
                    content = output.get("text", "") or output.get("content", "")
        parsed_prompt, _ = parse_json_object(content or raw)
        prompt = str(parsed_prompt.get("prompt", "")).strip()
        return truncate_text(prompt, 180) or ""

    def _build_fallback_creative_prompt(self, payload: GenerateCreativePromptRequest) -> str:
        duration_label = f"{payload.minDurationSeconds}-{payload.maxDurationSeconds}秒"
        intro = INTRO_TEMPLATE_LABELS.get(payload.introTemplate, payload.introTemplate)
        outro = OUTRO_TEMPLATE_LABELS.get(payload.outroTemplate, payload.outroTemplate)
        editing_mode = self._normalize_editing_mode(payload.editingMode, payload.mixcutEnabled)
        if editing_mode == "mixcut":
            semantic_hint = "优先编排镜头脚本，适度插入静帧、回望和对照镜头"
        elif payload.transcriptText and "-->" in payload.transcriptText:
            semantic_hint = "优先贴近字幕时间轴，完整保留关键对白和情绪爆点"
        elif payload.transcriptText and payload.transcriptText.strip():
            semantic_hint = "优先抓住对白冲突、反转信息和情绪升级"
        else:
            semantic_hint = "优先寻找高燃冲突、表情反转和动作爆点"
        style_label = MIXCUT_STYLE_PRESET_LABELS.get((self._normalize_mixcut_style_preset(payload.mixcutStylePreset) or ""), "")
        return (
            f"围绕《{payload.title}》做{payload.platform}平台投放剪辑，目标时长{duration_label}，"
            f"{semantic_hint}，开头采用{intro}，结尾落在{outro}，"
            f"{f'整体风格偏向{style_label}，' if style_label else ''}"
            "不要切断对白或连续动作，最后一拍要有明确落点。"
        )

    def _append_editing_mode_prompt(
        self,
        prompt: str | None,
        *,
        editing_mode: str,
        source_count: int | None = None,
        source_names: list[str] | None = None,
        mixcut_content_type: str | None = None,
        mixcut_style_preset: str | None = None,
    ) -> str:
        base = (prompt or "").strip()
        normalized_mode = self._normalize_editing_mode(editing_mode)
        if normalized_mode == "drama":
            appendix = DRAMA_PROMPT_APPENDIX
            if base and DRAMA_PROMPT_APPENDIX in base:
                return base
        else:
            if MIXCUT_PROMPT_APPENDIX in base:
                return base
            appendix = MIXCUT_PROMPT_APPENDIX
        details: list[str] = []
        if source_count is not None and source_count > 1:
            details.append(f"当前共有 {source_count} 个素材")
        if source_names:
            preview = "、".join([name for name in source_names[:3] if name])
            if preview:
                details.append(f"素材示例：{preview}")
        if normalized_mode == "mixcut":
            content_type_label = MIXCUT_CONTENT_TYPE_LABELS.get((self._normalize_mixcut_content_type(mixcut_content_type) or ""), "")
            if content_type_label:
                details.append(f"题材：{content_type_label}")
            style_label = MIXCUT_STYLE_PRESET_LABELS.get((self._normalize_mixcut_style_preset(mixcut_style_preset) or ""), "")
            if style_label:
                details.append(f"风格：{style_label}")
        if details:
            appendix = f"{appendix} {'；'.join(details)}。"
        if base:
            return f"{base}\n{appendix}"
        return appendix

    def _append_mixcut_prompt(
        self,
        prompt: str | None,
        *,
        mixcut_enabled: bool,
        source_count: int | None = None,
        source_names: list[str] | None = None,
        mixcut_content_type: str | None = None,
        mixcut_style_preset: str | None = None,
    ) -> str:
        return self._append_editing_mode_prompt(
            prompt,
            editing_mode="mixcut" if mixcut_enabled else "drama",
            source_count=source_count,
            source_names=source_names,
            mixcut_content_type=mixcut_content_type,
            mixcut_style_preset=mixcut_style_preset,
        )

    def _normalize_source_selection(
        self,
        session: Session,
        payload: CreateTaskRequest,
    ) -> tuple[list[SourceAsset], list[str]]:
        requested_ids = [item.strip() for item in payload.sourceAssetIds if item and item.strip()]
        if payload.sourceAssetId and payload.sourceAssetId.strip():
            requested_ids.insert(0, payload.sourceAssetId.strip())
        source_asset_ids = list(dict.fromkeys(requested_ids))
        if not source_asset_ids:
            raise ValueError("at least one source asset is required")

        assets: list[SourceAsset] = []
        for asset_id in source_asset_ids:
            asset = session.get(SourceAsset, asset_id)
            if asset is None:
                raise LookupError("source asset not found")
            assets.append(asset)

        requested_names = [item.strip() for item in payload.sourceFileNames if item and item.strip()]
        if not requested_names and payload.sourceFileName and payload.sourceFileName.strip():
            requested_names = [payload.sourceFileName.strip()]

        source_file_names: list[str] = []
        for index, asset in enumerate(assets):
            if index < len(requested_names):
                source_file_names.append(requested_names[index])
            else:
                source_file_names.append(asset.original_file_name)

        return assets, source_file_names

    def _source_name_summary(self, source_file_names: list[str]) -> str:
        cleaned = [item.strip() for item in source_file_names if item and item.strip()]
        if not cleaned:
            return "未命名素材"
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return "、".join(cleaned)
        return f"{cleaned[0]}、{cleaned[1]} 等 {len(cleaned)} 个素材"

    def _resolve_mixcut_visual_profile(
        self,
        *,
        editing_mode: str,
        mixcut_content_type: str | None,
        mixcut_style_preset: str | None,
        source_asset_count: int,
    ) -> dict[str, str]:
        if self._normalize_editing_mode(editing_mode) != "mixcut" or source_asset_count <= 1:
            return {
                "transition_style": "cut",
                "layout_style": "single_focus",
                "effect_style": "none",
                "mixcut_template": "single_focus_cut",
            }
        content_type = self._normalize_mixcut_content_type(mixcut_content_type)
        style_preset = self._normalize_mixcut_style_preset(mixcut_style_preset)
        if style_preset == "music_sync":
            return {
                "transition_style": "flash",
                "layout_style": "beat_montage",
                "effect_style": "flash_cut",
                "mixcut_template": "music_sync_flash_montage",
            }
        return {
            "transition_style": "crossfade",
            "layout_style": "director_story",
            "effect_style": "crossfade",
            "mixcut_template": "director_crossfade_story",
        }

    def get_task_trace(self, task_id: str, limit: int = 500) -> list[TaskTraceEvent]:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
        return read_task_trace(self.storage.task_trace_path(task_id), limit=limit)

    def create_task(self, payload: CreateTaskRequest) -> TaskDetail:
        if payload.minDurationSeconds > payload.maxDurationSeconds:
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")
        if payload.outputCount > self.settings.pipeline.max_output_count:
            raise ValueError(f"outputCount exceeds limit {self.settings.pipeline.max_output_count}")

        with self.session() as session:
            assets, source_file_names = self._normalize_source_selection(session, payload)
            primary_asset = assets[0]
            source_asset_ids = [asset.id for asset in assets]
            editing_mode = self._normalize_editing_mode(payload.editingMode, payload.mixcutEnabled)
            mixcut_enabled = editing_mode == "mixcut"
            mixcut_content_type = None
            mixcut_style_preset = None
            if mixcut_enabled:
                mixcut_content_type = self._normalize_mixcut_content_type(payload.mixcutContentType)
                mixcut_style_preset = self._normalize_mixcut_style_preset(payload.mixcutStylePreset)
            mixcut_profile = self._resolve_mixcut_visual_profile(
                editing_mode=editing_mode,
                mixcut_content_type=mixcut_content_type,
                mixcut_style_preset=mixcut_style_preset,
                source_asset_count=len(source_asset_ids),
            )
            creative_prompt = self._append_editing_mode_prompt(
                payload.creativePrompt,
                editing_mode=editing_mode,
                source_count=len(source_asset_ids),
                source_names=source_file_names,
                mixcut_content_type=mixcut_content_type,
                mixcut_style_preset=mixcut_style_preset,
            )
            source_file_name = self._source_name_summary(source_file_names)

            task = Task(
                id=new_id("task"),
                title=payload.title,
                source_asset_id=primary_asset.id,
                source_file_name=source_file_name,
                platform=payload.platform,
                aspect_ratio=payload.aspectRatio,
                min_duration_seconds=payload.minDurationSeconds,
                max_duration_seconds=payload.maxDurationSeconds,
                output_count=payload.outputCount,
                intro_template=payload.introTemplate,
                outro_template=payload.outroTemplate,
                creative_prompt=creative_prompt,
                model_provider=self.settings.model.provider,
                execution_mode=self.settings.app.execution_mode,
                status="PENDING",
                progress=0,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

        self._trace(
            task.id,
            "api",
            "task.created",
            "任务已创建，等待进入处理流程。",
            {
                "title": payload.title,
                "platform": payload.platform,
                "aspect_ratio": payload.aspectRatio,
                "duration_range": [payload.minDurationSeconds, payload.maxDurationSeconds],
                "output_count": payload.outputCount,
                "has_creative_prompt": bool(creative_prompt),
                "has_transcript": bool(payload.transcriptText),
                "transcript_cue_count": len(parse_transcript_cues(payload.transcriptText)),
                "source_asset_id": primary_asset.id,
                "source_asset_ids": source_asset_ids,
                "source_file_names": source_file_names,
                "source_asset_count": len(source_asset_ids),
                "editing_mode": editing_mode,
                "mixcut_enabled": mixcut_enabled,
                "mixcut_content_type": mixcut_content_type or "",
                "mixcut_style_preset": mixcut_style_preset or "",
                "mixcut_transition_style": mixcut_profile["transition_style"],
                "mixcut_layout_style": mixcut_profile["layout_style"],
                "mixcut_effect_style": mixcut_profile["effect_style"],
                "mixcut_template": mixcut_profile["mixcut_template"],
            },
        )
        self._save_task_context(
            task.id,
            transcript_text=payload.transcriptText,
            source_asset_ids=source_asset_ids,
            source_file_names=source_file_names,
            editing_mode=editing_mode,
            mixcut_enabled=mixcut_enabled,
            mixcut_content_type=mixcut_content_type,
            mixcut_style_preset=mixcut_style_preset,
            mixcut_transition_style=mixcut_profile["transition_style"],
            mixcut_layout_style=mixcut_profile["layout_style"],
            mixcut_effect_style=mixcut_profile["effect_style"],
            mixcut_template=mixcut_profile["mixcut_template"],
        )
        self.dispatch_task(task.id)
        return self.get_task_detail(task.id)

    def clone_task(self, task_id: str) -> TaskDraft:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            asset = session.get(SourceAsset, task.source_asset_id)
            return self._task_to_draft(task, asset)

    def list_tasks(
        self,
        q: str | None = None,
        status: str | None = None,
        platform: str | None = None,
    ) -> list[TaskListItem]:
        with self.session() as session:
            stmt = select(Task).options(selectinload(Task.outputs))
            filters = []
            if q:
                pattern = f"%{q}%"
                filters.append(
                    (
                        Task.title.ilike(pattern)
                        | Task.source_file_name.ilike(pattern)
                        | Task.creative_prompt.ilike(pattern)
                    )
                )
            if status:
                filters.append(Task.status == status)
            if platform:
                filters.append(Task.platform == platform)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.scalars(stmt.order_by(Task.created_at.desc())).all()
            return [self._task_to_list_item(row) for row in rows]

    def get_admin_overview(self) -> AdminOverview:
        tasks = self.list_tasks()
        total = len(tasks)
        return AdminOverview(
            generatedAt=_iso(utcnow()),
            counts=AdminOverviewCounts(
                totalTasks=total,
                queuedTasks=len([task for task in tasks if task.status == "PENDING"]),
                runningTasks=len([task for task in tasks if task.status in {"ANALYZING", "PLANNING", "RENDERING"}]),
                completedTasks=len([task for task in tasks if task.status == "COMPLETED"]),
                failedTasks=len([task for task in tasks if task.status == "FAILED"]),
                semanticTasks=len([task for task in tasks if task.hasTranscript]),
                timedSemanticTasks=len([task for task in tasks if task.hasTimedTranscript]),
                averageProgress=round(sum(task.progress for task in tasks) / total) if total else 0,
            ),
            modelReady=bool(
                self.settings.model.provider
                and self.settings.model.model_name
                and self.settings.model.endpoint
                and self.settings.model.api_key
            ),
            primaryModel=self.settings.model.model_name,
            visionModel=self.settings.model.vision_model_name,
            recentTasks=tasks[:8],
            recentFailures=[task for task in tasks if task.status == "FAILED"][:6],
            recentRunningTasks=[task for task in tasks if task.status in {"ANALYZING", "PLANNING", "RENDERING"}][:6],
            recentTraceCount=len(self.list_admin_traces(limit=120)),
        )

    def list_admin_traces(
        self,
        *,
        limit: int = 200,
        task_id: str | None = None,
        stage: str | None = None,
        level: str | None = None,
        q: str | None = None,
    ) -> list[AdminTraceEvent]:
        trace_dir = self.storage.temp_root / "task_trace"
        if not trace_dir.exists():
            return []

        requested_task_id = (task_id or "").strip()
        normalized_stage = (stage or "").strip()
        normalized_level = (level or "").strip().upper()
        keyword = (q or "").strip().lower()

        tasks_by_id: dict[str, TaskListItem] = {task.id: task for task in self.list_tasks()}
        candidate_paths: list[Path]
        if requested_task_id:
            candidate_paths = [self.storage.task_trace_path(requested_task_id)]
        else:
            candidate_paths = sorted(trace_dir.glob("*.jsonl"), reverse=True)

        combined: list[AdminTraceEvent] = []
        per_file_limit = max(50, limit)
        for path in candidate_paths:
            if not path.exists():
                continue
            current_task_id = path.stem
            task_meta = tasks_by_id.get(current_task_id)
            events = read_task_trace(path, limit=per_file_limit)
            for event in events:
                if normalized_stage and event.stage != normalized_stage:
                    continue
                if normalized_level and event.level.upper() != normalized_level:
                    continue
                if keyword:
                    haystack = " ".join(
                        [
                            current_task_id,
                            event.stage,
                            event.event,
                            event.message,
                            json.dumps(event.payload, ensure_ascii=False),
                            task_meta.title if task_meta else "",
                        ]
                    ).lower()
                    if keyword not in haystack:
                        continue
                combined.append(
                    AdminTraceEvent(
                        taskId=current_task_id,
                        taskTitle=task_meta.title if task_meta else None,
                        taskStatus=task_meta.status.value if task_meta else None,
                        **event.model_dump(),
                    )
                )

        combined.sort(key=lambda item: item.timestamp, reverse=True)
        return combined[:limit]

    def get_task_detail(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            stmt = (
                select(Task)
                .options(selectinload(Task.outputs), selectinload(Task.source_asset))
                .where(Task.id == task_id)
            )
            task = session.scalars(stmt).one_or_none()
            if task is None:
                raise LookupError("task not found")
            return self._task_to_detail(task)

    def retry_task(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            render_only_retry = self._can_retry_render_only(task)
            self._delete_outputs(session, task)
            task.status = "PENDING"
            task.progress = 0
            task.error_message = None
            if not render_only_retry:
                task.plan_json = None
            task.started_at = None
            task.finished_at = None
            task.retry_count = (task.retry_count or 0) + 1
            session.commit()
        self._save_task_context(task_id, render_only_retry=render_only_retry)

        self._trace(
            task_id,
            "api",
            "task.retry_requested",
            "Task retry requested.",
            {
                "retry_count": self.get_task_detail(task_id).retryCount,
                "render_only_retry": render_only_retry,
            },
        )
        self.dispatch_task(task_id)
        return self.get_task_detail(task_id)

    def delete_task(self, task_id: str) -> TaskDeleteResult:
        with self.session() as session:
            task = session.scalar(
                select(Task)
                .options(selectinload(Task.outputs))
                .where(Task.id == task_id)
            )
            if task is None:
                raise LookupError("task not found")
            if task.status in {"ANALYZING", "PLANNING", "RENDERING"}:
                raise ValueError("进行中的任务不能直接删除，请等待任务完成或失败后再删除。")

            self._trace(
                task_id,
                "api",
                "task.delete_requested",
                "已收到删除任务请求。",
                {"status": task.status},
                "WARN",
            )
            self._delete_outputs(session, task)
            session.delete(task)
            session.commit()

        self.storage.remove_task_artifacts(task_id)
        return TaskDeleteResult(taskId=task_id, deleted=True)

    def bulk_delete_tasks(self, task_ids: list[str]) -> AdminTaskBatchResult:
        succeeded: list[str] = []
        failed: list[AdminTaskActionFailure] = []
        for task_id in task_ids:
            try:
                self.delete_task(task_id)
                succeeded.append(task_id)
            except Exception as exc:
                failed.append(AdminTaskActionFailure(taskId=task_id, reason=str(exc)))
        return AdminTaskBatchResult(
            action="delete",
            requestedCount=len(task_ids),
            succeededTaskIds=succeeded,
            failed=failed,
        )

    def bulk_retry_tasks(self, task_ids: list[str]) -> AdminTaskBatchResult:
        succeeded: list[str] = []
        failed: list[AdminTaskActionFailure] = []
        for task_id in task_ids:
            try:
                self.retry_task(task_id)
                succeeded.append(task_id)
            except Exception as exc:
                failed.append(AdminTaskActionFailure(taskId=task_id, reason=str(exc)))
        return AdminTaskBatchResult(
            action="retry",
            requestedCount=len(task_ids),
            succeededTaskIds=succeeded,
            failed=failed,
        )

    def list_pending_task_ids(self, limit: int = 10) -> list[str]:
        with self.session() as session:
            rows = session.scalars(
                select(Task.id)
                .where(Task.status == "PENDING")
                .order_by(Task.created_at.asc())
                .limit(limit)
            ).all()
            return list(rows)

    def dispatch_task(self, task_id: str) -> None:
        if self.settings.using_inline_execution or self.worker is None or self.worker.job_queue is None:
            self._trace(
                task_id,
                "dispatch",
                "task.dispatched_inline",
                "任务通过本地线程直接开始执行。",
                {"execution_mode": self.settings.app.execution_mode},
            )
            thread = threading.Thread(target=self.process_task, args=(task_id,), daemon=True)
            thread.start()
            return
        try:
            self.worker.job_queue.enqueue(task_id)
            self._trace(
                task_id,
                "dispatch",
                "task.enqueued",
                "任务已进入队列，等待 worker 处理。",
                {"queue_mode": True},
            )
        except Exception:
            self._trace(
                task_id,
                "dispatch",
                "task.enqueue_failed",
                "任务入队失败，已回退为本地线程执行。",
                {"queue_mode": True},
                "WARN",
            )
            thread = threading.Thread(target=self.process_task, args=(task_id,), daemon=True)
            thread.start()

    def process_task(self, task_id: str) -> None:
        if not self._claim_task(task_id):
            return
        self._trace(
            task_id,
            "pipeline",
            "task.processing_started",
            "任务进入处理流水线。",
            {},
        )

        try:
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                asset = session.get(SourceAsset, task.source_asset_id)
                if asset is None:
                    task.status = "FAILED"
                    task.error_message = "source asset missing"
                    task.finished_at = utcnow()
                    session.commit()
                    self._trace(
                        task_id,
                        "pipeline",
                        "task.source_missing",
                        "任务源素材不存在，流程终止。",
                        {"source_asset_id": task.source_asset_id},
                        "ERROR",
                    )
                    return
                context_payload = self._load_task_context(task_id)
                context_source_ids = self._context_source_asset_ids(context_payload)
                if not context_source_ids:
                    context_source_ids = [task.source_asset_id]
                source_asset_ids = list(dict.fromkeys(context_source_ids))
                source_assets: list[SourceAsset] = []
                for source_asset_id in source_asset_ids:
                    source_asset = session.get(SourceAsset, source_asset_id)
                    if source_asset is None:
                        continue
                    source_assets.append(source_asset)
                if not source_assets:
                    source_assets = [asset]
                    source_asset_ids = [asset.id]
                source_file_names = self._context_source_file_names(context_payload)
                editing_mode = self._context_editing_mode(context_payload)
                if editing_mode != "mixcut" and len(source_assets) > 1:
                    source_assets = [source_assets[0]]
                    source_asset_ids = [source_assets[0].id]
                    source_file_names = [source_file_names[0]] if source_file_names else [source_assets[0].original_file_name]
                source_file_names = source_file_names or [source_assets[0].original_file_name]
                mixcut_enabled = editing_mode == "mixcut"
                mixcut_content_type = self._context_mixcut_content_type(context_payload) if mixcut_enabled else None
                mixcut_style_preset = self._context_mixcut_style_preset(context_payload) if mixcut_enabled else None
                mixcut_profile = self._resolve_mixcut_visual_profile(
                    editing_mode=editing_mode,
                    mixcut_content_type=mixcut_content_type,
                    mixcut_style_preset=mixcut_style_preset,
                    source_asset_count=len(source_asset_ids),
                )
                mixcut_transition_style = mixcut_profile["transition_style"]
                mixcut_layout_style = mixcut_profile["layout_style"]
                mixcut_effect_style = mixcut_profile["effect_style"]
                mixcut_template = mixcut_profile["mixcut_template"]
                if not source_file_names:
                    source_file_names = [source_assets[0].original_file_name]
                source_timeline = self._load_source_timeline(source_assets, source_file_names)
                source_path = self.storage.root / source_assets[0].storage_path
                mixcut_source_path = None
                if len(source_assets) > 1:
                    mixcut_source_path = self.storage.task_work_dir(task_id) / "mixcut_source.mp4"
                    try:
                        self._trace(
                            task_id,
                            "analysis",
                            "multisource.source_build_started",
                            "检测到多素材输入，开始构建组合源。",
                            {
                                "source_asset_ids": source_asset_ids,
                                "source_file_names": source_file_names,
                                "mixcut_enabled": mixcut_enabled,
                                "mixcut_content_type": mixcut_content_type or "",
                                "mixcut_style_preset": mixcut_style_preset or "",
                            },
                        )
                        built_path = compose_source_timeline(
                            [Path(str(entry["source_path"])) for entry in source_timeline],
                            mixcut_source_path,
                            task.aspect_ratio,
                        )
                        source_path = built_path
                        self._trace(
                            task_id,
                            "analysis",
                            "multisource.source_build_completed",
                            "多素材组合源已生成。",
                            {
                                "source_count": len(source_assets),
                                "output_path": built_path.as_posix(),
                                "timeline_total_seconds": round(
                                    sum(float(entry["duration_seconds"]) for entry in source_timeline),
                                    3,
                                ),
                            },
                        )
                    except Exception as exc:
                        self._trace(
                            task_id,
                            "analysis",
                            "multisource.source_build_failed",
                            "多素材组合源构建失败，回退到首个素材继续处理。",
                            {
                                "source_asset_ids": source_asset_ids,
                                "error": str(exc),
                            },
                            "WARN",
                        )
                        source_path = self.storage.root / source_assets[0].storage_path
        except Exception as exc:
            self._fail_task(task_id, exc, message="任务处理失败，未能完成素材预处理。")
            return

        try:
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "ANALYZING"
                task.progress = 10
                task.started_at = task.started_at or utcnow()
                session.commit()
                self._trace(
                    task_id,
                    "analysis",
                    "analysis.started",
                    "开始分析源视频素材。",
                    {"source_path": source_path.as_posix()},
                )

            probe = probe_media(source_path)
            self._trace(
                task_id,
                "analysis",
                "analysis.completed",
                "素材分析完成。",
                probe.model_dump(),
            )
            with self.session() as session:
                updated = False
                for entry in source_timeline:
                    asset = session.get(SourceAsset, str(entry["asset_id"]))
                    entry_probe = entry.get("probe")
                    if asset is None or not isinstance(entry_probe, MediaProbe):
                        continue
                    asset.duration_seconds = entry_probe.durationSeconds
                    asset.width = entry_probe.width
                    asset.height = entry_probe.height
                    asset.has_audio = entry_probe.hasAudio
                    updated = True
                if updated:
                    session.commit()

            context_payload = self._load_task_context(task_id)
            render_only_retry = self._context_render_only_retry(context_payload)
            if render_only_retry:
                with self.session() as session:
                    task = session.get(Task, task_id)
                    if task is None:
                        return
                    clips = self._parse_plan(task)
                self._save_task_context(task_id, render_only_retry=False)
                if clips:
                    self._trace(
                        task_id,
                        "render",
                        "render.retry_reuse_started",
                        "检测到渲染级重试，复用已有规划结果并直接重新导出。",
                        {
                            "clip_count": len(clips),
                            "source_asset_count": len(source_asset_ids),
                            "mixcut_enabled": mixcut_enabled,
                            "mixcut_content_type": mixcut_content_type or "",
                            "mixcut_style_preset": mixcut_style_preset or "",
                            "reused_existing_plan": True,
                        },
                    )
                    self._render_outputs(
                        task_id=task_id,
                        source_path=source_path,
                        probe=probe,
                        clips=clips,
                        source_timeline=source_timeline,
                        mixcut_transition_style=mixcut_transition_style,
                        mixcut_layout_style=mixcut_layout_style,
                        mixcut_effect_style=mixcut_effect_style,
                        mixcut_template=mixcut_template,
                    )

                    with self.session() as session:
                        task = session.get(Task, task_id)
                        if task is None:
                            return
                        task.status = "COMPLETED"
                        task.progress = 100
                        task.finished_at = utcnow()
                        session.commit()
                        self._trace(
                            task_id,
                            "pipeline",
                            "task.completed",
                            "任务处理完成，所有输出已生成。",
                            {
                                "output_count": len(clips),
                                "source_asset_count": len(source_asset_ids),
                                "mixcut_enabled": mixcut_enabled,
                                "mixcut_content_type": mixcut_content_type or "",
                                "mixcut_style_preset": mixcut_style_preset or "",
                                "mixcut_transition_style": mixcut_transition_style,
                                "mixcut_layout_style": mixcut_layout_style,
                                "mixcut_effect_style": mixcut_effect_style,
                                "mixcut_template": mixcut_template,
                                "reused_existing_plan": True,
                            },
                        )
                    return
                self._trace(
                    task_id,
                    "render",
                    "render.retry_reuse_skipped",
                    "已有规划结果不可用，已回退为完整规划流程。",
                    {
                        "reason": "plan_missing_or_invalid",
                    },
                    "WARN",
                )

            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "PLANNING"
                task.progress = 25
                session.commit()
                context_payload = self._load_task_context(task_id)
                transcript_text = self._context_transcript(context_payload)
                transcript_cues = parse_transcript_cues(transcript_text)
                self._trace(
                    task_id,
                    "planning",
                    "planning.started",
                    "开始生成剪辑规划方案。",
                    {
                        "has_transcript": bool(transcript_text),
                        "transcript_cue_count": len(transcript_cues),
                        "creative_prompt_present": bool(task.creative_prompt),
                        "source_asset_count": len(source_asset_ids),
                        "source_file_names": source_file_names,
                        "mixcut_enabled": mixcut_enabled,
                        "mixcut_content_type": mixcut_content_type or "",
                        "mixcut_style_preset": mixcut_style_preset or "",
                        "mixcut_transition_style": mixcut_transition_style,
                        "mixcut_layout_style": mixcut_layout_style,
                        "mixcut_effect_style": mixcut_effect_style,
                        "mixcut_template": mixcut_template,
                        "model_provider": self.settings.model.provider,
                        "primary_model": self.settings.model.model_name,
                        "fallback_model": self.settings.model.fallback_model_name,
                        "vision_model": self.settings.model.vision_model_name,
                        "vision_fallback_model": self.settings.model.vision_fallback_model_name,
                    },
                )

                context = PlannerContext(
                    task=TaskSpec(
                        title=task.title,
                        platform=task.platform,
                        aspectRatio=task.aspect_ratio,
                        minDurationSeconds=task.min_duration_seconds,
                        maxDurationSeconds=task.max_duration_seconds,
                        outputCount=task.output_count,
                        introTemplate=task.intro_template,
                        outroTemplate=task.outro_template,
                        sourceAssetIds=source_asset_ids,
                        sourceFileNames=source_file_names,
                        editingMode=editing_mode,
                        mixcutEnabled=mixcut_enabled,
                        mixcutContentType=mixcut_content_type,
                        mixcutStylePreset=mixcut_style_preset,
                        mixcutTransitionStyle=mixcut_transition_style,
                        mixcutLayoutStyle=mixcut_layout_style,
                        mixcutEffectStyle=mixcut_effect_style,
                        mixcutTemplate=mixcut_template,
                        creativePrompt=task.creative_prompt,
                        transcriptText=transcript_text,
                    ),
                    source=probe,
                    transcriptText=transcript_text,
                    sourcePath=source_path.as_posix(),
                    sourceTimeline=source_timeline,
                    workDir=self.storage.task_work_dir(task_id).as_posix(),
                    trace=lambda stage, event, message, payload=None, level="INFO": self._trace(
                        task_id,
                        stage,
                        event,
                        message,
                        payload,
                        level,
                    ),
                )
                clips = self.planner.plan(context)
                if not clips:
                    raise RuntimeError("planner returned no clips")
                else:
                    clips = self._sanitize_clips(
                        task,
                        probe,
                        clips,
                        transcript_text=transcript_text,
                        source_path=source_path.as_posix(),
                        source_timeline=source_timeline,
                        mixcut_enabled=mixcut_enabled,
                        mixcut_content_type=mixcut_content_type,
                        mixcut_style_preset=mixcut_style_preset,
                    )
                    if not clips:
                        raise RuntimeError("planner produced no valid clips after sanitization")
                task.plan_json = json.dumps([clip.model_dump() for clip in clips], ensure_ascii=False)
                task.progress = 35
                session.commit()
                self._trace(
                    task_id,
                    "planning",
                    "planning.completed",
                    "剪辑规划方案已生成。",
                    {
                        "clip_count": len(clips),
                        "clip_titles": [clip.title for clip in clips[:5]],
                        "dialogue_safe_boundaries": bool(transcript_text and parse_transcript_cues(transcript_text)),
                        "lead_in_seconds": 0.35,
                        "lead_out_seconds": 0.3,
                        "scene_boundary_signal": True,
                        "source_asset_count": len(source_asset_ids),
                        "mixcut_enabled": mixcut_enabled,
                        "mixcut_content_type": mixcut_content_type or "",
                        "mixcut_style_preset": mixcut_style_preset or "",
                        "mixcut_transition_style": mixcut_transition_style,
                        "mixcut_layout_style": mixcut_layout_style,
                        "mixcut_effect_style": mixcut_effect_style,
                        "mixcut_template": mixcut_template,
                    },
                )

            self._render_outputs(
                task_id=task_id,
                source_path=source_path,
                probe=probe,
                clips=clips,
                source_timeline=source_timeline,
                mixcut_transition_style=mixcut_transition_style,
                mixcut_layout_style=mixcut_layout_style,
                mixcut_effect_style=mixcut_effect_style,
                mixcut_template=mixcut_template,
            )

            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "COMPLETED"
                task.progress = 100
                task.finished_at = utcnow()
                session.commit()
                self._trace(
                    task_id,
                    "pipeline",
                    "task.completed",
                    "任务处理完成，所有输出已生成。",
                    {
                        "output_count": len(clips),
                        "source_asset_count": len(source_asset_ids),
                        "mixcut_enabled": mixcut_enabled,
                        "mixcut_content_type": mixcut_content_type or "",
                        "mixcut_style_preset": mixcut_style_preset or "",
                        "mixcut_transition_style": mixcut_transition_style,
                        "mixcut_layout_style": mixcut_layout_style,
                        "mixcut_effect_style": mixcut_effect_style,
                        "mixcut_template": mixcut_template,
                    },
                )
        except Exception as exc:
            self._fail_task(task_id, exc)

    def _claim_task(self, task_id: str) -> bool:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None or task.status not in {"PENDING", "FAILED"}:
                return False
            task.status = "ANALYZING"
            task.progress = max(task.progress or 0, 1)
            task.started_at = task.started_at or utcnow()
            session.commit()
            self._trace(
                task_id,
                "pipeline",
                "task.claimed",
                "任务已被执行器接管，准备开始处理。",
                {
                    "status": task.status,
                },
            )
            return True

    def _fallback_clips(self, task: Task, probe: MediaProbe, transcript_text: str | None = None) -> list[ClipPlan]:
        raise RuntimeError("heuristic fallback is disabled")

    def _load_source_timeline(
        self,
        source_assets: list[SourceAsset],
        source_file_names: list[str],
    ) -> list[dict[str, object]]:
        timeline: list[dict[str, object]] = []
        offset = 0.0
        for index, asset in enumerate(source_assets):
            source_path = self.storage.root / asset.storage_path
            probe = probe_media(source_path)
            file_name = (
                source_file_names[index]
                if index < len(source_file_names) and source_file_names[index].strip()
                else asset.original_file_name
            )
            duration_seconds = max(0.5, float(probe.durationSeconds))
            start_offset = round(offset, 3)
            end_offset = round(offset + duration_seconds, 3)
            timeline.append(
                {
                    "asset_id": asset.id,
                    "file_name": file_name,
                    "source_path": source_path,
                    "probe": probe,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "duration_seconds": duration_seconds,
                    "has_audio": probe.hasAudio,
                }
            )
            offset = end_offset
        return timeline

    def _timeline_segments_for_window(
        self,
        start_seconds: float,
        end_seconds: float,
        source_timeline: list[dict[str, object]],
    ) -> list[ClipSegment]:
        segments: list[ClipSegment] = []
        for entry in source_timeline:
            entry_start = float(entry["start_offset"])
            entry_end = float(entry["end_offset"])
            overlap_start = max(start_seconds, entry_start)
            overlap_end = min(end_seconds, entry_end)
            if overlap_end - overlap_start < 0.18:
                continue
            local_start = max(0.0, overlap_start - entry_start)
            local_end = max(local_start + 0.18, overlap_end - entry_start)
            segments.append(
                ClipSegment(
                    sourceAssetId=str(entry["asset_id"]),
                    sourceFileName=str(entry["file_name"]),
                    startSeconds=round(local_start, 3),
                    endSeconds=round(local_end, 3),
                    durationSeconds=round(local_end - local_start, 3),
                )
            )
        return segments

    def _promote_mixcut_segments(
        self,
        *,
        start_seconds: float,
        end_seconds: float,
        source_timeline: list[dict[str, object]],
    ) -> list[ClipSegment]:
        duration = max(0.8, end_seconds - start_seconds)
        if len(source_timeline) < 2:
            return []

        focus_center = (start_seconds + end_seconds) / 2
        best_boundary_index: int | None = None
        best_boundary_score = float("inf")
        for index in range(len(source_timeline) - 1):
            boundary = float(source_timeline[index]["end_offset"])
            distance = abs(boundary - focus_center)
            if distance < best_boundary_score:
                best_boundary_score = distance
                best_boundary_index = index

        if best_boundary_index is None:
            return []

        promote_threshold = min(4.2, max(1.6, duration * 0.48))
        if best_boundary_score > promote_threshold:
            return []

        left_entry = source_timeline[best_boundary_index]
        right_entry = source_timeline[best_boundary_index + 1]
        left_available = float(left_entry["duration_seconds"])
        right_available = float(right_entry["duration_seconds"])
        left_target = min(left_available, max(0.7, duration * 0.44))
        right_target = min(right_available, max(0.7, duration - left_target))
        remaining = duration - (left_target + right_target)
        if remaining > 0.12:
            extra_left = min(max(0.0, left_available - left_target), remaining * 0.5)
            left_target += extra_left
            right_target += min(max(0.0, right_available - right_target), remaining - extra_left)

        if left_target < 0.45 or right_target < 0.45:
            return []

        promoted = [
            ClipSegment(
                sourceAssetId=str(left_entry["asset_id"]),
                sourceFileName=str(left_entry["file_name"]),
                startSeconds=round(max(0.0, left_available - left_target), 3),
                endSeconds=round(left_available, 3),
                durationSeconds=round(left_target, 3),
            ),
            ClipSegment(
                sourceAssetId=str(right_entry["asset_id"]),
                sourceFileName=str(right_entry["file_name"]),
                startSeconds=0.0,
                endSeconds=round(right_target, 3),
                durationSeconds=round(right_target, 3),
            ),
        ]
        return [segment for segment in promoted if segment.durationSeconds >= 0.45]

    def _resolve_clip_segments(
        self,
        *,
        start_seconds: float,
        end_seconds: float,
        source_timeline: list[dict[str, object]] | None,
        mixcut_enabled: bool,
    ) -> tuple[list[ClipSegment], bool]:
        if not source_timeline:
            return [], False
        natural_segments = self._timeline_segments_for_window(start_seconds, end_seconds, source_timeline)
        if len(natural_segments) >= 2:
            return natural_segments, False
        if mixcut_enabled and len(source_timeline) >= 2:
            promoted = self._promote_mixcut_segments(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                source_timeline=source_timeline,
            )
            if len(promoted) >= 2:
                return promoted, True
        return natural_segments, False

    def _storyboard_video_role(self, index: int, total: int) -> str:
        if total <= 1:
            return "single_focus"
        if index == 0:
            return "scene_open"
        if index == total - 1:
            return "landing_motion"
        return "story_motion"

    def _build_storyboard_segments(
        self,
        *,
        segments: list[ClipSegment],
        mixcut_enabled: bool,
        mixcut_template: str,
        mixcut_style_preset: str | None = None,
        mixcut_content_type: str | None = None,
    ) -> list[ClipSegment]:
        if not segments:
            return []

        normalized_videos: list[ClipSegment] = []
        for index, segment in enumerate(segments):
            normalized_videos.append(
                segment.model_copy(
                    update={
                        "segmentKind": "video",
                        "frameTimestampSeconds": None,
                        "segmentRole": self._storyboard_video_role(index, len(segments)),
                    }
                )
            )

        if not mixcut_enabled or len(normalized_videos) < 2:
            return normalized_videos

        style_preset = self._normalize_mixcut_style_preset(mixcut_style_preset)
        content_type = self._normalize_mixcut_content_type(mixcut_content_type)
        candidate_indexes: list[int] = []
        seen_source_ids: set[str] = set()
        for index, segment in enumerate(normalized_videos):
            if segment.sourceAssetId in seen_source_ids:
                continue
            seen_source_ids.add(segment.sourceAssetId)
            candidate_indexes.append(index)
            if len(candidate_indexes) >= 4:
                break
        if len(candidate_indexes) < 2:
            return normalized_videos

        if len(candidate_indexes) < len(normalized_videos):
            for index in (len(normalized_videos) // 2, len(normalized_videos) - 1):
                if index not in candidate_indexes:
                    candidate_indexes.append(index)

        opening_limit = 3 if style_preset == "music_sync" else 2
        opening_limit = min(opening_limit, len(candidate_indexes))
        opening_indexes = set(candidate_indexes[:opening_limit])
        bridge_indexes = candidate_indexes[opening_limit:]

        frame_segments: list[ClipSegment] = []
        adjusted_videos: list[ClipSegment] = []
        insert_positions = bridge_indexes
        insert_frames: list[ClipSegment] = []
        for index, segment in enumerate(normalized_videos):
            adjusted = segment.model_copy(deep=True)
            if index in opening_indexes or index in insert_positions:
                if index in opening_indexes:
                    hold_floor = 1.0
                    hold_ceiling = 1.4 if style_preset == "music_sync" else 1.9
                    reserved_motion = 0.9
                else:
                    hold_floor = 1.0
                    hold_ceiling = 1.2 if style_preset == "music_sync" else 1.8
                    reserved_motion = 0.8
                max_trim = max(0.0, segment.durationSeconds - reserved_motion)
                if max_trim < hold_floor:
                    adjusted_videos.append(adjusted)
                    continue
                hold_duration = round(clamp(segment.durationSeconds * 0.22, hold_floor, hold_ceiling), 3)
                trim_seconds = round(min(max_trim, hold_duration * 0.9), 3)
                frame_timestamp = round(
                    clamp(
                        segment.startSeconds + max(0.08, trim_seconds * 0.55),
                        segment.startSeconds,
                        max(segment.startSeconds, segment.endSeconds - 0.08),
                    ),
                    3,
                )
                if trim_seconds >= hold_floor:
                    new_start = round(min(segment.endSeconds - 0.6, segment.startSeconds + trim_seconds), 3)
                    adjusted = adjusted.model_copy(
                        update={
                            "startSeconds": new_start,
                            "durationSeconds": round(segment.endSeconds - new_start, 3),
                            "segmentRole": self._storyboard_video_role(index, len(normalized_videos)),
                        }
                    )
                    if adjusted.durationSeconds >= 0.6:
                        frame_segment = ClipSegment(
                            sourceAssetId=segment.sourceAssetId,
                            sourceFileName=segment.sourceFileName,
                            startSeconds=frame_timestamp,
                            endSeconds=frame_timestamp,
                            durationSeconds=hold_duration,
                            segmentKind="frame",
                            frameTimestampSeconds=frame_timestamp,
                            segmentRole="opening_flash" if index in opening_indexes else "flashback_insert",
                        )
                        if index in opening_indexes:
                            frame_segments.append(frame_segment)
                        else:
                            insert_frames.append(frame_segment)
            adjusted_videos.append(adjusted)

        if len(frame_segments) < 1:
            return normalized_videos

        storyboard_segments: list[ClipSegment] = list(frame_segments)
        remaining_inserts = list(insert_frames)
        for index, segment in enumerate(adjusted_videos):
            storyboard_segments.append(segment)
            should_insert_after = (
                remaining_inserts
                and (
                    index == 0
                    or (
                        index < len(adjusted_videos) - 1
                        and style_preset in {"director", "music_sync"}
                    )
                )
            )
            if should_insert_after:
                storyboard_segments.append(remaining_inserts.pop(0))

        storyboard_segments.extend(remaining_inserts)
        return storyboard_segments

    def _segment_counts(self, segments: list[ClipSegment]) -> tuple[int, int]:
        frame_count = sum(1 for segment in segments if segment.segmentKind == "frame")
        return frame_count, max(0, len(segments) - frame_count)

    def _sanitize_clips(
        self,
        task: Task,
        probe: MediaProbe,
        clips: list[ClipPlan],
        transcript_text: str | None = None,
        source_path: str | None = None,
        source_timeline: list[dict[str, object]] | None = None,
        mixcut_enabled: bool = False,
        mixcut_content_type: str | None = None,
        mixcut_style_preset: str | None = None,
    ) -> list[ClipPlan]:
        normalized: list[ClipPlan] = []
        source_duration = max(1.0, probe.durationSeconds)
        minimum = float(task.min_duration_seconds)
        maximum = float(task.max_duration_seconds)
        transcript_cues = parse_transcript_cues(transcript_text)
        editing_mode = "mixcut" if mixcut_enabled else "drama"
        mixcut_content_type = mixcut_content_type if mixcut_enabled else None
        mixcut_style_preset = mixcut_style_preset if mixcut_enabled else None
        mixcut_profile = self._resolve_mixcut_visual_profile(
            editing_mode=editing_mode,
            mixcut_content_type=mixcut_content_type,
            mixcut_style_preset=mixcut_style_preset,
            source_asset_count=max(1, len(source_timeline or [])),
        )
        scene_changes: list[float] = []
        if source_path:
            try:
                scene_changes = [item.timestamp_seconds for item in detect_scene_changes(source_path, probe.durationSeconds, max_changes=18)]
            except Exception:
                scene_changes = []
        lead_in = 0.35
        lead_out = 0.3
        for index, clip in enumerate(clips[: task.output_count], start=1):
            start_seconds = clamp(float(clip.startSeconds), 0.0, max(0.0, source_duration - 0.5))
            requested_end = float(clip.endSeconds)
            if requested_end <= start_seconds:
                requested_end = start_seconds + max(minimum, 1.0)
            end_seconds = clamp(requested_end, start_seconds + 0.5, source_duration)

            if transcript_cues:
                start_seconds, end_seconds = self._snap_clip_to_transcript_boundaries(
                    start_seconds,
                    end_seconds,
                    transcript_cues,
                    minimum=minimum,
                    maximum=maximum,
                    source_duration=source_duration,
                    lead_in=lead_in,
                    lead_out=lead_out,
                )
            else:
                # Keep a little visual runway so clips do not start/end on a harsh mid-action frame.
                start_seconds = max(0.0, start_seconds - lead_in)
                end_seconds = min(source_duration, end_seconds + lead_out)

            if scene_changes:
                start_seconds, end_seconds = self._snap_clip_to_scene_boundaries(
                    start_seconds,
                    end_seconds,
                    scene_changes,
                    source_duration=source_duration,
                    minimum=minimum,
                    maximum=maximum,
                )

            duration_seconds = end_seconds - start_seconds
            if duration_seconds < minimum:
                end_seconds = clamp(start_seconds + minimum, start_seconds + 0.5, source_duration)
                duration_seconds = max(1.0, end_seconds - start_seconds)
            duration_seconds = clamp(duration_seconds, 1.0, maximum)
            end_seconds = min(source_duration, start_seconds + duration_seconds)
            if end_seconds <= start_seconds:
                continue
            segments, promoted_mixcut = self._resolve_clip_segments(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                source_timeline=source_timeline,
                mixcut_enabled=mixcut_enabled,
            )
            segments = self._build_storyboard_segments(
                segments=segments,
                mixcut_enabled=mixcut_enabled,
                mixcut_template=mixcut_profile["mixcut_template"],
                mixcut_style_preset=mixcut_style_preset,
                mixcut_content_type=mixcut_content_type,
            )
            source_asset_id = segments[0].sourceAssetId if len(segments) == 1 else None
            source_file_name = segments[0].sourceFileName if len(segments) == 1 else None
            reason = (clip.reason or "由模型规划生成")[:1000]
            if len(segments) >= 2:
                frame_count, motion_count = self._segment_counts(segments)
                source_names = "、".join(
                    list(dict.fromkeys([segment.sourceFileName for segment in segments if segment.sourceFileName]))[:3]
                )
                reason = f"{reason} 已组织为 {len(segments)} 段分镜"
                if source_names:
                    reason = f"{reason}，涉及 {source_names}。"
                if promoted_mixcut:
                    reason = f"{reason} 已增强为跨素材混剪切法。"
                if frame_count:
                    reason = f"{reason} 开场加入 {frame_count} 张静帧快闪，后续承接 {motion_count} 段运动镜头，强化分镜脚本感。"
            normalized.append(
                ClipPlan(
                    clipIndex=index,
                    title=(clip.title or f"素材 {index}")[:255],
                    reason=reason,
                    startSeconds=round(start_seconds, 3),
                    endSeconds=round(end_seconds, 3),
                    durationSeconds=round(end_seconds - start_seconds, 3),
                    sourceAssetId=source_asset_id,
                    sourceFileName=source_file_name,
                    segments=segments,
                    transitionStyle=mixcut_profile["transition_style"] if mixcut_enabled else "cut",
                    layoutStyle=mixcut_profile["layout_style"] if mixcut_enabled else "single_focus",
                    effectStyle=mixcut_profile["effect_style"] if mixcut_enabled else "none",
                    mixcutTemplate=mixcut_profile["mixcut_template"] if mixcut_enabled else "single_focus_cut",
                )
            )
        return normalized

    def _snap_clip_to_transcript_boundaries(
        self,
        start_seconds: float,
        end_seconds: float,
        transcript_cues,
        *,
        minimum: float,
        maximum: float,
        source_duration: float,
        lead_in: float,
        lead_out: float,
    ) -> tuple[float, float]:
        overlapping = [
            cue
            for cue in transcript_cues
            if cue.endSeconds >= start_seconds - 0.6 and cue.startSeconds <= end_seconds + 0.6
        ]
        if not overlapping:
            return max(0.0, start_seconds - lead_in), min(source_duration, end_seconds + lead_out)

        focus_seconds = (start_seconds + end_seconds) / 2
        target_duration = clamp(end_seconds - start_seconds, minimum, maximum)
        selected_cues = self._select_dialogue_focus_window(
            overlapping,
            focus_seconds=focus_seconds,
            target_duration=target_duration,
            maximum=maximum,
            lead_in=lead_in,
            lead_out=lead_out,
        )
        blocks = build_dialogue_blocks(selected_cues)
        first_block = blocks[0] if blocks else None
        last_block = blocks[-1] if blocks else None
        first_cue = selected_cues[0]
        last_cue = selected_cues[-1]

        # Do not cut through spoken lines. Snap to surrounding cue boundaries and add a small buffer.
        snapped_start = max(0.0, (first_block.startSeconds if first_block else first_cue.startSeconds) - lead_in)
        snapped_end = min(source_duration, (last_block.endSeconds if last_block else last_cue.endSeconds) + lead_out)

        if snapped_end - snapped_start < minimum:
            deficit = minimum - (snapped_end - snapped_start)
            snapped_start = max(0.0, snapped_start - deficit * 0.45)
            snapped_end = min(source_duration, snapped_end + deficit * 0.55)

        if snapped_end - snapped_start > maximum:
            selected_cues = self._trim_dialogue_window_to_maximum(
                selected_cues,
                focus_seconds=focus_seconds,
                maximum=maximum,
                lead_in=lead_in,
                lead_out=lead_out,
            )
            blocks = build_dialogue_blocks(selected_cues)
            first_block = blocks[0] if blocks else None
            last_block = blocks[-1] if blocks else None
            first_cue = selected_cues[0]
            last_cue = selected_cues[-1]
            snapped_start = max(0.0, (first_block.startSeconds if first_block else first_cue.startSeconds) - lead_in)
            snapped_end = min(source_duration, (last_block.endSeconds if last_block else last_cue.endSeconds) + lead_out)

        snapped_start = clamp(snapped_start, 0.0, max(0.0, source_duration - 0.5))
        snapped_end = clamp(snapped_end, snapped_start + 0.5, source_duration)
        return snapped_start, snapped_end

    def _select_dialogue_focus_window(
        self,
        transcript_cues,
        *,
        focus_seconds: float,
        target_duration: float,
        maximum: float,
        lead_in: float,
        lead_out: float,
    ):
        ordered = sorted(transcript_cues, key=lambda cue: (cue.startSeconds, cue.endSeconds))
        best_window = ordered[:1]
        best_score = float("-inf")
        for left_index in range(len(ordered)):
            for right_index in range(left_index, len(ordered)):
                window = ordered[left_index : right_index + 1]
                raw_duration = (window[-1].endSeconds - window[0].startSeconds) + lead_in + lead_out
                if raw_duration > maximum + 0.35:
                    break
                center = (window[0].startSeconds + window[-1].endSeconds) / 2
                focus_distance = abs(center - focus_seconds)
                score = len(window) * 2.4 - focus_distance * 0.8 - abs(raw_duration - target_duration) * 0.2
                if window[0].startSeconds <= focus_seconds <= window[-1].endSeconds:
                    score += 3.0
                if score > best_score:
                    best_score = score
                    best_window = window
        return best_window

    def _trim_dialogue_window_to_maximum(
        self,
        transcript_cues,
        *,
        focus_seconds: float,
        maximum: float,
        lead_in: float,
        lead_out: float,
    ):
        selected = sorted(transcript_cues, key=lambda cue: (cue.startSeconds, cue.endSeconds))
        while len(selected) > 1:
            duration = (selected[-1].endSeconds - selected[0].startSeconds) + lead_in + lead_out
            if duration <= maximum:
                break
            left_center = (selected[0].startSeconds + selected[0].endSeconds) / 2
            right_center = (selected[-1].startSeconds + selected[-1].endSeconds) / 2
            if abs(right_center - focus_seconds) >= abs(left_center - focus_seconds):
                selected = selected[:-1]
            else:
                selected = selected[1:]
        return selected

    def _snap_clip_to_scene_boundaries(
        self,
        start_seconds: float,
        end_seconds: float,
        scene_changes: list[float],
        *,
        source_duration: float,
        minimum: float,
        maximum: float,
    ) -> tuple[float, float]:
        if not scene_changes:
            return start_seconds, end_seconds

        boundary_window = 1.2
        focus_center = (start_seconds + end_seconds) / 2
        original_duration = end_seconds - start_seconds
        start_candidates = [start_seconds]
        end_candidates = [end_seconds]

        nearby_start = [timestamp for timestamp in scene_changes if abs(timestamp - start_seconds) <= boundary_window]
        nearby_end = [timestamp for timestamp in scene_changes if abs(timestamp - end_seconds) <= boundary_window]
        start_candidates.extend(nearby_start)
        end_candidates.extend(nearby_end)

        best_window = (start_seconds, end_seconds)
        best_score = float("-inf")
        for candidate_start in sorted(set(start_candidates)):
            for candidate_end in sorted(set(end_candidates)):
                if candidate_end <= candidate_start:
                    continue
                duration = candidate_end - candidate_start
                if duration < minimum - 0.25 or duration > maximum + 0.25:
                    continue
                center = (candidate_start + candidate_end) / 2
                score = 0.0
                if candidate_start != start_seconds:
                    score += 1.2
                if candidate_end != end_seconds:
                    score += 1.2
                score -= abs(center - focus_center) * 0.7
                score -= abs(duration - original_duration) * 0.25
                if score > best_score:
                    best_score = score
                    best_window = (candidate_start, candidate_end)

        snapped_start, snapped_end = best_window
        if snapped_end - snapped_start < minimum:
            snapped_end = min(source_duration, snapped_start + minimum)
        if snapped_end - snapped_start > maximum:
            snapped_end = min(source_duration, snapped_start + maximum)

        snapped_start = clamp(snapped_start, 0.0, max(0.0, source_duration - 0.5))
        snapped_end = clamp(snapped_end, snapped_start + 0.5, source_duration)
        return snapped_start, snapped_end

    def _render_outputs(
        self,
        task_id: str,
        source_path,
        probe: MediaProbe,
        clips: list[ClipPlan],
        source_timeline: list[dict[str, object]] | None = None,
        mixcut_transition_style: str = "cut",
        mixcut_layout_style: str = "single_focus",
        mixcut_effect_style: str = "none",
        mixcut_template: str = "single_focus_cut",
    ) -> None:
        total = max(1, len(clips))
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is not None:
                task.status = "RENDERING"
                task.progress = 40
                session.commit()
        self._trace(
            task_id,
            "render",
            "render.started",
            "开始执行 FFmpeg 剪辑输出。",
            {
                "clip_count": len(clips),
                "transition_style": mixcut_transition_style,
                "layout_style": mixcut_layout_style,
                "effect_style": mixcut_effect_style,
                "mixcut_template": mixcut_template,
                "template_label": MIXCUT_TEMPLATE_LABELS.get(mixcut_template, mixcut_template),
                "transition_label": MIXCUT_TRANSITION_STYLE_LABELS.get(mixcut_transition_style, mixcut_transition_style),
            },
        )
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                return
            aspect_ratio = task.aspect_ratio
            intro_template = task.intro_template
            outro_template = task.outro_template
        for index, clip in enumerate(clips, start=1):
            output_path = self.storage.task_output_path(task_id, clip.clipIndex)
            self._trace(
                task_id,
                "render",
                "render.clip_started",
                f"开始剪辑第 {clip.clipIndex} 条素材。",
                {
                    "clip_index": clip.clipIndex,
                    "title": clip.title,
                    "start_seconds": clip.startSeconds,
                    "end_seconds": clip.endSeconds,
                    "segment_count": len(clip.segments or []),
                    "frame_segment_count": sum(1 for segment in (clip.segments or []) if segment.segmentKind == "frame"),
                    "motion_segment_count": sum(1 for segment in (clip.segments or []) if segment.segmentKind != "frame"),
                    "transition_style": clip.transitionStyle or mixcut_transition_style,
                    "layout_style": clip.layoutStyle or mixcut_layout_style,
                    "effect_style": clip.effectStyle or mixcut_effect_style,
                    "mixcut_template": clip.mixcutTemplate or mixcut_template,
                    "template_label": MIXCUT_TEMPLATE_LABELS.get(
                        clip.mixcutTemplate or mixcut_template,
                        clip.mixcutTemplate or mixcut_template,
                    ),
                    "output_path": output_path.as_posix(),
                },
            )
            try:
                if source_timeline and clip.segments:
                    timeline_by_asset = {
                        str(entry["asset_id"]): entry
                        for entry in source_timeline
                    }
                    if len(clip.segments) >= 2:
                        render_segments: list[RenderSegmentSpec] = []
                        for segment in clip.segments:
                            entry = timeline_by_asset.get(segment.sourceAssetId)
                            if entry is None:
                                continue
                            render_segments.append(
                                RenderSegmentSpec(
                                    source_path=Path(str(entry["source_path"])),
                                    start_seconds=segment.startSeconds,
                                    end_seconds=segment.endSeconds,
                                    has_audio=bool(entry["has_audio"]),
                                    segment_kind=(segment.segmentKind or "video"),
                                    frame_timestamp_seconds=segment.frameTimestampSeconds,
                                    hold_seconds=segment.durationSeconds if segment.segmentKind == "frame" else None,
                                )
                            )
                        if len(render_segments) >= 2:
                            render_output_segments(
                                segments=render_segments,
                                output_path=output_path,
                                aspect_ratio=aspect_ratio,
                                intro_template=intro_template,
                                outro_template=outro_template,
                                transition_style=clip.transitionStyle or mixcut_transition_style,
                            )
                        else:
                            render_output(
                                source_path=source_path,
                                output_path=output_path,
                                start_seconds=clip.startSeconds,
                                end_seconds=clip.endSeconds,
                                aspect_ratio=aspect_ratio,
                                intro_template=intro_template,
                                outro_template=outro_template,
                                has_audio=probe.hasAudio,
                            )
                    else:
                        segment = clip.segments[0]
                        entry = timeline_by_asset.get(segment.sourceAssetId)
                        if entry is None:
                            render_output(
                                source_path=source_path,
                                output_path=output_path,
                                start_seconds=clip.startSeconds,
                                end_seconds=clip.endSeconds,
                                aspect_ratio=aspect_ratio,
                                intro_template=intro_template,
                                outro_template=outro_template,
                                has_audio=probe.hasAudio,
                            )
                        else:
                            render_output(
                                source_path=Path(str(entry["source_path"])),
                                output_path=output_path,
                                start_seconds=segment.startSeconds,
                                end_seconds=segment.endSeconds,
                                aspect_ratio=aspect_ratio,
                                intro_template=intro_template,
                                outro_template=outro_template,
                                has_audio=bool(entry["has_audio"]),
                            )
                else:
                    render_output(
                        source_path=source_path,
                        output_path=output_path,
                        start_seconds=clip.startSeconds,
                        end_seconds=clip.endSeconds,
                        aspect_ratio=aspect_ratio,
                        intro_template=intro_template,
                        outro_template=outro_template,
                        has_audio=probe.hasAudio,
                    )
            except Exception as exc:
                self._trace(
                    task_id,
                    "render",
                    "render.clip_failed",
                    f"第 {clip.clipIndex} 条 FFmpeg 剪辑失败。",
                    {
                        "clip_index": clip.clipIndex,
                        "title": clip.title,
                        "start_seconds": clip.startSeconds,
                        "end_seconds": clip.endSeconds,
                        "segments": [segment.model_dump() for segment in clip.segments],
                        "transition_style": clip.transitionStyle or mixcut_transition_style,
                        "layout_style": clip.layoutStyle or mixcut_layout_style,
                        "effect_style": clip.effectStyle or mixcut_effect_style,
                        "mixcut_template": clip.mixcutTemplate or mixcut_template,
                        "output_path": output_path.as_posix(),
                        "error": str(exc),
                    },
                    "ERROR",
                )
                raise
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    continue
                session.add(
                    TaskOutput(
                        id=new_id("output"),
                        task_id=task_id,
                        clip_index=clip.clipIndex,
                        title=clip.title,
                        reason=clip.reason,
                        start_seconds=clip.startSeconds,
                        end_seconds=clip.endSeconds,
                        duration_seconds=round(
                            sum(_timeline_segment_duration(segment) for segment in clip.segments),
                            3,
                        )
                        if clip.segments
                        else clip.durationSeconds,
                        preview_path=output_path.relative_to(self.storage.root).as_posix(),
                        download_path=output_path.relative_to(self.storage.root).as_posix(),
                    )
                )
                task.progress = min(95, 35 + int(60 * (index / total)))
                session.commit()
            self._trace(
                task_id,
                "render",
                "render.clip_completed",
                f"第 {clip.clipIndex} 条素材剪辑完成。",
                {
                    "clip_index": clip.clipIndex,
                    "title": clip.title,
                    "output_path": output_path.as_posix(),
                    "segment_count": len(clip.segments or []),
                    "segment_sources": list(
                        dict.fromkeys([segment.sourceFileName for segment in clip.segments if segment.sourceFileName])
                    )[:5],
                    "transition_style": mixcut_transition_style,
                    "progress": min(95, 35 + int(60 * (index / total))),
                },
            )

    def _delete_outputs(self, session: Session, task: Task) -> None:
        self.storage.remove_output_bundle(task.id)
        session.execute(delete(TaskOutput).where(TaskOutput.task_id == task.id))
        session.flush()

    def _task_to_list_item(self, task: Task) -> TaskListItem:
        context_payload = self._load_task_context(task.id)
        transcript_text = self._context_transcript(context_payload)
        source_asset_ids = self._context_source_asset_ids(context_payload) or [task.source_asset_id]
        return TaskListItem(
            id=task.id,
            title=task.title,
            status=task.status,
            platform=task.platform,
            progress=task.progress,
            outputCount=task.output_count,
            createdAt=_iso(task.created_at),
            updatedAt=_iso(task.updated_at),
            sourceFileName=task.source_file_name,
            aspectRatio=task.aspect_ratio,
            minDurationSeconds=task.min_duration_seconds,
            maxDurationSeconds=task.max_duration_seconds,
            retryCount=task.retry_count or 0,
            startedAt=_optional_iso(task.started_at),
            finishedAt=_optional_iso(task.finished_at),
            completedOutputCount=len(task.outputs),
            hasTranscript=bool(transcript_text),
            hasTimedTranscript=bool(parse_transcript_cues(transcript_text)),
            sourceAssetCount=len(source_asset_ids),
            editingMode=self._context_editing_mode(context_payload),
            mixcutEnabled=self._context_mixcut_enabled(context_payload),
        )

    def _source_asset_summary(self, asset: SourceAsset | None) -> SourceAssetSummary | None:
        if asset is None:
            return None
        return SourceAssetSummary(
            assetId=asset.id,
            originalFileName=asset.original_file_name,
            storedFileName=asset.stored_file_name,
            fileUrl=self.storage.build_public_url(asset.storage_path),
            mimeType=asset.mime_type,
            sizeBytes=asset.size_bytes,
            sha256=asset.sha256,
            durationSeconds=asset.duration_seconds,
            width=asset.width,
            height=asset.height,
            hasAudio=asset.has_audio,
            createdAt=_iso(asset.created_at),
            updatedAt=_iso(asset.updated_at),
        )

    def _load_source_asset_summaries(self, source_asset_ids: list[str]) -> list[SourceAssetSummary]:
        if not source_asset_ids:
            return []
        with self.session() as session:
            assets = [
                session.get(SourceAsset, source_asset_id)
                for source_asset_id in list(dict.fromkeys(source_asset_ids))
            ]
        return [summary for summary in (self._source_asset_summary(asset) for asset in assets) if summary is not None]

    def _parse_plan(self, task: Task) -> list[ClipPlan]:
        if not task.plan_json:
            return []
        try:
            raw = json.loads(task.plan_json)
        except Exception:
            return []
        if not isinstance(raw, list):
            return []

        plan: list[ClipPlan] = []
        for item in raw:
            try:
                plan.append(ClipPlan.model_validate(item))
            except Exception:
                continue
        return plan

    def _load_task_context(self, task_id: str) -> dict[str, object]:
        return self.storage.load_task_context(task_id)

    def _context_source_asset_ids(self, payload: dict[str, object]) -> list[str]:
        raw = payload.get("sourceAssetIds")
        if not isinstance(raw, list):
            return []
        values = [str(item).strip() for item in raw if str(item).strip()]
        return list(dict.fromkeys(values))

    def _context_source_file_names(self, payload: dict[str, object]) -> list[str]:
        raw = payload.get("sourceFileNames")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    def _context_editing_mode(self, payload: dict[str, object]) -> str:
        raw = payload.get("editingMode")
        if isinstance(raw, str) and raw.strip():
            return self._normalize_editing_mode(raw)
        return "mixcut" if bool(payload.get("mixcutEnabled")) else "drama"

    def _context_mixcut_enabled(self, payload: dict[str, object]) -> bool:
        return self._context_editing_mode(payload) == "mixcut"

    def _context_mixcut_content_type(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("mixcutContentType")
        if isinstance(raw, str) and raw.strip():
            return self._normalize_mixcut_content_type(raw)
        return None

    def _context_mixcut_style_preset(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("mixcutStylePreset")
        if isinstance(raw, str) and raw.strip():
            return self._normalize_mixcut_style_preset(raw)
        return None

    def _context_mixcut_transition_style(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("mixcutTransitionStyle")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _context_mixcut_layout_style(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("mixcutLayoutStyle")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _context_mixcut_effect_style(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("mixcutEffectStyle")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _context_mixcut_template(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("mixcutTemplate")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _context_render_only_retry(self, payload: dict[str, object]) -> bool:
        return bool(payload.get("renderOnlyRetry"))

    def _can_retry_render_only(self, task: Task) -> bool:
        if task.status != "FAILED":
            return False
        if not task.plan_json:
            return False
        return (task.progress or 0) >= 40

    def _resolve_mixcut_transition_style(self, payload: dict[str, object]) -> str:
        transition_style = self._context_mixcut_transition_style(payload)
        if transition_style:
            return transition_style
        if self._context_editing_mode(payload) != "mixcut":
            return "cut"
        style = (self._context_mixcut_style_preset(payload) or "").strip()
        if style == "music_sync":
            return "flash"
        return "crossfade"

    def _trace(
        self,
        task_id: str,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, object] | None = None,
        level: str = "INFO",
    ) -> None:
        writer = TaskTraceWriter(task_id=task_id, trace_path=self.storage.task_trace_path(task_id))
        writer.log(stage=stage, event=event, message=message, payload=payload, level=level)

    def _fail_task(self, task_id: str, exc: Exception, *, message: str = "任务处理失败。") -> None:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is not None:
                task.status = "FAILED"
                task.progress = min(99, task.progress or 0)
                task.error_message = truncate_text(str(exc), 1000)
                task.finished_at = utcnow()
                session.commit()
        self._trace(
            task_id,
            "pipeline",
            "task.failed",
            message,
            {
                "error": str(exc),
            },
            "ERROR",
        )

    def _save_task_context(
        self,
        task_id: str,
        *,
        transcript_text: str | None = None,
        source_asset_ids: list[str] | None = None,
        source_file_names: list[str] | None = None,
        editing_mode: str | None = None,
        mixcut_enabled: bool | None = None,
        mixcut_content_type: str | None = None,
        mixcut_style_preset: str | None = None,
        mixcut_transition_style: str | None = None,
        mixcut_layout_style: str | None = None,
        mixcut_effect_style: str | None = None,
        mixcut_template: str | None = None,
        render_only_retry: bool | None = None,
    ) -> None:
        context = self._load_task_context(task_id)
        normalized_transcript = (transcript_text or "").strip()
        if normalized_transcript:
            context["transcriptText"] = normalized_transcript
        if source_asset_ids:
            context["sourceAssetIds"] = list(dict.fromkeys([item for item in source_asset_ids if item]))
        if source_file_names:
            context["sourceFileNames"] = [item for item in source_file_names if item]
        if editing_mode is not None:
            context["editingMode"] = self._normalize_editing_mode(editing_mode, mixcut_enabled)
        if mixcut_enabled is not None:
            context["mixcutEnabled"] = bool(mixcut_enabled)
        if mixcut_content_type is not None:
            context["mixcutContentType"] = mixcut_content_type.strip()
        if mixcut_style_preset is not None:
            context["mixcutStylePreset"] = mixcut_style_preset.strip()
        if mixcut_transition_style is not None:
            context["mixcutTransitionStyle"] = mixcut_transition_style.strip()
        if mixcut_layout_style is not None:
            context["mixcutLayoutStyle"] = mixcut_layout_style.strip()
        if mixcut_effect_style is not None:
            context["mixcutEffectStyle"] = mixcut_effect_style.strip()
        if mixcut_template is not None:
            context["mixcutTemplate"] = mixcut_template.strip()
        if render_only_retry is not None:
            if render_only_retry:
                context["renderOnlyRetry"] = True
            else:
                context.pop("renderOnlyRetry", None)
        self.storage.save_task_context(task_id, context)

    def _context_transcript(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("transcriptText")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _transcript_preview(self, transcript_text: str | None, limit: int = 220) -> str | None:
        if not transcript_text:
            return None
        normalized = " ".join(line.strip() for line in transcript_text.splitlines() if line.strip())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    def _task_to_draft(self, task: Task, asset: SourceAsset | None) -> TaskDraft:
        title = task.title.strip()
        if title and not title.endswith("复制版"):
            title = f"{title} 复制版"
        context_payload = self._load_task_context(task.id)
        transcript_text = self._context_transcript(context_payload)
        transcript_cues = parse_transcript_cues(transcript_text)
        source_asset_ids = self._context_source_asset_ids(context_payload) or [task.source_asset_id]
        source_file_names = self._context_source_file_names(context_payload) or [task.source_file_name]
        source_assets = self._load_source_asset_summaries(source_asset_ids)
        return TaskDraft(
            sourceTaskId=task.id,
            sourceAssetId=task.source_asset_id,
            sourceAssetIds=source_asset_ids,
            sourceFileName=task.source_file_name,
            sourceFileNames=source_file_names,
            sourceAssetCount=len(source_asset_ids),
            editingMode=self._context_editing_mode(context_payload),
            mixcutEnabled=self._context_mixcut_enabled(context_payload),
            mixcutContentType=self._context_mixcut_content_type(context_payload),
            mixcutStylePreset=self._context_mixcut_style_preset(context_payload),
            mixcutTransitionStyle=self._context_mixcut_transition_style(context_payload),
            mixcutLayoutStyle=self._context_mixcut_layout_style(context_payload),
            mixcutEffectStyle=self._context_mixcut_effect_style(context_payload),
            mixcutTemplate=self._context_mixcut_template(context_payload),
            title=title or task.title,
            platform=task.platform,
            aspectRatio=task.aspect_ratio,
            minDurationSeconds=task.min_duration_seconds,
            maxDurationSeconds=task.max_duration_seconds,
            outputCount=task.output_count,
            introTemplate=task.intro_template,
            outroTemplate=task.outro_template,
            creativePrompt=task.creative_prompt,
            transcriptText=transcript_text,
            hasTimedTranscript=bool(transcript_cues),
            transcriptCueCount=len(transcript_cues),
            source=self._source_asset_summary(asset),
            sourceAssets=source_assets or ([self._source_asset_summary(asset)] if asset is not None else []),
        )

    def _task_to_detail(self, task: Task) -> TaskDetail:
        outputs: list[TaskOutputSchema] = []
        for output in sorted(task.outputs, key=lambda item: item.clip_index):
            relative = output.preview_path
            outputs.append(
                TaskOutputSchema(
                    id=output.id,
                    clipIndex=output.clip_index,
                    title=output.title,
                    reason=output.reason,
                    startSeconds=output.start_seconds,
                    endSeconds=output.end_seconds,
                    durationSeconds=output.duration_seconds,
                    previewUrl=self.storage.build_public_url(relative),
                    downloadUrl=self.storage.build_public_url(output.download_path),
                )
            )
        source_asset = task.source_asset if hasattr(task, "source_asset") else None
        plan = self._parse_plan(task)
        context_payload = self._load_task_context(task.id)
        transcript_text = self._context_transcript(context_payload)
        transcript_cues = parse_transcript_cues(transcript_text)
        source_asset_ids = self._context_source_asset_ids(context_payload) or [task.source_asset_id]
        source_file_names = self._context_source_file_names(context_payload) or [task.source_file_name]
        source_assets = self._load_source_asset_summaries(source_asset_ids)
        return TaskDetail(
            id=task.id,
            title=task.title,
            status=task.status,
            platform=task.platform,
            progress=task.progress,
            outputCount=task.output_count,
            createdAt=_iso(task.created_at),
            updatedAt=_iso(task.updated_at),
            sourceFileName=task.source_file_name,
            aspectRatio=task.aspect_ratio,
            minDurationSeconds=task.min_duration_seconds,
            maxDurationSeconds=task.max_duration_seconds,
            introTemplate=task.intro_template,
            outroTemplate=task.outro_template,
            creativePrompt=task.creative_prompt,
            errorMessage=task.error_message,
            startedAt=_optional_iso(task.started_at),
            finishedAt=_optional_iso(task.finished_at),
            retryCount=task.retry_count or 0,
            completedOutputCount=len(outputs),
            transcriptPreview=self._transcript_preview(transcript_text),
            hasTranscript=bool(transcript_text),
            hasTimedTranscript=bool(transcript_cues),
            transcriptCueCount=len(transcript_cues),
            source=self._source_asset_summary(source_asset),
            sourceAssets=source_assets or ([self._source_asset_summary(source_asset)] if source_asset is not None else []),
            sourceAssetIds=source_asset_ids,
            sourceFileNames=source_file_names,
            sourceAssetCount=len(source_asset_ids),
            editingMode=self._context_editing_mode(context_payload),
            mixcutEnabled=self._context_mixcut_enabled(context_payload),
            mixcutContentType=self._context_mixcut_content_type(context_payload),
            mixcutStylePreset=self._context_mixcut_style_preset(context_payload),
            mixcutTransitionStyle=self._context_mixcut_transition_style(context_payload),
            mixcutLayoutStyle=self._context_mixcut_layout_style(context_payload),
            mixcutEffectStyle=self._context_mixcut_effect_style(context_payload),
            mixcutTemplate=self._context_mixcut_template(context_payload),
            plan=plan,
            outputs=outputs,
        )
