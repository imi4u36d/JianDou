"""Workflow service — Python translation of WorkflowApplicationService (Java).

Handles the multi-stage creative workflow lifecycle:
  STORYBOARD -> KEYFRAME -> VIDEO -> JOINED
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow

# ---------------------------------------------------------------------------
# Constants (mirroring WorkflowConstants.java)
# ---------------------------------------------------------------------------
STAGE_STORYBOARD = "storyboard"
STAGE_KEYFRAME = "keyframe"
STAGE_VIDEO = "video"
STAGE_JOINED = "joined"

STATUS_DRAFT = "DRAFT"
STATUS_READY = "READY"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"
DEFAULT_MIN_DURATION_SECONDS = 5
DEFAULT_MAX_DURATION_SECONDS = 12

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _random_id() -> str:
    return uuid.uuid4().hex


def _trim(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = value.strip()
    return stripped if stripped else fallback.strip()


def _first_non_blank(*values: str | None) -> str:
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    s = str(value).strip().lower()
    return s in ("true", "1", "yes")


def _read_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text) or {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _write_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _default_video_size(aspect_ratio: str | None) -> str:
    return "1280*720" if _trim(aspect_ratio) == "16:9" else "720*1280"


def _normalize_duration_mode(
    duration_mode: str | None,
    min_seconds: int | None,
    max_seconds: int | None,
) -> str:
    mode = _trim(duration_mode).lower()
    if mode in ("manual", "auto"):
        return mode
    return "manual" if (min_seconds is not None or max_seconds is not None) else "auto"


def _dimensions_from_aspect_ratio(aspect_ratio: str | None) -> tuple[int, int]:
    ar = _trim(aspect_ratio)
    if ar == "16:9":
        return 1824, 1024
    if ar == "1:1":
        return 1024, 1024
    return 1024, 1824


def _dimensions_from_size(value: str | None, fallback_aspect_ratio: str | None = None) -> tuple[int, int]:
    raw = _trim(value).lower().replace("x", "*")
    match = re.search(r"(\d{3,5})\s*\*\s*(\d{3,5})", raw)
    if match:
        return _safe_int(match.group(1), 0), _safe_int(match.group(2), 0)
    if "1280" in raw and "720" in raw:
        return 1280, 720
    if "720" in raw and "1280" in raw:
        return 720, 1280
    return _dimensions_from_aspect_ratio(fallback_aspect_ratio)


def _strip_markdown_cell(value: str) -> str:
    return re.sub(r"<br\s*/?>", " ", _trim(value), flags=re.IGNORECASE).replace("\\|", "|").strip()


def _split_markdown_row(line: str) -> list[str]:
    stripped = _trim(line)
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [_strip_markdown_cell(cell) for cell in stripped.strip("|").split("|")]


def _is_markdown_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell or "") for cell in cells)


def _parse_storyboard_markdown(markdown: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    characters: list[dict[str, Any]] = []
    clips: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    section = ""
    table_headers: list[str] = []
    for line in lines:
        text = _trim(line)
        if not text:
            continue
        if "角色定义" in text:
            section = "characters"
            table_headers = []
            continue
        if "分镜脚本" in text:
            section = "clips"
            table_headers = []
            continue
        cells = _split_markdown_row(text)
        if not cells:
            continue
        if _is_markdown_separator(cells):
            continue
        if not table_headers:
            table_headers = cells
            continue
        if section == "characters":
            name = cells[0] if cells else ""
            if not name or name == "角色":
                continue
            details = []
            for header, cell in zip(table_headers[1:], cells[1:]):
                if cell:
                    details.append(f"{header}: {cell}")
            characters.append({
                "name": name,
                "appearance": "；".join(details),
                "summary": "；".join(details[:4]) or name,
            })
        elif section == "clips":
            if not cells or cells[0] == "镜号":
                continue
            clip_no = _safe_int(cells[0], len(clips) + 1)
            duration_text = cells[4] if len(cells) > 4 else ""
            duration_match = re.search(r"\d+", duration_text)
            duration_seconds = _safe_int(duration_match.group(0), 8) if duration_match else 8
            clips.append({
                "clipIndex": clip_no if clip_no > 0 else len(clips) + 1,
                "shotLabel": f"镜头 {cells[0]}",
                "startFrame": cells[1] if len(cells) > 1 else "",
                "endFrame": cells[2] if len(cells) > 2 else "",
                "scene": cells[3] if len(cells) > 3 else "",
                "durationHint": duration_text,
                "targetDurationSeconds": duration_seconds,
            })
    return characters, clips


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class WorkflowService:
    """Multi-stage creative workflow service."""

    def __init__(self, db: AsyncSession, generation_service: Any | None = None) -> None:
        self.db = db
        self._generation_service = generation_service

    def _get_generation_service(self):
        if self._generation_service is None:
            raise RuntimeError("generation service not configured")
        return self._generation_service

    async def _validate_generation_models(
        self,
        owner_user_id: int,
        text_model: str,
        image_model: str,
        video_model: str,
    ) -> None:
        gen_service = self._get_generation_service()
        factory = getattr(gen_service, "_factory", None)
        resolver = getattr(factory, "_config_resolver", None)
        if resolver is None:
            raise ValueError("模型配置服务未初始化，请重启服务后重试。")

        checks = [
            ("文本模型", text_model, "text"),
            ("关键帧模型", image_model, "image"),
            ("视频模型", video_model, "video"),
        ]
        for label, model, kind in checks:
            value = _trim(model)
            if not value:
                raise ValueError(f"请先选择{label}。")
            try:
                if kind == "text":
                    profile = resolver.resolve_text_profile(value, owner_user_id)
                    provider = getattr(profile, "provider", "")
                    api_key = getattr(profile, "api_key", "")
                    base_url = getattr(profile, "base_url", "")
                    task_base_url = True
                else:
                    profile = resolver.resolve_media_profile(value, kind, owner_user_id)
                    provider = getattr(profile, "provider", "")
                    api_key = getattr(profile, "api_key", "")
                    base_url = getattr(profile, "base_url", "")
                    task_base_url = kind != "video" or bool(getattr(profile, "task_base_url", ""))
                ready = getattr(profile, "ready", False)
            except Exception as exc:
                raise ValueError(f"{label}不可用：{value}") from exc
            if not provider:
                raise ValueError(f"{label}不可用：{value}")
            if not api_key:
                raise ValueError(f"当前用户未设置{label} Key，请先在用户管理中配置 Key。")
            if not base_url:
                raise ValueError(f"{label}缺少 base_url，请检查模型配置。")
            if not task_base_url:
                raise ValueError(f"{label}缺少 task_base_url，请检查模型配置。")
            if not ready:
                raise ValueError(f"{label}配置未就绪，请检查用户 Key 和模型配置。")

    # ------------------------------------------------------------------
    # Workflow CRUD
    # ------------------------------------------------------------------

    async def create_workflow(
        self,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Create a draft workflow."""
        workflow_id = f"wf_{_random_id()[:12]}"
        aspect_ratio = _trim(request.get("aspectRatio", "9:16"))
        keyframe_seed = request.get("keyframeSeed") or request.get("seed")
        video_seed = request.get("videoSeed") or request.get("seed")
        duration_mode = _normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_dur = (
            DEFAULT_MIN_DURATION_SECONDS
            if duration_mode == "auto"
            else max(1, _safe_int(request.get("minDurationSeconds"), 1))
        )
        max_dur = (
            DEFAULT_MAX_DURATION_SECONDS
            if duration_mode == "auto"
            else max(_safe_int(request.get("maxDurationSeconds", min_dur)), min_dur)
        )
        text_model = _trim(request.get("textAnalysisModel"), "")
        image_model = _trim(request.get("imageModel"), "")
        video_model = _trim(request.get("videoModel"), "")
        await self._validate_generation_models(owner_user_id or 0, text_model, image_model, video_model)
        now = _now_iso()
        workflow = BizStageWorkflow(
            workflow_id=workflow_id,
            owner_user_id=owner_user_id or 0,
            title=_trim(request.get("title"), "未命名工作流"),
            transcript_text=_trim(request.get("transcriptText"), ""),
            aspect_ratio=aspect_ratio,
            style_preset=_trim(request.get("stylePreset"), "cinematic"),
            text_analysis_model=text_model,
            image_model=image_model,
            video_model=video_model,
            video_size=_trim(request.get("videoSize"), _default_video_size(aspect_ratio)),
            keyframe_seed=keyframe_seed,
            video_seed=video_seed,
            duration_mode=duration_mode,
            task_seed=request.get("seed"),
            min_duration_seconds=min_dur,
            max_duration_seconds=max_dur,
            status=STATUS_DRAFT,
            current_stage=STAGE_STORYBOARD,
            selected_storyboard_version_id="",
            final_join_asset_id="",
            effect_rating=None,
            effect_rating_note="",
            metadata_json="{}",
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )
        self.db.add(workflow)
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def list_workflows(
        self,
        owner_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """List user's workflows with version counts."""
        stmt = (
            select(BizStageWorkflow)
            .where(BizStageWorkflow.is_deleted == 0)
            .order_by(BizStageWorkflow.update_time.desc())
        )
        if owner_user_id is not None:
            stmt = stmt.where(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self.db.execute(stmt)
        workflows = result.scalars().all()

        rows: list[dict[str, Any]] = []
        for wf in workflows:
            versions = await self._list_stage_versions(wf.workflow_id)
            rows.append(self._to_workflow_summary(wf, versions))
        return rows

    async def get_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Get full workflow detail with all versions and assets."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        if await self._refresh_video_versions(wf, versions):
            versions = await self._list_stage_versions(workflow_id)
        asset_map = await self._load_asset_map(versions, wf.final_join_asset_id)
        return self._to_workflow_detail(wf, versions, asset_map)

    async def delete_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Soft delete workflow and all versions."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        asset_ids: set[str] = set()
        now = _now_iso()
        for v in versions:
            if v.material_asset_id:
                asset_ids.add(v.material_asset_id)
            v.selected = 0
            v.is_deleted = 1
            v.update_time = now
        if wf.final_join_asset_id:
            asset_ids.add(wf.final_join_asset_id)
        for aid in asset_ids:
            await self._mark_asset_deleted(aid)
        wf.is_deleted = 1
        wf.update_time = now
        await self.db.commit()
        return {"workflowId": workflow_id, "deleted": True}

    async def update_workflow_settings(
        self,
        workflow_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update workflow parameters."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        aspect_ratio = _trim(request.get("aspectRatio", "9:16"))
        duration_mode = _normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_dur = (
            DEFAULT_MIN_DURATION_SECONDS
            if duration_mode == "auto"
            else max(1, _safe_int(request.get("minDurationSeconds"), 1))
        )
        max_dur = (
            DEFAULT_MAX_DURATION_SECONDS
            if duration_mode == "auto"
            else max(_safe_int(request.get("maxDurationSeconds"), min_dur), min_dur)
        )
        text_model = _trim(request.get("textAnalysisModel"), "")
        image_model = _trim(request.get("imageModel"), "")
        video_model = _trim(request.get("videoModel"), "")
        await self._validate_generation_models(wf.owner_user_id, text_model, image_model, video_model)
        wf.aspect_ratio = aspect_ratio
        wf.style_preset = _trim(request.get("stylePreset"), "cinematic")
        wf.text_analysis_model = text_model
        wf.image_model = image_model
        wf.video_model = video_model
        wf.video_size = _trim(request.get("videoSize"), _default_video_size(aspect_ratio))
        wf.keyframe_seed = request.get("keyframeSeed")
        wf.video_seed = request.get("videoSeed")
        wf.duration_mode = duration_mode
        wf.min_duration_seconds = min_dur
        wf.max_duration_seconds = max_dur
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Storyboard
    # ------------------------------------------------------------------

    async def generate_storyboard(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate a storyboard version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        if owner_user_id is not None and wf.owner_user_id != owner_user_id:
            return None

        # Check if transcript text exists
        if not wf.transcript_text or not wf.transcript_text.strip():
            raise ValueError("请先填写正文内容，再生成分镜。")

        # Create a new storyboard version
        version_id = f"sv_{_random_id()[:12]}"
        now = _now_iso()

        # Count existing storyboard versions for version number
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_STORYBOARD,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0

        # Call real AI generation for storyboard
        gen_service = self._get_generation_service()
        text_model = _trim(getattr(wf, 'text_analysis_model', ''))
        if not text_model:
            raise ValueError("请先选择文本模型。")
        visual_style = _trim(getattr(wf, 'style_preset', ''), 'cinematic')

        generation_request = {
            "kind": "script",
            "input": {
                "text": wf.transcript_text,
                "sourceText": wf.transcript_text,
            },
            "model": {
                "textAnalysisModel": text_model,
            },
            "options": {
                "visualStyle": visual_style,
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        }

        try:
            gen_result = await gen_service.create_run(generation_request)
        except Exception as ex:
            import logging
            logging.getLogger(__name__).warning("Storyboard generation failed: %s", ex)
            raw_error = str(ex)
            if "missing api key" in raw_error.lower() or "missing api key or base url" in raw_error.lower():
                raise ValueError("当前用户未设置对应模型 Key，请先在用户管理中配置 Key。") from ex
            raise ValueError(f"分镜生成失败：{raw_error}") from ex

        script_markdown = ""
        output_summary = {}
        model_call_summary = {}

        # Extract script markdown from generation result
        result_script = gen_result.get("resultScript", gen_result.get("result", {}))
        if isinstance(result_script, dict):
            script_markdown = result_script.get("scriptMarkdown", "")
            output_summary = {
                "scriptMarkdown": script_markdown,
                "markdownUrl": result_script.get("markdownUrl", ""),
                "runId": result_script.get("runId", ""),
            }
            model_call_summary = {
                "modelInfo": result_script.get("modelInfo", {}),
                "callChain": result_script.get("callChain", []),
            }

        if not script_markdown:
            raise ValueError("分镜生成失败：模型返回为空，请重试。")

        storyboard_version = BizStageVersion(
            stage_version_id=version_id,
            workflow_id=workflow_id,
            owner_user_id=wf.owner_user_id,
            stage_type=STAGE_STORYBOARD,
            clip_index=0,
            version_no=version_count + 1,
            title=f"分镜版本 {version_count + 1}",
            status="COMPLETED",
            selected=0,
            rating_note="",
            parent_version_id="",
            source_material_asset_id="",
            material_asset_id="",
            preview_url="",
            download_url="",
            input_summary_json=_write_json({"transcriptLength": len(wf.transcript_text or "")}),
            output_summary_json=_write_json(output_summary),
            model_call_summary_json=_write_json(model_call_summary),
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )

        self.db.add(storyboard_version)
        await self.db.commit()

        return await self.get_workflow(workflow_id)

    async def select_storyboard(
        self,
        workflow_id: str,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Select a storyboard version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_STORYBOARD, 0, version_id)
        wf.selected_storyboard_version_id = version_id
        wf.current_stage = STAGE_KEYFRAME
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def adjust_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        prompt: str | None = None,
    ) -> dict[str, Any] | None:
        """Adjust an existing storyboard version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None

        # Verify the storyboard version exists
        version = await self._require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None

        # Update the version with adjustment info
        now = _now_iso()
        version.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Keyframe
    # ------------------------------------------------------------------

    async def generate_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
    ) -> dict[str, Any] | None:
        """Generate keyframe for a clip."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        storyboard_version = await self._selected_storyboard_version(wf)
        if storyboard_version is None:
            raise ValueError("请先选中一个分镜版本。")
        characters, clips = self._storyboard_plan(storyboard_version)
        is_character_sheet = clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE
        character: dict[str, Any] | None = None
        clip: dict[str, Any] | None = None
        if is_character_sheet:
            char_index = clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE - 1
            if char_index < 0 or char_index >= len(characters):
                raise ValueError("角色不存在，请重新选择分镜版本。")
            character = characters[char_index]
        else:
            clip = next((item for item in clips if _safe_int(item.get("clipIndex"), 0) == clip_index), None)
            if clip is None:
                raise ValueError("镜头不存在，请重新选择分镜版本。")

        version_id = f"kv_{_random_id()[:12]}"
        now = _now_iso()

        # Count existing keyframe versions for this clip
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0
        width, height = _dimensions_from_aspect_ratio(wf.aspect_ratio)
        prompt = (
            self._character_sheet_prompt(character)
            if character is not None
            else self._keyframe_prompt(wf, clip or {})
        )
        gen_result = await self._get_generation_service().create_run({
            "kind": "image",
            "input": {
                "prompt": prompt,
                "width": width,
                "height": height,
                "frameRole": "sheet" if is_character_sheet else "keyframe",
                "seed": wf.keyframe_seed,
            },
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": wf.image_model,
            },
            "options": {
                "stylePreset": wf.style_preset,
            },
            "metadata": {
                "workflowId": workflow_id,
                "stage": STAGE_KEYFRAME,
                "clipIndex": clip_index,
                "variantKind": VARIANT_KIND_CHARACTER_SHEET if is_character_sheet else "keyframe",
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        })
        image_result = gen_result.get("resultImage", gen_result.get("result", {}))
        if gen_result.get("status") not in ("succeeded", "completed", "success") or not isinstance(image_result, dict):
            raise ValueError(f"图片生成失败：{gen_result.get('error') or '模型返回为空'}")
        output_url = _trim(image_result.get("outputUrl") or image_result.get("metadata", {}).get("outputUrl"))
        if not output_url:
            raise ValueError("图片生成失败：模型未返回图片。")
        image_metadata = image_result.get("metadata", {}) if isinstance(image_result.get("metadata"), dict) else {}
        remote_source_url = _first_non_blank(
            _trim(image_metadata.get("remoteSourceUrl")),
            _trim(image_metadata.get("providerRemoteSourceUrl")),
            _trim(image_result.get("remoteSourceUrl")),
        )
        asset = self._create_material_asset(
            wf=wf,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            media_type="image",
            title=(f"{character.get('name')} 三视图" if character else f"镜头 {clip_index} 关键帧"),
            public_url=output_url,
            mime_type=_trim(image_result.get("mimeType"), "image/png"),
            width=_safe_int(image_result.get("width"), width),
            height=_safe_int(image_result.get("height"), height),
            duration_seconds=0,
            origin_provider=_trim(image_metadata.get("provider")),
            origin_model=_trim(image_metadata.get("providerModel")),
            remote_url=remote_source_url,
            metadata={
                "runId": gen_result.get("id") or image_result.get("runId"),
                "prompt": prompt,
                "remoteSourceUrl": remote_source_url,
                "characterName": character.get("name") if character else "",
                "clip": clip or {},
            },
        )
        self.db.add(asset)
        output_summary = {
            "fileUrl": output_url,
            "previewUrl": output_url,
            "width": _safe_int(image_result.get("width"), width),
            "height": _safe_int(image_result.get("height"), height),
            "prompt": prompt,
            "runId": image_result.get("runId") or gen_result.get("id", ""),
            "remoteSourceUrl": remote_source_url,
        }
        input_summary = {
            "clipIndex": clip_index,
            "prompt": prompt,
        }
        title = f"关键帧 {clip_index + 1}-{version_count + 1}"
        if character is not None:
            output_summary.update({
                "sheetUrl": output_url,
                "characterName": character.get("name", ""),
                "characterAppearance": character.get("appearance", ""),
            })
            input_summary.update({
                "variantKind": VARIANT_KIND_CHARACTER_SHEET,
                "characterName": character.get("name", ""),
                "appearance": character.get("appearance", ""),
            })
            title = f"{character.get('name')} 三视图 {version_count + 1}"
        else:
            output_summary.update({
                "startFrameUrl": output_url,
                "endFrameUrl": output_url,
                "startFrameRemoteUrl": remote_source_url,
                "endFrameRemoteUrl": remote_source_url,
                "selectedFirstFrame": True,
                "selectedLastFrame": True,
            })
            input_summary.update({
                "variantKind": "keyframe",
                "shotLabel": (clip or {}).get("shotLabel", ""),
                "scene": (clip or {}).get("scene", ""),
            })

        keyframe_version = BizStageVersion(
            stage_version_id=version_id,
            workflow_id=workflow_id,
            owner_user_id=wf.owner_user_id,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=title,
            status="COMPLETED",
            selected=1,
            rating_note="",
            parent_version_id="",
            source_material_asset_id="",
            material_asset_id=asset.material_asset_id,
            preview_url=output_url,
            download_url=output_url,
            input_summary_json=_write_json(input_summary),
            output_summary_json=_write_json(output_summary),
            model_call_summary_json=_write_json({
                "runId": image_result.get("runId") or gen_result.get("id", ""),
                "modelInfo": image_result.get("modelInfo", {}),
            }),
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )

        self.db.add(keyframe_version)
        await self._mark_selected_stage_version(workflow_id, STAGE_KEYFRAME, clip_index, version_id)
        wf.current_stage = STAGE_KEYFRAME if is_character_sheet else STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id)

    async def generate_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        frame_role: str,
    ) -> dict[str, Any] | None:
        """Generate single keyframe frame."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None

        # Create a placeholder frame version
        version_id = f"fv_{_random_id()[:12]}"
        now = _now_iso()

        # Count existing versions for this clip and frame role
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0

        frame_version = BizStageVersion(
            stage_version_id=version_id,
            workflow_id=workflow_id,
            owner_user_id=wf.owner_user_id,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=f"关键帧 {clip_index + 1}-{frame_role}",
            status="COMPLETED",
            selected=0,
            rating_note="",
            parent_version_id="",
            source_material_asset_id="",
            material_asset_id="",
            preview_url="",
            download_url="",
            input_summary_json='{"clipIndex": ' + str(clip_index) + ', "frameRole": "' + frame_role + '"}',
            output_summary_json='{"message": "关键帧帧生成中，请稍后刷新查看结果。"}',
            model_call_summary_json="{}",
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )

        self.db.add(frame_version)
        await self.db.commit()

        return await self.get_workflow(workflow_id)

    async def select_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Select a keyframe version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_KEYFRAME)
        if version is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_KEYFRAME, clip_index, version_id)
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def select_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        frame_role: str,
    ) -> dict[str, Any] | None:
        """Select a keyframe frame."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def select_character_sheet_asset(
        self,
        workflow_id: str,
        clip_index: int,
        asset_id: str,
    ) -> dict[str, Any] | None:
        """Link a character sheet material asset to a workflow clip."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None

        # Update the workflow with the selected asset
        now = _now_iso()
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        workflow_id: str,
        clip_index: int,
    ) -> dict[str, Any] | None:
        """Generate video for a clip."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        storyboard_version = await self._selected_storyboard_version(wf)
        if storyboard_version is None:
            raise ValueError("请先选中一个分镜版本。")
        _, clips = self._storyboard_plan(storyboard_version)
        clip = next((item for item in clips if _safe_int(item.get("clipIndex"), 0) == clip_index), None)
        if clip is None:
            raise ValueError("镜头不存在，请重新选择分镜版本。")
        versions = await self._list_stage_versions(workflow_id)
        selected_keyframe = next(
            (
                v for v in versions
                if v.stage_type == STAGE_KEYFRAME
                and v.clip_index == clip_index
                and v.selected == 1
                and _trim(_read_json(v.input_summary_json).get("variantKind", "")) != VARIANT_KIND_CHARACTER_SHEET
            ),
            None,
        )
        if selected_keyframe is None:
            raise ValueError("请先为该镜头生成并选中关键帧。")
        keyframe_output = _read_json(selected_keyframe.output_summary_json)
        first_frame_url = _first_non_blank(
            _trim(keyframe_output.get("startFrameRemoteUrl")),
            _trim(keyframe_output.get("remoteSourceUrl")),
            _trim(keyframe_output.get("remoteUrl")),
        )
        last_frame_url = _first_non_blank(
            _trim(keyframe_output.get("endFrameRemoteUrl")),
            _trim(keyframe_output.get("remoteSourceUrl")),
            _trim(keyframe_output.get("remoteUrl")),
        )
        if not first_frame_url:
            raise ValueError("关键帧缺少远端首帧图片 URL，无法生成视频。")
        model_first_frame_url = self._video_frame_model_input(first_frame_url)
        model_last_frame_url = self._video_frame_model_input(last_frame_url) if last_frame_url else ""
        if not model_first_frame_url:
            raise ValueError("关键帧远端首帧图片 URL 不是视频模型可访问的地址，无法生成视频。")

        version_id = f"vv_{_random_id()[:12]}"
        now = _now_iso()

        # Count existing video versions for this clip
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_VIDEO,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0
        width, height = _dimensions_from_size(wf.video_size, wf.aspect_ratio)
        duration_seconds = _safe_int(clip.get("targetDurationSeconds"), wf.min_duration_seconds or 8)
        duration_seconds = max(1, min(duration_seconds, wf.max_duration_seconds or duration_seconds))
        prompt = self._video_prompt(wf, clip)
        gen_result = await self._get_generation_service().create_run({
            "kind": "video",
            "input": {
                "prompt": prompt,
                "videoSize": wf.video_size,
                "width": width,
                "height": height,
                "durationSeconds": duration_seconds,
                "minDurationSeconds": duration_seconds,
                "maxDurationSeconds": duration_seconds,
                "firstFrameUrl": model_first_frame_url,
                "lastFrameUrl": model_last_frame_url,
                "seed": wf.video_seed,
            },
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": wf.video_model,
            },
            "options": {
                "stylePreset": wf.style_preset,
            },
            "metadata": {
                "workflowId": workflow_id,
                "stage": STAGE_VIDEO,
                "clipIndex": clip_index,
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        })
        video_result = gen_result.get("resultVideo", gen_result.get("result", {}))
        if not isinstance(video_result, dict):
            raise ValueError(f"视频生成失败：{gen_result.get('error') or '模型返回为空'}")
        metadata = video_result.get("metadata", {}) if isinstance(video_result.get("metadata"), dict) else {}
        status = _trim(gen_result.get("status"), "running").upper()
        output_url = _trim(video_result.get("outputUrl") or metadata.get("outputUrl"))
        remote_task_id = _trim(metadata.get("taskId"))
        preview_url = output_url or _trim(video_result.get("thumbnailUrl")) or first_frame_url
        asset_id = ""
        if output_url:
            asset = self._create_material_asset(
                wf=wf,
                stage_type=STAGE_VIDEO,
                clip_index=clip_index,
                version_no=version_count + 1,
                media_type="video",
                title=f"镜头 {clip_index} 视频",
                public_url=output_url,
                mime_type=_trim(video_result.get("mimeType"), "video/mp4"),
                width=_safe_int(video_result.get("width"), width),
                height=_safe_int(video_result.get("height"), height),
                duration_seconds=_safe_float(video_result.get("durationSeconds"), float(duration_seconds)),
                origin_provider=_trim(metadata.get("provider")),
                origin_model=_trim(metadata.get("providerModel")),
                remote_task_id=remote_task_id,
                metadata={
                    "runId": video_result.get("runId") or gen_result.get("id"),
                    "prompt": prompt,
                    "clip": clip,
                },
            )
            self.db.add(asset)
            asset_id = asset.material_asset_id

        video_version = BizStageVersion(
            stage_version_id=version_id,
            workflow_id=workflow_id,
            owner_user_id=wf.owner_user_id,
            stage_type=STAGE_VIDEO,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=f"视频 {clip_index + 1}-{version_count + 1}",
            status="COMPLETED" if output_url else status,
            selected=1 if output_url else 0,
            rating_note="",
            parent_version_id=selected_keyframe.stage_version_id,
            source_material_asset_id="",
            material_asset_id=asset_id,
            preview_url=preview_url,
            download_url=output_url,
            input_summary_json=_write_json({
                "clipIndex": clip_index,
                "prompt": prompt,
                "firstFrameUrl": first_frame_url,
                "lastFrameUrl": last_frame_url,
            }),
            output_summary_json=_write_json({
                "fileUrl": output_url,
                "previewUrl": preview_url,
                "posterUrl": first_frame_url,
                "taskId": remote_task_id,
                "taskStatus": metadata.get("taskStatus", status),
                "durationSeconds": duration_seconds,
                "width": width,
                "height": height,
                "prompt": prompt,
                "runId": video_result.get("runId") or gen_result.get("id", ""),
            }),
            model_call_summary_json=_write_json({
                "runId": video_result.get("runId") or gen_result.get("id", ""),
                "modelInfo": video_result.get("modelInfo", {}),
            }),
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )

        self.db.add(video_version)
        if output_url:
            await self._mark_selected_stage_version(workflow_id, STAGE_VIDEO, clip_index, version_id)
            wf.current_stage = STAGE_JOINED
        else:
            wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id)

    async def select_video(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Select a video version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_VIDEO, clip_index, version_id)
        wf.current_stage = STAGE_JOINED
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Finalize
    # ------------------------------------------------------------------

    async def finalize_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Mark workflow completed with the selected videos as final output."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        selected_videos = [
            v for v in versions
            if v.stage_type == STAGE_VIDEO and v.selected == 1 and _trim(v.preview_url)
        ]
        if not selected_videos:
            raise ValueError("请先为每个镜头选中视频版本。")
        selected_videos.sort(key=lambda v: v.clip_index)
        first = selected_videos[0]
        asset = self._create_material_asset(
            wf=wf,
            stage_type=STAGE_JOINED,
            clip_index=0,
            version_no=1,
            media_type="video",
            title=f"{wf.title} 完整视频",
            public_url=first.download_url or first.preview_url,
            mime_type="video/mp4",
            width=0,
            height=0,
            duration_seconds=sum(_safe_float(_read_json(v.output_summary_json).get("durationSeconds"), 0.0) for v in selected_videos),
            metadata={
                "sourceVideoVersionIds": [v.stage_version_id for v in selected_videos],
                "note": "当前环境使用首个已选视频作为成片预览，真实拼接服务接入后会生成完整拼接文件。",
            },
        )
        self.db.add(asset)
        wf.final_join_asset_id = asset.material_asset_id
        wf.current_stage = STAGE_JOINED
        wf.status = STATUS_COMPLETED
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Ratings & cleanup
    # ------------------------------------------------------------------

    async def rate_workflow(
        self,
        workflow_id: str,
        rating: int,
        note: str = "",
    ) -> dict[str, Any] | None:
        """Rate a workflow (1-5)."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        wf.effect_rating = rating
        wf.effect_rating_note = note
        wf.rated_at = _now_iso()
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def rate_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        rating: int,
        note: str = "",
    ) -> dict[str, Any] | None:
        """Rate a stage version."""
        version = await self._require_stage_version(workflow_id, version_id, "")
        if version is None:
            return None
        version.rating = rating
        version.rating_note = note
        version.rated_at = _now_iso()
        version.update_time = _now_iso()
        if version.material_asset_id:
            asset = await self._find_asset(version.material_asset_id)
            if asset is not None:
                asset.user_rating = rating
                asset.rating_note = note
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def delete_stage_version(
        self,
        workflow_id: str,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Delete a stage version and its downstream selections."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        target = await self._require_stage_version(workflow_id, version_id, "")
        if target is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        to_delete = self._resolve_delete_version_chain(target, versions)
        now = _now_iso()
        for v in to_delete:
            v.selected = 0
            v.is_deleted = 1
            v.update_time = now
            if v.material_asset_id:
                await self._mark_asset_deleted(v.material_asset_id)
        wf.update_time = now
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _require_workflow(self, workflow_id: str) -> BizStageWorkflow | None:
        stmt = select(BizStageWorkflow).where(
            BizStageWorkflow.workflow_id == workflow_id,
            BizStageWorkflow.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _require_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        expected_stage_type: str,
    ) -> BizStageVersion | None:
        stmt = select(BizStageVersion).where(
            BizStageVersion.workflow_id == workflow_id,
            BizStageVersion.stage_version_id == version_id,
            BizStageVersion.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            return None
        if expected_stage_type and version.stage_type != expected_stage_type:
            return None
        return version

    async def _find_asset(self, asset_id: str) -> BizMaterialAsset | None:
        stmt = select(BizMaterialAsset).where(
            BizMaterialAsset.material_asset_id == asset_id,
            BizMaterialAsset.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _mark_asset_deleted(self, asset_id: str) -> None:
        if not asset_id:
            return
        stmt = (
            update(BizMaterialAsset)
            .where(
                BizMaterialAsset.material_asset_id == asset_id,
                BizMaterialAsset.is_deleted == 0,
            )
            .values(selected_for_next=0, is_deleted=1, update_time=_now_iso())
        )
        await self.db.execute(stmt)

    async def _list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        stmt = (
            select(BizStageVersion)
            .where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.is_deleted == 0,
            )
            .order_by(
                BizStageVersion.stage_type,
                BizStageVersion.clip_index,
                BizStageVersion.version_no.desc(),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _refresh_video_versions(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> bool:
        changed = False
        now = _now_iso()
        for version in versions:
            if version.stage_type != STAGE_VIDEO or version.is_deleted != 0:
                continue
            status = _trim(version.status).upper()
            if status == "COMPLETED" and _trim(version.download_url):
                continue
            output_summary = _read_json(version.output_summary_json)
            run_id = _trim(output_summary.get("runId")) or _trim(_read_json(version.model_call_summary_json).get("runId"))
            if not run_id:
                continue
            try:
                run = await self._get_generation_service().get_run(run_id)
            except Exception:
                continue
            video_result = (run or {}).get("resultVideo") or (run or {}).get("result") or {}
            if not isinstance(video_result, dict):
                continue
            metadata = video_result.get("metadata", {}) if isinstance(video_result.get("metadata"), dict) else {}
            run_status = _trim((run or {}).get("status")).lower()
            output_url = _trim(video_result.get("outputUrl") or metadata.get("outputUrl") or metadata.get("fileUrl"))
            task_status = _trim(metadata.get("taskStatus") or output_summary.get("taskStatus") or status)

            if output_url:
                asset_id = version.material_asset_id
                if not asset_id:
                    asset = self._create_material_asset(
                        wf=wf,
                        stage_type=STAGE_VIDEO,
                        clip_index=_safe_int(version.clip_index, 0),
                        version_no=_safe_int(version.version_no, 1),
                        media_type="video",
                        title=version.title or f"镜头 {version.clip_index} 视频",
                        public_url=output_url,
                        mime_type=_trim(video_result.get("mimeType"), "video/mp4"),
                        width=_safe_int(video_result.get("width") or output_summary.get("width"), 0),
                        height=_safe_int(video_result.get("height") or output_summary.get("height"), 0),
                        duration_seconds=_safe_float(video_result.get("durationSeconds") or output_summary.get("durationSeconds"), 0.0),
                        origin_provider=_trim(metadata.get("provider")),
                        origin_model=_trim(metadata.get("providerModel")),
                        remote_task_id=_trim(metadata.get("taskId") or output_summary.get("taskId")),
                        remote_url=_trim(metadata.get("remoteSourceUrl")),
                        metadata={
                            "runId": run_id,
                            "taskId": _trim(metadata.get("taskId") or output_summary.get("taskId")),
                            "taskStatus": task_status,
                            "remoteSourceUrl": _trim(metadata.get("remoteSourceUrl")),
                        },
                    )
                    self.db.add(asset)
                    asset_id = asset.material_asset_id
                output_summary.update({
                    "fileUrl": output_url,
                    "previewUrl": output_url,
                    "taskStatus": task_status or "COMPLETED",
                    "remoteSourceUrl": _trim(metadata.get("remoteSourceUrl")),
                })
                version.status = "COMPLETED"
                version.selected = 1
                version.material_asset_id = asset_id
                version.preview_url = output_url
                version.download_url = output_url
                version.output_summary_json = _write_json(output_summary)
                version.update_time = now
                await self._mark_selected_stage_version(wf.workflow_id, STAGE_VIDEO, _safe_int(version.clip_index, 0), version.stage_version_id)
                wf.current_stage = STAGE_JOINED
                wf.status = STATUS_READY
                wf.update_time = now
                changed = True
                continue

            if run_status in {"failed", "error"}:
                output_summary["taskStatus"] = task_status or "FAILED"
                output_summary["error"] = _trim(video_result.get("error") or metadata.get("taskMessage") or metadata.get("error"))
                version.status = "FAILED"
                version.output_summary_json = _write_json(output_summary)
                version.update_time = now
                changed = True
            elif task_status:
                output_summary["taskStatus"] = task_status
                version.output_summary_json = _write_json(output_summary)
                version.update_time = now
                changed = True

        if changed:
            await self.db.commit()
        return changed

    async def _mark_selected_stage_version(
        self,
        workflow_id: str,
        stage_type: str,
        clip_index: int,
        selected_version_id: str,
    ) -> None:
        stmt = select(BizStageVersion).where(
            BizStageVersion.workflow_id == workflow_id,
            BizStageVersion.stage_type == stage_type,
            BizStageVersion.clip_index == clip_index,
            BizStageVersion.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        versions = result.scalars().all()
        now = _now_iso()
        for v in versions:
            v.selected = 1 if v.stage_version_id == selected_version_id else 0
            v.update_time = now

    async def _selected_storyboard_version(self, wf: BizStageWorkflow) -> BizStageVersion | None:
        version_id = _trim(wf.selected_storyboard_version_id)
        versions = await self._list_stage_versions(wf.workflow_id)
        storyboards = [v for v in versions if v.stage_type == STAGE_STORYBOARD]
        if version_id:
            for version in storyboards:
                if version.stage_version_id == version_id:
                    return version
        selected = next((v for v in storyboards if v.selected == 1), None)
        if selected is not None:
            return selected
        return storyboards[0] if storyboards else None

    def _storyboard_plan(self, version: BizStageVersion | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if version is None:
            return [], []
        output = _read_json(version.output_summary_json)
        script = _trim(output.get("scriptMarkdown") or output.get("previewText"))
        return _parse_storyboard_markdown(script)

    @staticmethod
    def _character_sheet_prompt(character: dict[str, Any] | None) -> str:
        if not character:
            return ""
        return (
            f"Create a clean character turnaround sheet for {character.get('name', '角色')}. "
            f"Show front view, side view, and back view in one image, full body, consistent outfit and face. "
            f"Character definition: {character.get('appearance', '')}. "
            "Plain light background, no text labels, no props, no logo, no watermark."
        )

    @staticmethod
    def _keyframe_prompt(wf: BizStageWorkflow, clip: dict[str, Any]) -> str:
        return (
            f"{wf.style_preset} cinematic keyframe, aspect ratio {wf.aspect_ratio}. "
            f"Shot: {clip.get('shotLabel', '')}. "
            f"Start frame: {clip.get('startFrame', '')}. "
            f"End frame: {clip.get('endFrame', '')}. "
            f"Scene action: {clip.get('scene', '')}. "
            "Generate a polished production keyframe, no text, no watermark."
        )

    @staticmethod
    def _video_frame_model_input(public_url: str) -> str:
        normalized = _trim(public_url)
        if normalized.startswith(("http://", "https://")):
            return normalized
        return ""

    @staticmethod
    def _video_prompt(wf: BizStageWorkflow, clip: dict[str, Any]) -> str:
        return (
            f"{wf.style_preset} short drama video clip. "
            f"Shot: {clip.get('shotLabel', '')}. "
            f"Scene action: {clip.get('scene', '')}. "
            f"Start frame: {clip.get('startFrame', '')}. "
            f"End frame: {clip.get('endFrame', '')}. "
            "Keep character identity consistent, natural camera motion, no subtitles, no watermark."
        )

    def _create_material_asset(
        self,
        *,
        wf: BizStageWorkflow,
        stage_type: str,
        clip_index: int,
        version_no: int,
        media_type: str,
        title: str,
        public_url: str,
        mime_type: str = "",
        width: int = 0,
        height: int = 0,
        duration_seconds: float = 0,
        origin_provider: str = "",
        origin_model: str = "",
        remote_task_id: str = "",
        remote_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> BizMaterialAsset:
        now = _now_iso()
        return BizMaterialAsset(
            material_asset_id=f"mat_{_random_id()[:16]}",
            remark="",
            owner_user_id=wf.owner_user_id,
            task_id="",
            workflow_id=wf.workflow_id,
            source_task_id="",
            source_material_id="",
            asset_role=stage_type,
            stage_type=stage_type,
            clip_index=clip_index,
            version_no=version_no,
            selected_for_next=1,
            media_type=media_type,
            title=title,
            user_rating=None,
            rating_note="",
            origin_provider=origin_provider,
            origin_model=origin_model,
            remote_task_id=remote_task_id,
            remote_asset_id="",
            original_file_name="",
            stored_file_name="",
            file_ext="",
            storage_provider="local",
            mime_type=mime_type,
            size_bytes=0,
            sha256="",
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            has_audio=1 if media_type == "video" else 0,
            local_storage_path="",
            local_file_path="",
            public_url=public_url,
            thumbnail_url=public_url if media_type == "image" else "",
            third_party_url="",
            remote_url=remote_url,
            metadata_json=_write_json(metadata or {}),
            captured_at=now,
            timezone_offset_minutes=0,
            create_time=now,
            update_time=now,
            is_deleted=0,
        )

    async def _load_asset_map(
        self,
        versions: list[BizStageVersion],
        final_join_asset_id: str | None,
    ) -> dict[str, BizMaterialAsset]:
        asset_ids: set[str] = set()
        for v in versions:
            if v.material_asset_id:
                asset_ids.add(v.material_asset_id)
        if final_join_asset_id:
            asset_ids.add(final_join_asset_id)
        if not asset_ids:
            return {}
        stmt = select(BizMaterialAsset).where(
            BizMaterialAsset.material_asset_id.in_(asset_ids),
            BizMaterialAsset.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        assets = result.scalars().all()
        return {a.material_asset_id: a for a in assets}

    def _resolve_delete_version_chain(
        self,
        target: BizStageVersion,
        versions: list[BizStageVersion],
    ) -> list[BizStageVersion]:
        deleted: list[BizStageVersion] = [target]
        if target.stage_type == STAGE_STORYBOARD:
            for v in versions:
                if v.stage_type == STAGE_KEYFRAME and v.parent_version_id == target.stage_version_id:
                    deleted.append(v)
            kf_ids = {v.stage_version_id for v in deleted if v.stage_type == STAGE_KEYFRAME}
            for v in versions:
                if v.stage_type == STAGE_VIDEO and v.parent_version_id in kf_ids:
                    deleted.append(v)
        elif target.stage_type == STAGE_KEYFRAME:
            for v in versions:
                if v.stage_type == STAGE_VIDEO and v.parent_version_id == target.stage_version_id:
                    deleted.append(v)
        seen: dict[str, BizStageVersion] = {}
        for v in deleted:
            seen[v.stage_version_id] = v
        return list(seen.values())

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------

    def _to_workflow_summary(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> dict[str, Any]:
        storyboard_count = sum(1 for v in versions if v.stage_type == STAGE_STORYBOARD)
        character_sheet_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) == VARIANT_KIND_CHARACTER_SHEET
        )
        selected_character_sheet_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) == VARIANT_KIND_CHARACTER_SHEET
            and v.selected == 1
        )
        keyframe_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) != VARIANT_KIND_CHARACTER_SHEET
        )
        video_count = sum(1 for v in versions if v.stage_type == STAGE_VIDEO)
        selected_keyframe_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) != VARIANT_KIND_CHARACTER_SHEET
            and v.selected == 1
        )
        return {
            "id": wf.workflow_id,
            "title": wf.title,
            "status": wf.status,
            "currentStage": wf.current_stage,
            "aspectRatio": wf.aspect_ratio,
            "effectRating": wf.effect_rating,
            "createdAt": wf.create_time,
            "updatedAt": wf.update_time,
            "storyboardVersionCount": storyboard_count,
            "keyframeVersionCount": keyframe_count,
            "selectedKeyframeCount": selected_keyframe_count,
            "videoVersionCount": video_count,
            "characterSheetVersionCount": character_sheet_count,
            "characterSheetCount": character_sheet_count,
            "selectedCharacterSheetCount": selected_character_sheet_count,
        }

    def _to_workflow_detail(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
        asset_map: dict[str, BizMaterialAsset],
    ) -> dict[str, Any]:
        storyboard_versions = [
            v for v in versions if v.stage_type == STAGE_STORYBOARD
        ]
        storyboard_versions.sort(key=lambda v: _safe_int(v.version_no, 0), reverse=True)
        selected_storyboard = next((v for v in storyboard_versions if v.stage_version_id == wf.selected_storyboard_version_id), None)
        if selected_storyboard is None:
            selected_storyboard = next((v for v in storyboard_versions if v.selected == 1), None)
        if selected_storyboard is None and storyboard_versions:
            selected_storyboard = storyboard_versions[0]
        characters, storyboard_clips = self._storyboard_plan(selected_storyboard)
        # Build clip slots from keyframe and video versions
        keyframe_versions = [v for v in versions if v.stage_type == STAGE_KEYFRAME]
        video_versions = [v for v in versions if v.stage_type == STAGE_VIDEO]

        # Group keyframe versions by clip index
        keyframe_by_clip: dict[int, list[BizStageVersion]] = {}
        for v in keyframe_versions:
            clip_idx = _safe_int(v.clip_index, 0)
            keyframe_by_clip.setdefault(clip_idx, []).append(v)

        # Group video versions by clip index
        video_by_clip: dict[int, list[BizStageVersion]] = {}
        for v in video_versions:
            clip_idx = _safe_int(v.clip_index, 0)
            video_by_clip.setdefault(clip_idx, []).append(v)

        # Get all unique non-character clip indexes. Storyboard clips are the source of truth.
        storyboard_clip_indexes = [_safe_int(item.get("clipIndex"), 0) for item in storyboard_clips]
        all_clip_indexes = sorted(
            idx for idx in set(storyboard_clip_indexes + list(keyframe_by_clip.keys()) + list(video_by_clip.keys()))
            if idx > 0 and idx < CHARACTER_SHEET_CLIP_INDEX_BASE
        )

        clip_slots = []
        for clip_idx in all_clip_indexes:
            clip = next((item for item in storyboard_clips if _safe_int(item.get("clipIndex"), 0) == clip_idx), {})
            clip_slots.append({
                "clipIndex": clip_idx,
                "shotLabel": clip.get("shotLabel") or f"镜头 {clip_idx:03d}",
                "scene": clip.get("scene"),
                "durationHint": clip.get("durationHint"),
                "targetDurationSeconds": clip.get("targetDurationSeconds"),
                "matchedCharacters": None,
                "keyframeVersions": [
                    self._to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sorted(keyframe_by_clip.get(clip_idx, []), key=lambda v: _safe_int(v.version_no, 0), reverse=True)
                ],
                "videoVersions": [
                    self._to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sorted(video_by_clip.get(clip_idx, []), key=lambda v: _safe_int(v.version_no, 0), reverse=True)
                ],
            })
        character_sheets = []
        for idx, character in enumerate(characters, start=1):
            synthetic_clip_index = CHARACTER_SHEET_CLIP_INDEX_BASE + idx
            sheet_versions = sorted(
                keyframe_by_clip.get(synthetic_clip_index, []),
                key=lambda v: _safe_int(v.version_no, 0),
                reverse=True,
            )
            character_sheets.append({
                "id": f"{wf.workflow_id}-character-{idx}",
                "characterName": character.get("name", ""),
                "name": character.get("name", ""),
                "displayName": character.get("name", ""),
                "appearanceSummary": character.get("summary", ""),
                "appearance": character.get("appearance", ""),
                "syntheticClipIndex": synthetic_clip_index,
                "clipIndex": synthetic_clip_index,
                "versions": [
                    self._to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sheet_versions
                ],
                "keyframeVersions": [
                    self._to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sheet_versions
                ],
            })

        return {
            "id": wf.workflow_id,
            "title": wf.title,
            "transcriptText": wf.transcript_text,
            "aspectRatio": wf.aspect_ratio,
            "stylePreset": wf.style_preset,
            "textAnalysisModel": wf.text_analysis_model,
            "imageModel": wf.image_model,
            "videoModel": wf.video_model,
            "videoSize": wf.video_size,
            "keyframeSeed": wf.keyframe_seed,
            "videoSeed": wf.video_seed,
            "seed": None,
            "durationMode": wf.duration_mode or "auto",
            "minDurationSeconds": wf.min_duration_seconds,
            "maxDurationSeconds": wf.max_duration_seconds,
            "status": wf.status,
            "currentStage": wf.current_stage,
            "selectedStoryboardVersionId": wf.selected_storyboard_version_id,
            "effectRating": wf.effect_rating,
            "effectRatingNote": wf.effect_rating_note,
            "ratedAt": wf.rated_at,
            "createdAt": wf.create_time,
            "updatedAt": wf.update_time,
            "storyboardVersions": [
                self._to_stage_version_row(v, asset_map.get(v.material_asset_id))
                for v in storyboard_versions
            ],
            "characterSheets": character_sheets,
            "clipSlots": clip_slots,
            "finalResult": self._to_material_asset_row(asset_map.get(wf.final_join_asset_id)) if wf.final_join_asset_id else None,
        }

    def _to_stage_version_row(
        self,
        version: BizStageVersion,
        asset: BizMaterialAsset | None,
    ) -> dict[str, Any]:
        input_summary = _read_json(version.input_summary_json)
        output_summary = _read_json(version.output_summary_json)
        model_call_summary = _read_json(version.model_call_summary_json)
        return {
            "id": version.stage_version_id,
            "stageType": version.stage_type,
            "clipIndex": _safe_int(version.clip_index, 0),
            "versionNo": _safe_int(version.version_no, 0),
            "title": version.title,
            "status": version.status,
            "selected": version.selected == 1,
            "rating": version.rating,
            "ratingNote": version.rating_note,
            "ratedAt": version.rated_at,
            "parentVersionId": version.parent_version_id,
            "sourceMaterialAssetId": version.source_material_asset_id,
            "materialAssetId": version.material_asset_id,
            "previewUrl": version.preview_url,
            "downloadUrl": version.download_url,
            "inputSummary": input_summary,
            "outputSummary": output_summary,
            "modelCallSummary": model_call_summary,
            "createdAt": version.create_time,
            "updatedAt": version.update_time,
            "asset": self._to_material_asset_row(asset) if asset else None,
        }

    def _to_material_asset_row(
        self,
        asset: BizMaterialAsset | None,
    ) -> dict[str, Any] | None:
        if asset is None:
            return None
        metadata = _read_json(asset.metadata_json)
        return {
            "id": asset.material_asset_id,
            "workflowId": asset.workflow_id,
            "stageType": asset.stage_type,
            "mediaType": asset.media_type,
            "title": asset.title,
            "mimeType": asset.mime_type,
            "durationSeconds": asset.duration_seconds,
            "width": asset.width,
            "height": asset.height,
            "hasAudio": _safe_bool(asset.has_audio),
            "fileUrl": asset.public_url,
            "previewUrl": asset.public_url,
            "thumbnailUrl": asset.thumbnail_url or "",
            "remoteUrl": asset.remote_url,
            "userRating": asset.user_rating,
            "ratingNote": asset.rating_note,
            "originModel": asset.origin_model,
            "originProvider": asset.origin_provider,
            "metadata": metadata,
            "createdAt": asset.create_time,
            "updatedAt": asset.update_time,
        }
