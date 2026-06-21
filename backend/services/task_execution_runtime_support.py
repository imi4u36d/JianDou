from __future__ import annotations

import uuid
from typing import Any

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import _TaskArtifactNaming
from backend.services.task_worker_status_stage_service import TaskExecutionAbortedException
from backend.shared import first_non_blank, string_value


def _truncate_text(value: str, max_length: int) -> str:
    if not value:
        return ""
    normalized = value.replace("\n", " ").strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length] + "..."


class GenerationRunKinds:
    SCRIPT = "script"
    IMAGE = "image"
    VIDEO = "video"


class GenerationModelKinds:
    IMAGE = "image"
    VIDEO = "video"


class ModelRuntimePropertiesResolverStub:
    """Stub for model runtime properties resolver."""

    def int_value(self, *keys: str, default: int = 0) -> int:
        return default

    def value(self, *keys: str, default: str = "") -> str:
        return default

    def supports_seed(self, model: str) -> bool:
        return False


class TaskExecutionRuntimeSupport:
    """Runtime utilities for task execution: dimensions, duration, request building."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        model_resolver: ModelRuntimePropertiesResolverStub | None = None,
        local_media_artifact_service: Any | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._model_resolver = model_resolver or ModelRuntimePropertiesResolverStub()
        self._local_media_artifact_service = local_media_artifact_service

    def active_attempt(self, task: TaskRecord) -> dict[str, Any] | None:
        if not task.active_attempt_id:
            return None
        for row in task.attempts:
            if task.active_attempt_id == string_value(row.get("attemptId", "")):
                return row
        return None

    def resolve_dimensions(self, task: TaskRecord) -> list[int]:
        snapshot = task.request_snapshot or {}
        image_size = string_value(snapshot.get("imageSize", ""))
        if image_size:
            parsed = self._parse_dimensions(image_size)
            if parsed:
                return parsed
        video_size = string_value(snapshot.get("videoSize", ""))
        if video_size:
            parsed = self._parse_dimensions(video_size)
            if parsed:
                return parsed
        aspect_map = {
            "16:9": [1280, 720],
            "1:1": [1024, 1024],
            "21:9": [1536, 658],
            "3:2": [1216, 832],
            "4:3": [1152, 896],
            "3:4": [896, 1152],
            "2:3": [832, 1216],
        }
        return aspect_map.get(task.aspect_ratio, [720, 1280])

    def resolve_duration_seconds(self, task: TaskRecord) -> int:
        snapshot = task.request_snapshot or {}
        video_duration = snapshot.get("videoDuration")
        if isinstance(video_duration, dict):
            if not video_duration.get("auto", True):
                seconds = video_duration.get("seconds")
                if isinstance(seconds, int) and seconds > 0:
                    return max(1, seconds)
        if task.max_duration_seconds > 0:
            return task.max_duration_seconds
        if task.min_duration_seconds > 0:
            return task.min_duration_seconds
        configured_default = self._model_resolver.int_value("catalog.defaults", "video_duration_seconds", default=10)
        return max(1, configured_default)

    def assert_task_still_active(self, task: TaskRecord) -> None:
        if self._task_repository is None:
            return
        if TaskStatus.is_execution_active(TaskStatus(task.status) if TaskStatus(task.status) else None):
            return
        raise TaskExecutionAbortedException(task.status, first_non_blank(task.error_message, "任务已停止执行。"))

    def build_script_run_request(self, task: TaskRecord) -> dict[str, Any]:
        source_text = first_non_blank(
            task.transcript_text,
            task.creative_prompt,
            task.title,
        )
        request: dict[str, Any] = {
            "kind": GenerationRunKinds.SCRIPT,
            "input": {"text": source_text},
            "model": {"textAnalysisModel": self._text_analysis_model(task)},
            "options": {"visualStyle": "AI 自动决策"},
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileName": _TaskArtifactNaming.storyboard_file_name(task, "md"),
            },
        }
        self._put_user_auth(request, task)
        return dict(request)

    def build_image_run_request(
        self,
        task: TaskRecord,
        clip_index: int,
        prompt: str,
        width: int,
        height: int,
        reference_image_url: str,
        duration_seconds: int = 0,
        frame_role: str = "first",
    ) -> dict[str, Any]:
        normalized_frame_role = self._normalize_frame_role(frame_role)
        input_data: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": normalized_frame_role,
        }
        if duration_seconds > 0:
            input_data["durationSeconds"] = duration_seconds
        image_seed = self._image_seed(task, clip_index)
        image_model = self._image_model(task)
        if image_seed is not None and self._model_resolver.supports_seed(image_model):
            input_data["seed"] = image_seed
        if reference_image_url:
            compatible = self._compatible_single_image_reference_url(reference_image_url, image_model)
            if compatible:
                input_data["referenceImageUrl"] = compatible[0]
                input_data["referenceImageUrls"] = compatible
        request: dict[str, Any] = {
            "kind": GenerationRunKinds.IMAGE,
            "input": input_data,
            "model": {
                "textAnalysisModel": self._text_analysis_model(task),
                "providerModel": image_model,
            },
            "options": {"stylePreset": self._style_preset(task)},
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileStem": f"clip{max(1, clip_index)}-{normalized_frame_role}",
            },
            "metadata": {
                "relatedTaskId": string_value(task.id),
                "clipIndex": max(1, clip_index),
                "frameRole": normalized_frame_role,
            },
        }
        self._put_user_auth(request, task)
        return dict(request)

    def build_workspace_image_run_request(self, task: TaskRecord, width: int, height: int) -> dict[str, Any]:
        snapshot = task.request_snapshot or {}
        asset_type = string_value(snapshot.get("assetType", ""))
        if not asset_type:
            asset_type = "character_sheet" if task.task_type == "character_sheet" else "free"
        prompt = first_non_blank(
            string_value(snapshot.get("creativePrompt", "")),
            task.creative_prompt,
            task.title,
        )
        reference_urls = self._reference_image_urls(task)
        prompt = self._build_workspace_image_prompt(asset_type, task.title, prompt, bool(reference_urls))
        input_data: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": asset_type,
        }
        if asset_type == "free":
            input_data["promptPassthrough"] = True
        image_model = self._image_model(task)
        compatible = self._compatible_image_reference_url_list(reference_urls, image_model)
        if compatible:
            input_data["referenceImageUrl"] = compatible[0]
            input_data["referenceImageUrls"] = compatible
        image_seed = self._task_seed(task)
        if image_seed is not None and self._model_resolver.supports_seed(image_model):
            input_data["seed"] = image_seed
        request: dict[str, Any] = {
            "kind": GenerationRunKinds.IMAGE,
            "input": input_data,
            "model": {
                "textAnalysisModel": self._text_analysis_model(task),
                "providerModel": image_model,
            },
            "options": {"stylePreset": self._style_preset(task)},
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileStem": "workspace-image",
                "requireRemoteSourceUrl": False,
            },
            "metadata": {
                "relatedTaskId": string_value(task.id),
                "taskType": task.task_type,
                "assetType": asset_type,
                "referenceImageCount": len(compatible),
            },
        }
        self._put_user_auth(request, task)
        return dict(request)

    def build_video_run_request(
        self,
        task: TaskRecord,
        clip_index: int,
        prompt: str,
        video_size: str,
        duration_seconds: int,
        min_duration_seconds: int,
        max_duration_seconds: int,
        first_frame_url: str,
        last_frame_url: str,
    ) -> dict[str, Any]:
        input_data: dict[str, Any] = {
            "prompt": self._build_video_clip_execution_prompt(prompt),
            "videoSize": video_size,
            "durationSeconds": duration_seconds,
            "minDurationSeconds": min_duration_seconds,
            "maxDurationSeconds": max_duration_seconds,
            "firstFrameUrl": first_frame_url,
            "generateAudio": self._default_video_generate_audio(),
            "returnLastFrame": True,
        }
        if last_frame_url:
            input_data["lastFrameUrl"] = last_frame_url
        task_seed = self._task_seed(task)
        if task_seed is not None:
            input_data["seed"] = task_seed
        request: dict[str, Any] = {
            "kind": GenerationRunKinds.VIDEO,
            "input": input_data,
            "model": {
                "textAnalysisModel": self._text_analysis_model(task),
                "providerModel": self._video_model(task),
            },
            "options": {"stylePreset": self._style_preset(task)},
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileStem": f"clip{max(1, clip_index)}",
            },
            "metadata": {
                "relatedTaskId": string_value(task.id),
                "clipIndex": max(1, clip_index),
            },
        }
        self._put_user_auth(request, task)
        return dict(request)

    def _parse_dimensions(self, value: str) -> list[int] | None:
        normalized = string_value(value).lower().replace("x", "*")
        parts = normalized.split("*")
        if len(parts) != 2:
            return None
        try:
            width = int(parts[0].strip())
            height = int(parts[1].strip())
            return [width, height] if width > 0 and height > 0 else None
        except (ValueError, TypeError):
            return None

    def _text_analysis_model(self, task: TaskRecord) -> str:
        return self._required_snapshot_model(task, "textAnalysisModel", "文本模型")

    def _image_model(self, task: TaskRecord) -> str:
        return self._required_snapshot_model(task, "imageModel", "关键帧模型")

    def _video_model(self, task: TaskRecord) -> str:
        return self._required_snapshot_model(task, "videoModel", "视频模型")

    def _required_snapshot_model(self, task: TaskRecord, field_name: str, label: str) -> str:
        snapshot = task.request_snapshot or {}
        configured = string_value(snapshot.get(field_name, ""))
        if configured:
            return configured
        raise ValueError(f"任务缺少必选模型：{label}（{field_name}）")

    def _style_preset(self, task: TaskRecord) -> str:
        snapshot = task.request_snapshot or {}
        configured = string_value(snapshot.get("stylePreset", ""))
        return configured if configured else "cinematic"

    def _task_seed(self, task: TaskRecord) -> int | None:
        snapshot = task.request_snapshot or {}
        configured = snapshot.get("seed")
        if isinstance(configured, int):
            return configured
        return task.task_seed

    def _image_seed(self, task: TaskRecord, clip_index: int) -> int | None:
        seed = self._task_seed(task)
        if seed is not None:
            return seed
        task_identity = first_non_blank(task.id, task.title, task.creative_prompt, "task")
        seed_source = f"{task_identity}:clip:{max(1, clip_index)}:keyframe"
        raw = uuid.uuid5(uuid.NAMESPACE_OID, seed_source).int >> 64
        return (raw % (2**31 - 2)) + 1

    def _normalize_frame_role(self, frame_role: str) -> str:
        return "last" if frame_role.lower() == "last" else "first"

    def _compatible_single_image_reference_url(self, reference_image_url: str, image_model: str) -> list[str]:
        normalized = string_value(reference_image_url)
        if not normalized:
            return []
        if normalized.startswith("/storage/"):
            if self._local_media_artifact_service:
                public_url = self._local_media_artifact_service.build_externally_accessible_url(normalized)
                if public_url:
                    return [public_url]
                if self._supports_image_data_uri_references(image_model):
                    try:
                        data_uri = self._local_media_artifact_service.image_data_uri_from_public_url(normalized)
                        if data_uri:
                            return [data_uri]
                    except RuntimeError:
                        raise ValueError(
                            "referenceImageUrl is local storage address; configure "
                            "JIANDOU_STORAGE_PUBLIC_BASE_URL or use an image model "
                            "that supports data URI references"
                        )
            raise ValueError(
                "referenceImageUrl is local storage address; configure "
                "JIANDOU_STORAGE_PUBLIC_BASE_URL or use an image model "
                "that supports data URI references"
            )
        return [normalized]

    def _compatible_image_reference_url_list(self, urls: list[str], image_model: str) -> list[str]:
        resolved: list[str] = []
        for url in urls:
            for item in self._compatible_single_image_reference_url(url, image_model):
                if item and item not in resolved:
                    resolved.append(item)
        return resolved

    def _reference_image_urls(self, task: TaskRecord) -> list[str]:
        ctx = task.execution_context or {}
        raw = ctx.get("referenceImageUrls")
        if isinstance(raw, list):
            values: list[str] = []
            for item in raw:
                normalized = string_value(item)
                if normalized and normalized not in values:
                    values.append(normalized)
            return values
        return []

    def _supports_image_data_uri_references(self, image_model: str) -> bool:
        lower = string_value(image_model).lower()
        return "gpt-image" in lower or "seedream" in lower

    def _build_workspace_image_prompt(self, asset_type: str, title: str, description: str, has_references: bool) -> str:
        normalized_asset_type = string_value(asset_type)
        normalized_description = string_value(description)
        if normalized_asset_type in ("free", ""):
            return normalized_description
        parts: list[str] = [
            f"素材标题：{first_non_blank(title, '工作台图片生成')}",
            f"素材描述：{normalized_description}",
        ]
        if has_references:
            parts.append("参考图要求：严格沿用参考图中的主体结构、外观锚点、材质和关键比例，不要重新设计核心主体。")
        if normalized_asset_type == "character_sheet":
            parts.append("生成类型：角色三视图设定图。")
            parts.append("必须输出同一角色的正面、侧面、背面三视图，放在同一张图中。")
            parts.append("三个视图都必须是完整从头到脚全身像，人物整体缩小并居中，头顶、双手、鞋子、脚底四周保留清晰留白，不得裁切或超出图片外。")
            parts.append("禁止半身像、胸像、近景特写、肖像照或过度放大构图；三个视图横向等距排列在同一张画布内。")
            parts.append("使用标准中性站姿，身体直立，双臂自然下垂或微微离身，双手空置，不做动作戏、剧情动作、表演动作或复杂姿势。")
            parts.append("只保留稳定穿戴配饰；禁止手拿、背负、牵引、互动或携带任何道具、武器、包袋、手机、文件、杯子、伞、花束等物体。")
            parts.append("脸、发型、服装、体型、年龄感和配饰保持一致。")
            parts.append("背景使用纯净浅色或纯白背景，不出现文字、箭头、水印、logo、说明标签或复杂场景。")
        return "\n".join(parts)

    def _build_video_clip_execution_prompt(self, prompt: str) -> str:
        return _truncate_text(prompt, 2200)

    def _default_video_generate_audio(self) -> bool:
        val = self._model_resolver.value("catalog.defaults", "video_generate_audio", default="true")
        return bool(val) and val.lower() in ("true", "1", "yes")

    def _put_user_auth(self, request: dict[str, Any], task: TaskRecord) -> None:
        if task.owner_user_id is not None:
            request["auth"] = {"userId": str(task.owner_user_id)}
