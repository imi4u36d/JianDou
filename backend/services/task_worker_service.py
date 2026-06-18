"""Task worker and view services.

Translates the Java runtime pipeline services:
- TaskWorkerPipelineHandler
- TaskWorkerRenderStageService
- TaskWorkerStatusStageService
- TaskExecutionRuntimeSupport
- TaskExecutionArtifactAssembler
- JoinOutputService
- TaskViewMapper
"""

from __future__ import annotations

import uuid
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional

from backend.domain.enums import AttemptStatus, TaskStatus, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import TaskQueuePort
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_execution_coordinator import (
    TaskExecutionCoordinator,
    TaskStateTransition,
)
from backend.services.generation_service import DefaultGenerationApplicationService

# ---------------------------------------------------------------------------
# Module-level utility helpers (mirrors Java stringValue/intValue/firstNonBlank)
# ---------------------------------------------------------------------------

_ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(_ISO_FMT)


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _int_value(value: Any, fallback: int = 0) -> int:
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


def _float_value(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    s = _string_value(value).lower()
    return s in ("true", "1", "yes")


def _first_non_blank(*values: str | None) -> str:
    for v in values:
        if v is not None and v.strip():
            return v.strip()
    return ""


def _blank_to_null(value: str) -> str | None:
    s = _string_value(value)
    return None if not s else s


def _first_present(*values: Any) -> Any:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def _map_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _list_map_value(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _nullable_int(value: Any) -> int | None:
    if value is None:
        return None
    return _int_value(value, 0)


def _nullable_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return None


def _file_name_from_url(url: str) -> str:
    normalized = re.sub(r"[?#].*$", "", _string_value(url)).rstrip("/")
    idx = normalized.rfind("/")
    return normalized[idx + 1:] if idx >= 0 else normalized


def _file_ext(file_name: str) -> str:
    normalized = re.sub(r"[?#].*$", "", _string_value(file_name))
    idx = normalized.rfind(".")
    if idx < 0 or idx == len(normalized) - 1:
        return ""
    candidate = normalized[idx + 1:].lower()
    return candidate if re.match(r"^[a-z0-9]{1,10}$", candidate) else ""


def _file_ext_or_default(file_name: str, fallback: str) -> str:
    ext = _file_ext(file_name)
    return ext if ext else fallback


def _stable_id(prefix: str, *parts: str) -> str:
    seed = prefix + ":" + ":".join(parts)
    return prefix + "_" + uuid.uuid5(uuid.NAMESPACE_OID, seed).hex


def _truncate_text(value: str, max_length: int) -> str:
    if not value:
        return ""
    normalized = value.replace("\n", " ").strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length] + "..."


def _duration_millis(started_at: str, finished_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(finished_at)
        return max(0, int((end - start).total_seconds() * 1000))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# TaskWorkerExecutionContext
# ---------------------------------------------------------------------------

class TaskWorkerExecutionContext:
    """Execution context for a single worker run."""

    def __init__(
        self,
        worker_instance_id: str,
        worker_type: str,
        execution_mode: str,
    ) -> None:
        self._worker_instance_id = worker_instance_id
        self._worker_type = worker_type
        self._execution_mode = execution_mode

    @property
    def worker_instance_id(self) -> str:
        return self._worker_instance_id

    @property
    def worker_type(self) -> str:
        return self._worker_type

    @property
    def execution_mode(self) -> str:
        return self._execution_mode


# ---------------------------------------------------------------------------
# TaskStage constants
# ---------------------------------------------------------------------------

class _TaskStage:
    ANALYSIS = "analysis"
    PLANNING = "planning"
    RENDER = "render"
    PIPELINE = "pipeline"
    DISPATCH = "dispatch"
    PAUSED = "paused"


class _TaskResultTypes:
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    VIDEO_JOIN = "video_join"

    @staticmethod
    def is_primary_video(result_type: Any) -> bool:
        rt = _string_value(result_type).lower()
        return rt in ("video", "video_generation")

    @staticmethod
    def is_video(result_type: str) -> bool:
        rt = result_type.lower()
        return rt in ("video", "video_generation", "video_join")

    @staticmethod
    def is_join(result_type: str) -> bool:
        return result_type.lower() == "video_join"


class _GenerationRunKinds:
    SCRIPT = "script"
    IMAGE = "image"
    VIDEO = "video"


class _GenerationRunStatuses:
    @staticmethod
    def is_active(status: str) -> bool:
        return status.lower() in ("pending", "running", "queued", "processing")

    @staticmethod
    def is_successful(status: str) -> bool:
        return status.lower() in ("completed", "success", "succeeded")


class _GenerationModelKinds:
    IMAGE = "image"
    VIDEO = "video"


class _TaskArtifactNaming:
    @staticmethod
    def task_base_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}"

    @staticmethod
    def task_running_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}/running"

    @staticmethod
    def task_joined_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}/joined"

    @staticmethod
    def storyboard_file_name(task: TaskRecord, ext: str) -> str:
        return f"storyboard-{task.id}.{ext}"

    @staticmethod
    def clip_frame_file_name(clip_index: int, frame_role: str, ext: str) -> str:
        return f"clip{clip_index}-{frame_role}.{ext}"

    @staticmethod
    def clip_file_name(clip_index: int, ext: str) -> str:
        return f"clip{clip_index}.{ext}"

    @staticmethod
    def last_frame_file_name(clip_index: int, ext: str) -> str:
        return f"clip{clip_index}-last-frame.{ext}"

    @staticmethod
    def join_name(end_clip_index: int) -> str:
        return f"join-{end_clip_index}"


# ---------------------------------------------------------------------------
# Stub external service interfaces (to be wired via dependency injection)
# ---------------------------------------------------------------------------

class GenerationApplicationServiceStub:
    """Stub for GenerationApplicationService. Replace with real client."""

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"message": "not yet implemented", "id": "", "status": "pending", "result": {}}

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return {"id": run_id, "status": "completed", "result": {}}


class LocalMediaArtifactServiceStub:
    """Stub for LocalMediaArtifactService."""

    class StoredArtifact:
        def __init__(self, public_url: str = "", file_name: str = "", absolute_path: str = "", size_bytes: int = 0) -> None:
            self._public_url = public_url
            self._file_name = file_name
            self._absolute_path = absolute_path
            self._size_bytes = size_bytes

        def public_url(self) -> str: ...
        def file_name(self) -> str: ...
        def absolute_path(self) -> str: ...
        def size_bytes(self) -> int: ...

    def materialize_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> StoredArtifact: ...
    def copy_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> StoredArtifact: ...
    def concat_videos(self, relative_dir: str, output_file_name: str, segment_urls: list[str]) -> StoredArtifact: ...
    def build_externally_accessible_url(self, local_path: str) -> str: ...
    def image_data_uri_from_public_url(self, public_url: str) -> str: ...
    def ensure_media_thumbnail(self, media_type: str, public_url: str, candidate_image_urls: list[str], max_width: int) -> str: ...
    def resolve_absolute_path(self, file_url: str) -> str: ...


class TaskStoryboardPlannerStub:
    """Stub for TaskStoryboardPlanner."""

    class StoryboardShotPlan:
        def __init__(self, *, sequential_index: int = 1, shot_label: str = "", scene: str = "",
                     video_prompt: str = "", image_prompt: str = "", first_frame_prompt: str = "",
                     last_frame_prompt: str = "", motion: str = "", camera_movement: str = "",
                     duration_hint: str = "") -> None:
            self._sequential_index = sequential_index
            self._shot_label = shot_label
            self._scene = scene
            self._video_prompt = video_prompt
            self._image_prompt = image_prompt
            self._first_frame_prompt = first_frame_prompt
            self._last_frame_prompt = last_frame_prompt
            self._motion = motion
            self._camera_movement = camera_movement
            self._duration_hint = duration_hint

        def sequential_index(self) -> int: return self._sequential_index
        def shot_label(self) -> str: return self._shot_label
        def scene(self) -> str: return self._scene
        def video_prompt(self) -> str: return self._video_prompt
        def image_prompt(self) -> str: return self._image_prompt
        def first_frame_prompt(self) -> str: return self._first_frame_prompt
        def last_frame_prompt(self) -> str: return self._last_frame_prompt
        def motion(self) -> str: return self._motion
        def camera_movement(self) -> str: return self._camera_movement
        def duration_hint(self) -> str: return self._duration_hint

    def build_storyboard_shot_plans(self, task: TaskRecord, storyboard_markdown: str) -> list[StoryboardShotPlan]:
        return []

    def resolve_requested_output_count(self, task: TaskRecord, storyboard_clip_count: int) -> int:
        return storyboard_clip_count

    def extract_storyboard_shot_duration_ranges(self, storyboard_markdown: str) -> list[list[int]]:
        return []

    def build_clip_duration_plan(self, task: TaskRecord, duration_seconds: int, clip_count: int, storyboard_markdown: str) -> list[list[int]]:
        return [[duration_seconds, duration_seconds, duration_seconds]] * clip_count

    def normalize_clip_duration_plan(self, video_model: str, clip_duration_plan: list[list[int]]) -> list[list[int]]:
        return clip_duration_plan

    def request_snapshot_output_count(self, task: TaskRecord) -> int:
        return 0

    def build_clip_duration_plan_context(self, clip_duration_plan: list[list[int]], duration_ranges: list[list[int]]) -> list[dict[str, Any]]:
        return []


class ModelRuntimePropertiesResolverStub:
    """Stub for model runtime properties resolver."""

    def int_value(self, *keys: str, default: int = 0) -> int:
        return default

    def value(self, *keys: str, default: str = "") -> str:
        return default

    def supports_seed(self, model: str) -> bool:
        return False


class TaskExecutionAbortedException(Exception):
    """Raised when task execution is aborted (paused, cancelled, etc.)."""

    def __init__(self, task_status: str, message: str = "") -> None:
        super().__init__(message)
        self._task_status = task_status

    @property
    def task_status(self) -> str:
        return self._task_status


class GenerationProviderException(Exception):
    """Raised when a generation provider returns an error."""

    def __init__(self, message: str = "", http_status: int = 0, provider_request: Any = None, provider_response: Any = None) -> None:
        super().__init__(message)
        self._http_status = http_status
        self._provider_request = provider_request
        self._provider_response = provider_response

    @property
    def http_status(self) -> int:
        return self._http_status

    @property
    def provider_request(self) -> Any:
        return self._provider_request

    @property
    def provider_response(self) -> Any:
        return self._provider_response


# ===================================================================
# TaskExecutionRuntimeSupport
# ===================================================================

class TaskExecutionRuntimeSupport:
    """Runtime utilities for task execution: dimensions, duration, request building."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        model_resolver: ModelRuntimePropertiesResolverStub | None = None,
        local_media_artifact_service: LocalMediaArtifactServiceStub | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._model_resolver = model_resolver or ModelRuntimePropertiesResolverStub()
        self._local_media_artifact_service = local_media_artifact_service

    def active_attempt(self, task: TaskRecord) -> dict[str, Any] | None:
        if not task.active_attempt_id:
            return None
        for row in task.attempts:
            if task.active_attempt_id == _string_value(row.get("attemptId", "")):
                return row
        return None

    def resolve_dimensions(self, task: TaskRecord) -> list[int]:
        snapshot = task.request_snapshot or {}
        image_size = _string_value(snapshot.get("imageSize", ""))
        if image_size:
            parsed = self._parse_dimensions(image_size)
            if parsed:
                return parsed
        video_size = _string_value(snapshot.get("videoSize", ""))
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
        raise TaskExecutionAbortedException(task.status, _first_non_blank(task.error_message, "任务已停止执行。"))

    def build_script_run_request(self, task: TaskRecord) -> dict[str, Any]:
        source_text = _first_non_blank(
            task.transcript_text,
            task.creative_prompt,
            task.title,
        )
        request: dict[str, Any] = {
            "kind": _GenerationRunKinds.SCRIPT,
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
            compatible = self._compatible_image_reference_urls(reference_image_url, image_model)
            if compatible:
                input_data["referenceImageUrl"] = compatible[0]
                input_data["referenceImageUrls"] = compatible
        request: dict[str, Any] = {
            "kind": _GenerationRunKinds.IMAGE,
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
                "relatedTaskId": _string_value(task.id),
                "clipIndex": max(1, clip_index),
                "frameRole": normalized_frame_role,
            },
        }
        self._put_user_auth(request, task)
        return dict(request)

    def build_workspace_image_run_request(self, task: TaskRecord, width: int, height: int) -> dict[str, Any]:
        snapshot = task.request_snapshot or {}
        asset_type = _string_value(snapshot.get("assetType", ""))
        if not asset_type:
            asset_type = "character_sheet" if task.task_type == "character_sheet" else "free"
        prompt = _first_non_blank(
            _string_value(snapshot.get("creativePrompt", "")),
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
        compatible = self._compatible_image_reference_urls(reference_urls, image_model)
        if compatible:
            input_data["referenceImageUrl"] = compatible[0]
            input_data["referenceImageUrls"] = compatible
        image_seed = self._task_seed(task)
        if image_seed is not None and self._model_resolver.supports_seed(image_model):
            input_data["seed"] = image_seed
        request: dict[str, Any] = {
            "kind": _GenerationRunKinds.IMAGE,
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
                "relatedTaskId": _string_value(task.id),
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
            "kind": _GenerationRunKinds.VIDEO,
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
                "relatedTaskId": _string_value(task.id),
                "clipIndex": max(1, clip_index),
            },
        }
        self._put_user_auth(request, task)
        return dict(request)

    # ---- Private helpers ----

    def _parse_dimensions(self, value: str) -> list[int] | None:
        normalized = _string_value(value).lower().replace("x", "*")
        parts = normalized.split("*")
        if len(parts) != 2:
            return None
        try:
            w = int(parts[0].strip())
            h = int(parts[1].strip())
            return [w, h] if w > 0 and h > 0 else None
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
        configured = _string_value(snapshot.get(field_name, ""))
        if configured:
            return configured
        raise ValueError(f"任务缺少必选模型：{label}（{field_name}）")

    def _style_preset(self, task: TaskRecord) -> str:
        snapshot = task.request_snapshot or {}
        configured = _string_value(snapshot.get("stylePreset", ""))
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
        task_identity = _first_non_blank(
            task.id,
            task.title,
            task.creative_prompt,
            "task",
        )
        seed_source = f"{task_identity}:clip:{max(1, clip_index)}:keyframe"
        raw = uuid.uuid5(uuid.NAMESPACE_OID, seed_source).int >> 64
        return (raw % (2**31 - 2)) + 1

    def _normalize_frame_role(self, frame_role: str) -> str:
        return "last" if frame_role.lower() == "last" else "first"

    def _compatible_image_reference_urls(self, reference_image_url: str, image_model: str) -> list[str]:
        normalized = _string_value(reference_image_url)
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

    def _compatible_image_reference_urls(self, urls: list[str], image_model: str) -> list[str]:
        resolved: list[str] = []
        for url in urls:
            for item in self._compatible_image_reference_urls(url, image_model):
                if item and item not in resolved:
                    resolved.append(item)
        return resolved

    def _reference_image_urls(self, task: TaskRecord) -> list[str]:
        ctx = task.execution_context or {}
        raw = ctx.get("referenceImageUrls")
        if isinstance(raw, list):
            values: list[str] = []
            for item in raw:
                normalized = _string_value(item)
                if normalized and normalized not in values:
                    values.append(normalized)
            return values
        return []

    def _supports_image_data_uri_references(self, image_model: str) -> bool:
        lower = _string_value(image_model).lower()
        return "gpt-image" in lower or "seedream" in lower

    def _build_workspace_image_prompt(self, asset_type: str, title: str, description: str, has_references: bool) -> str:
        normalized_asset_type = _string_value(asset_type)
        normalized_description = _string_value(description)
        if normalized_asset_type in ("free", ""):
            return normalized_description
        parts: list[str] = []
        parts.append(f"素材标题：{_first_non_blank(title, '工作台图片生成')}")
        parts.append(f"素材描述：{normalized_description}")
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


# ===================================================================
# TaskExecutionArtifactAssembler
# ===================================================================

class TaskExecutionArtifactAssembler:
    """Assembles execution artifacts (materials, results) from task data."""

    def __init__(self, local_media_artifact_service: LocalMediaArtifactServiceStub | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service

    def create_text_material(self, task: TaskRecord, run: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        file_url = _string_value(result.get("markdownUrl", ""))
        artifact = self._normalize_task_artifact(
            task, file_url,
            _TaskArtifactNaming.storyboard_file_name(task, _file_ext_or_default(_file_name_from_url(file_url), "md")),
            "storyboard",
        )
        return self._create_material(
            task, run,
            _TaskResultTypes.TEXT,
            f"{task.title} 分镜脚本",
            artifact.public_url() if hasattr(artifact, 'public_url') else file_url,
            artifact.public_url() if hasattr(artifact, 'public_url') else file_url,
            _string_value(result.get("mimeType", "text/markdown")),
            0.0, 0, 0, False, 1, "storyboard",
            {}, {"taskArtifact": True}, "",
        )

    def create_image_material(self, task: TaskRecord, run: dict[str, Any], result: dict[str, Any], clip_index: int, frame_role: str) -> dict[str, Any]:
        output_url = _string_value(result.get("outputUrl", ""))
        metadata = _map_value(result.get("metadata"))
        normalized_frame_role = "last" if frame_role.lower() == "last" else "first"
        artifact = self._normalize_task_artifact(
            task, output_url,
            _TaskArtifactNaming.clip_frame_file_name(clip_index, normalized_frame_role, _file_ext_or_default(_file_name_from_url(output_url), "png")),
            "keyframe",
        )
        return self._create_material(
            task, run,
            _TaskResultTypes.IMAGE,
            f"{task.title} {'尾帧关键画面' if normalized_frame_role == 'last' else '首帧关键画面'}",
            artifact.public_url() if hasattr(artifact, 'public_url') else output_url,
            artifact.public_url() if hasattr(artifact, 'public_url') else output_url,
            _string_value(result.get("mimeType", "image/png")),
            0.0,
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            False, clip_index, f"keyframe-{normalized_frame_role}",
            metadata,
            {"taskArtifact": True, "clipIndex": clip_index, "frameRole": normalized_frame_role, "remoteSourceUrl": _string_value(metadata.get("remoteSourceUrl"))},
            _string_value(metadata.get("remoteSourceUrl")),
        )

    def create_workspace_image_material(self, task: TaskRecord, run: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        metadata = _map_value(result.get("metadata"))
        output_url = self._image_output_url(result, metadata)
        artifact = self._normalize_task_artifact(
            task, output_url,
            f"workspace-image-{task.id}.{_file_ext_or_default(_file_name_from_url(output_url), 'png')}",
            "keyframe",
        )
        snapshot = task.request_snapshot or {}
        asset_type = _string_value(snapshot.get("assetType", ""))
        if not asset_type:
            asset_type = _string_value(task.task_type)
        return self._create_material(
            task, run,
            _TaskResultTypes.IMAGE,
            task.title,
            artifact.public_url() if hasattr(artifact, 'public_url') else output_url,
            artifact.public_url() if hasattr(artifact, 'public_url') else output_url,
            _string_value(result.get("mimeType", "image/png")),
            0.0,
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            False, 1, asset_type if asset_type else "free",
            metadata,
            {"taskArtifact": True, "assetType": asset_type, "taskType": task.task_type, "remoteSourceUrl": _string_value(metadata.get("remoteSourceUrl"))},
            _string_value(metadata.get("remoteSourceUrl")),
        )

    def create_reference_frame_material(self, task: TaskRecord, clip_index: int, source_url: str, frame_role: str) -> dict[str, Any]:
        normalized_frame_role = "last" if frame_role.lower() == "last" else "first"
        target_file_name = _TaskArtifactNaming.clip_frame_file_name(clip_index, normalized_frame_role, _file_ext_or_default(_file_name_from_url(source_url), "png"))
        file_url = _string_value(source_url)
        try:
            artifact = self._normalize_task_artifact(task, source_url, target_file_name, "keyframe")
            file_url = artifact.public_url() if hasattr(artifact, 'public_url') else file_url
        except Exception:
            pass
        return self._create_material(
            task, {},
            _TaskResultTypes.IMAGE,
            f"{task.title} {'尾帧关键画面' if normalized_frame_role == 'last' else '首帧关键画面'}",
            file_url, file_url,
            self._image_mime_type(target_file_name),
            0.0, 0, 0, False, clip_index, f"keyframe-{normalized_frame_role}",
            {},
            {"taskArtifact": file_url.startswith("/storage/"), "clipIndex": clip_index, "frameRole": normalized_frame_role, "remoteSourceUrl": _string_value(source_url), "reusedFromPreviousClip": True},
            _string_value(source_url),
        )

    def create_video_material(self, task: TaskRecord, run: dict[str, Any], result: dict[str, Any], clip_index: int, fallback_duration_seconds: int) -> dict[str, Any]:
        metadata = _map_value(result.get("metadata"))
        output_url = _first_non_blank(
            _string_value(result.get("outputUrl")),
            _string_value(metadata.get("outputUrl")),
            _string_value(metadata.get("fileUrl")),
            _string_value(metadata.get("remoteSourceUrl")),
        )
        artifact = self._normalize_task_artifact(
            task, output_url,
            _TaskArtifactNaming.clip_file_name(clip_index, _file_ext_or_default(_file_name_from_url(output_url), "mp4")),
            "clip",
        )
        return self._create_material(
            task, run,
            _TaskResultTypes.VIDEO,
            f"{task.title} 片段输出",
            artifact.public_url() if hasattr(artifact, 'public_url') else output_url,
            artifact.public_url() if hasattr(artifact, 'public_url') else output_url,
            _string_value(result.get("mimeType", "video/mp4")),
            _float_value(result.get("durationSeconds"), float(fallback_duration_seconds)),
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            _bool_value(result.get("hasAudio")),
            clip_index, "clip",
            metadata,
            {"taskArtifact": True, "clipIndex": clip_index, "firstFrameUrl": _string_value(metadata.get("firstFrameUrl")), "lastFrameUrl": self.extract_last_frame_url(result), "requestedLastFrameUrl": _string_value(metadata.get("requestedLastFrameUrl")), "remoteSourceUrl": _string_value(metadata.get("remoteSourceUrl"))},
            _string_value(metadata.get("remoteSourceUrl")),
        )

    def create_result(
        self,
        task: TaskRecord,
        video_run: dict[str, Any],
        video_result: dict[str, Any],
        video_material: dict[str, Any],
        image_material: dict[str, Any],
        video_model_call: dict[str, Any],
        resolved_last_frame_url: str,
        clip_index: int,
        fallback_duration_seconds: int,
        min_duration_seconds: int,
        max_duration_seconds: int,
    ) -> dict[str, Any]:
        video_metadata = _map_value(video_result.get("metadata"))
        row: dict[str, Any] = {
            "id": _stable_id("result", task.id, _TaskResultTypes.VIDEO, str(clip_index)),
            "resultType": _TaskResultTypes.VIDEO,
            "clipIndex": clip_index,
            "title": f"{task.title} 成片输出 #{clip_index}",
            "reason": "Spring Boot worker 已按分镜顺序完成视频片段输出。",
            "sourceModelCallId": _string_value(video_model_call.get("modelCallId")),
            "materialAssetId": video_material.get("id"),
            "startSeconds": 0.0,
            "endSeconds": _float_value(video_result.get("durationSeconds"), float(fallback_duration_seconds)),
            "durationSeconds": _float_value(video_result.get("durationSeconds"), float(fallback_duration_seconds)),
            "previewUrl": _string_value(video_material.get("previewUrl")),
            "downloadUrl": _string_value(video_material.get("fileUrl")),
            "mimeType": _string_value(video_result.get("mimeType", "video/mp4")),
            "width": _int_value(video_result.get("width"), 0),
            "height": _int_value(video_result.get("height"), 0),
            "sizeBytes": self._file_size(self._resolve_absolute_path(_string_value(video_material.get("fileUrl")))),
            "remoteUrl": _string_value(video_metadata.get("remoteSourceUrl")),
            "extra": {
                "runId": _string_value(video_run.get("id")),
                "posterUrl": _string_value(image_material.get("fileUrl")),
                "thumbnailUrl": _string_value(video_result.get("thumbnailUrl")),
                "hasAudio": _bool_value(video_result.get("hasAudio")),
                "clipIndex": clip_index,
                "targetDurationSeconds": fallback_duration_seconds,
                "minDurationSeconds": min_duration_seconds,
                "maxDurationSeconds": max_duration_seconds,
                "requestedDurationSeconds": fallback_duration_seconds,
                "appliedDurationSeconds": _float_value(video_result.get("durationSeconds"), float(fallback_duration_seconds)),
                "remoteTaskId": _string_value(video_metadata.get("taskId")),
                "firstFrameUrl": _first_non_blank(_string_value(video_metadata.get("firstFrameUrl")), _string_value(image_material.get("remoteUrl"))),
                "lastFrameUrl": resolved_last_frame_url,
                "requestedLastFrameUrl": _string_value(video_metadata.get("requestedLastFrameUrl")),
            },
            "createdAt": _now_iso(),
        }
        return row

    def create_image_result(
        self,
        task: TaskRecord,
        image_run: dict[str, Any],
        image_result: dict[str, Any],
        image_material: dict[str, Any],
        model_call: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = _map_value(image_result.get("metadata"))
        snapshot = task.request_snapshot or {}
        row: dict[str, Any] = {
            "id": _stable_id("result", task.id, _TaskResultTypes.IMAGE, "1"),
            "resultType": _TaskResultTypes.IMAGE,
            "clipIndex": 1,
            "title": task.title,
            "reason": "工作台图片生成已完成。",
            "sourceModelCallId": _string_value(model_call.get("modelCallId")),
            "materialAssetId": image_material.get("id"),
            "startSeconds": 0.0,
            "endSeconds": 0.0,
            "durationSeconds": 0.0,
            "previewUrl": _string_value(image_material.get("previewUrl")),
            "downloadUrl": _string_value(image_material.get("fileUrl")),
            "mimeType": _string_value(image_result.get("mimeType", "image/png")),
            "width": _int_value(image_result.get("width"), 0),
            "height": _int_value(image_result.get("height"), 0),
            "sizeBytes": self._file_size(self._resolve_absolute_path(_string_value(image_material.get("fileUrl")))),
            "remoteUrl": _string_value(metadata.get("remoteSourceUrl")),
            "extra": {
                "runId": _string_value(image_run.get("id")),
                "assetType": _string_value(snapshot.get("assetType", "")),
                "taskType": task.task_type,
                "referenceImageUrls": metadata.get("referenceImageUrls", []),
            },
            "createdAt": _now_iso(),
        }
        return row

    def normalize_optional_task_artifact(self, task: TaskRecord, source_url: str, target_file_name: str) -> None:
        if not _string_value(source_url) or not _string_value(target_file_name):
            return
        if self._local_media_artifact_service:
            try:
                self._local_media_artifact_service.materialize_artifact(
                    source_url, _TaskArtifactNaming.task_running_relative_dir(task), target_file_name,
                )
            except Exception:
                pass

    def extract_last_frame_url(self, value: Any) -> str:
        direct = self._find_nested_string(value, "lastFrameUrl", "last_frame_url")
        if direct:
            return direct
        return self._find_nested_role_url(value, "last_frame")

    # ---- Private helpers ----

    def _image_output_url(self, result: dict[str, Any], metadata: dict[str, Any]) -> str:
        return _first_non_blank(
            _string_value(result.get("outputUrl")),
            _string_value(metadata.get("outputUrl")),
            _string_value(metadata.get("fileUrl")),
            _string_value(metadata.get("remoteSourceUrl")),
        )

    def _image_mime_type(self, file_name: str) -> str:
        ext = _file_ext(file_name)
        if ext in ("jpg", "jpeg"):
            return "image/jpeg"
        if ext == "webp":
            return "image/webp"
        return "image/png"

    def _normalize_task_artifact(self, task: TaskRecord, source_url: str, target_file_name: str, fallback_kind: str) -> Any:
        resolved = _string_value(target_file_name)
        if not resolved:
            if fallback_kind == "storyboard":
                resolved = _TaskArtifactNaming.storyboard_file_name(task, "bin")
            elif fallback_kind == "keyframe":
                resolved = _TaskArtifactNaming.clip_frame_file_name(1, "first", "bin")
            else:
                resolved = _TaskArtifactNaming.clip_file_name(1, "bin")
        if self._local_media_artifact_service:
            return self._local_media_artifact_service.materialize_artifact(
                source_url, _TaskArtifactNaming.task_running_relative_dir(task), resolved,
            )
        return LocalMediaArtifactServiceStub.StoredArtifact(public_url=source_url)

    def _create_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        media_type: str,
        title: str,
        file_url: str,
        preview_url: str,
        mime_type: str,
        duration_seconds: float,
        width: int,
        height: int,
        has_audio: bool,
        clip_index: int,
        kind: str,
        source_metadata: dict[str, Any],
        extra_metadata: dict[str, Any],
        remote_url: str,
    ) -> dict[str, Any]:
        run_result = _map_value(run.get("result"))
        model_info = _map_value(run_result.get("modelInfo"))
        absolute_path = self._resolve_absolute_path(file_url) if file_url else ""
        file_name = _file_name_from_url(file_url) if file_url else ""
        metadata: dict[str, Any] = {
            "taskId": task.id,
            "kind": kind,
            "clipIndex": clip_index,
            "runId": _string_value(run.get("id")),
            "sourceMetadata": source_metadata if source_metadata else {},
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        thumbnail_url = self._media_thumbnail_url(media_type, file_url, metadata)
        row: dict[str, Any] = {
            "id": _stable_id("asset", task.id, kind, str(clip_index)),
            "ownerUserId": task.owner_user_id,
            "kind": kind,
            "mediaType": media_type,
            "title": title,
            "originProvider": _string_value(model_info.get("provider", "spring-placeholder")),
            "originModel": _string_value(model_info.get("resolvedModel", model_info.get("providerModel"))),
            "remoteTaskId": _first_non_blank(_string_value(source_metadata.get("taskId")), _string_value(run.get("id"))),
            "remoteAssetId": "",
            "originalFileName": file_name,
            "storedFileName": file_name,
            "fileExt": _file_ext(file_name),
            "storageProvider": "local",
            "mimeType": mime_type,
            "sizeBytes": self._file_size(absolute_path) if absolute_path else 0,
            "durationSeconds": duration_seconds,
            "width": width,
            "height": height,
            "hasAudio": has_audio,
            "storagePath": absolute_path,
            "localFilePath": absolute_path,
            "fileUrl": file_url or "",
            "previewUrl": preview_url or "",
            "thumbnailUrl": thumbnail_url or "",
            "remoteUrl": remote_url or "",
            "metadata": metadata,
            "createdAt": _now_iso(),
        }
        return row

    def _media_thumbnail_url(self, media_type: str, file_url: str, metadata: dict[str, Any]) -> str:
        candidate = _first_non_blank(
            _string_value(metadata.get("thumbnailUrl")),
            _string_value(metadata.get("posterUrl")),
            _string_value(metadata.get("firstFrameUrl")),
            _string_value(metadata.get("startFrameUrl")),
        )
        if self._local_media_artifact_service:
            return _string_value(self._local_media_artifact_service.ensure_media_thumbnail(
                media_type, file_url, [candidate] if candidate else [], 480,
            ))
        return candidate or ""

    def _file_size(self, absolute_path: str) -> int:
        if not absolute_path:
            return 0
        import os
        try:
            return os.path.getsize(absolute_path) if os.path.exists(absolute_path) else 0
        except OSError:
            return 0

    def _resolve_absolute_path(self, file_url: str) -> str:
        if self._local_media_artifact_service:
            return self._local_media_artifact_service.resolve_absolute_path(file_url)
        return file_url

    def _find_nested_string(self, value: Any, *keys: str) -> str:
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
                if isinstance(candidate, dict):
                    nested = self._find_nested_string(candidate, "url", "href", "uri")
                    if nested:
                        return nested
            for nested in value.values():
                resolved = self._find_nested_string(nested, *keys)
                if resolved:
                    return resolved
        if isinstance(value, list):
            for item in value:
                resolved = self._find_nested_string(item, *keys)
                if resolved:
                    return resolved
        return ""

    def _find_nested_role_url(self, value: Any, role: str) -> str:
        if isinstance(value, dict):
            current_role = _string_value(value.get("role")).lower()
            if role == current_role:
                image_url = value.get("image_url") or value.get("imageUrl")
                resolved = self._find_nested_string(image_url, "url", "href", "uri")
                if resolved:
                    return resolved
            for nested in value.values():
                resolved = self._find_nested_role_url(nested, role)
                if resolved:
                    return resolved
        if isinstance(value, list):
            for item in value:
                resolved = self._find_nested_role_url(item, role)
                if resolved:
                    return resolved
        return ""


# ===================================================================
# TaskWorkerStatusStageService
# ===================================================================

class TaskWorkerStatusStageService:
    """Service for tracking status, model calls, stage runs, and lifecycle events."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        task_queue_port: TaskQueuePort | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._task_queue_port = task_queue_port
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()

    def update_status(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
    ) -> dict[str, Any]:
        self._assert_task_still_active(task)
        return self._execution_coordinator.transition_task(
            task,
            TaskStateTransition.info(
                next_status,
                progress,
                stage,
                event,
                message,
                {"workerInstanceId": run_context.worker_instance_id},
            ),
        )

    def record_stage_run(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        seq: int,
        stage_name: str,
        clip_index: int,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
    ) -> dict[str, Any]:
        now = _now_iso()
        row: dict[str, Any] = {
            "stageRunId": _stable_id("stgrun", task.id, stage_name, str(clip_index)),
            "attemptId": task.active_attempt_id,
            "stageName": stage_name,
            "stageSeq": seq,
            "clipIndex": clip_index,
            "status": "COMPLETED",
            "workerInstanceId": run_context.worker_instance_id,
            "startedAt": now,
            "finishedAt": now,
            "durationMs": 0,
            "inputSummary": input_summary,
            "outputSummary": output_summary,
            "errorCode": "",
            "errorMessage": "",
        }
        return self._execution_coordinator.record_stage_run(task, row)

    def create_pending_model_call(
        self,
        task: TaskRecord,
        stage: str,
        operation: str,
        request_payload: dict[str, Any],
        clip_index: int,
        kind: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        model_section = _map_value(request_payload.get("model"))
        provider_model = _first_non_blank(
            _string_value(model_section.get("providerModel")),
            _string_value(model_section.get("textAnalysisModel")),
        )
        row: dict[str, Any] = {
            "modelCallId": _stable_id("mdlcall", task.id, stage, kind, str(clip_index)),
            "requestLogId": "reqlog_" + _stable_id("mdlcall", task.id, stage, kind, str(clip_index)),
            "callKind": stage,
            "stage": stage,
            "operation": operation,
            "provider": "generation",
            "providerModel": provider_model,
            "requestedModel": provider_model,
            "resolvedModel": "",
            "modelName": "",
            "modelAlias": provider_model,
            "endpointHost": "",
            "requestId": "",
            "requestPayload": request_payload,
            "responsePayload": {},
            "httpStatus": 0,
            "responseCode": 0,
            "success": False,
            "status": "pending",
            "errorCode": "",
            "errorMessage": "",
            "latencyMs": 0,
            "durationMs": 0,
            "inputTokens": 0,
            "outputTokens": 0,
            "startedAt": now,
            "finishedAt": now,
        }
        return row

    def complete_model_call(self, pending_model_call: dict[str, Any], run: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        row = dict(pending_model_call or {})
        model_info = _map_value(result.get("modelInfo"))
        started_at = _string_value(row.get("startedAt"))
        finished_at = _string_value(run.get("updatedAt", _now_iso()))
        row["provider"] = _string_value(model_info.get("provider", row.get("provider")))
        row["providerModel"] = _first_non_blank(_string_value(model_info.get("providerModel")), _string_value(row.get("providerModel")))
        row["requestedModel"] = _first_non_blank(_string_value(model_info.get("requestedModel")), _string_value(row.get("requestedModel")))
        row["resolvedModel"] = _string_value(model_info.get("resolvedModel"))
        row["modelName"] = _string_value(model_info.get("modelName", model_info.get("resolvedModel")))
        row["modelAlias"] = _string_value(model_info.get("modelName", model_info.get("resolvedModel")))
        row["endpointHost"] = _string_value(model_info.get("endpointHost"))
        row["requestId"] = _string_value(run.get("id"))
        row["responsePayload"] = {"runId": _string_value(run.get("id")), "result": result}
        row["httpStatus"] = 200
        row["responseCode"] = 200
        row["success"] = True
        row["status"] = "success"
        row["errorCode"] = ""
        row["errorMessage"] = ""
        row["latencyMs"] = 0
        row["durationMs"] = _duration_millis(started_at, finished_at)
        row["finishedAt"] = finished_at
        return row

    def fail_model_call(self, pending_model_call: dict[str, Any], error: Exception) -> dict[str, Any]:
        row = dict(pending_model_call or {})
        started_at = _string_value(row.get("startedAt"))
        finished_at = _now_iso()
        http_status = error.http_status if isinstance(error, GenerationProviderException) else 0
        response_payload: dict[str, Any] = {
            "errorType": error.__class__.__name__ if error else "",
            "errorMessage": _first_non_blank(str(error) if error else "", "unknown"),
        }
        if isinstance(error, GenerationProviderException):
            response_payload["providerRequest"] = error.provider_request
            response_payload["providerResponse"] = error.provider_response
            response_payload["httpStatus"] = error.http_status
        row["responsePayload"] = response_payload
        row["httpStatus"] = max(0, http_status)
        row["responseCode"] = max(0, http_status)
        row["success"] = False
        row["status"] = "failed"
        row["errorCode"] = error.__class__.__name__ if error else ""
        row["errorMessage"] = _first_non_blank(str(error) if error else "", "unknown")
        row["durationMs"] = _duration_millis(started_at, finished_at)
        row["finishedAt"] = finished_at
        return row

    def record_run_call_chain(self, task: TaskRecord, fallback_stage: str, run: dict[str, Any], result: dict[str, Any]) -> None:
        raw = result.get("callChain")
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, dict):
                continue
            stage = _string_value(item.get("stage"))
            event = _string_value(item.get("event"))
            message = _string_value(item.get("message"))
            status = _string_value(item.get("status"))
            level = "INFO" if status.lower() == "success" else "WARN"
            self._execution_coordinator.record_trace(
                task,
                stage if stage else fallback_stage,
                event if event else "generation.call",
                message if message else "generation run completed",
                level,
                {"runId": _string_value(run.get("id")), "status": status, "details": _map_value(item.get("details"))},
            )

    def complete_task(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        script_run: dict[str, Any],
        image_run_ids: list[str],
        video_run_ids: list[str],
        clip_count: int,
        latest_video_output_url: str,
    ) -> dict[str, Any]:
        self._assert_task_still_active(task)
        result = self._execution_coordinator.transition_task(
            task,
            TaskStateTransition.info(
                "COMPLETED",
                100,
                _TaskStage.PIPELINE,
                "task.completed",
                "Spring worker 已通过 generation 服务完成分镜视频生成。",
                {
                    "scriptRunId": _string_value(script_run.get("id")),
                    "imageRunIds": image_run_ids,
                    "videoRunIds": video_run_ids,
                    "clipCount": clip_count,
                    "outputUrl": latest_video_output_url,
                },
            ).with_attempt(AttemptStatus.FINISHED.value, ""),
        )
        self._execution_coordinator.touch_worker_instance(
            run_context.worker_instance_id,
            run_context.worker_type,
            WorkerStatus.RUNNING.value,
            {"lastTaskId": task.id, "lastTaskStatus": "COMPLETED"},
        )
        return result

    def complete_workspace_image_task(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        image_run: dict[str, Any],
        output_url: str,
    ) -> dict[str, Any]:
        self._assert_task_still_active(task)
        result = self._execution_coordinator.transition_task(
            task,
            TaskStateTransition.info(
                "COMPLETED",
                100,
                _TaskStage.PIPELINE,
                "task.completed",
                "Spring worker 已完成工作台图片生成。",
                {
                    "imageRunId": _string_value(image_run.get("id")),
                    "outputUrl": output_url,
                    "taskType": task.task_type,
                },
            ).with_attempt(AttemptStatus.FINISHED.value, ""),
        )
        self._execution_coordinator.touch_worker_instance(
            run_context.worker_instance_id,
            run_context.worker_type,
            WorkerStatus.RUNNING.value,
            {"lastTaskId": task.id, "lastTaskStatus": "COMPLETED"},
        )
        return result

    def handle_abort(self, task: TaskRecord, run_context: TaskWorkerExecutionContext, task_status: str) -> dict[str, Any]:
        return self._execution_coordinator.touch_worker_instance(
            run_context.worker_instance_id,
            run_context.worker_type,
            WorkerStatus.RUNNING.value,
            {"lastTaskId": task.id, "lastTaskStatus": task_status},
        )

    def fail_task(self, task: TaskRecord, run_context: TaskWorkerExecutionContext, ex: Exception) -> None:
        try:
            if self._task_queue_port:
                self._task_queue_port.remove(task.id)
            task.is_queued = False
            task.queue_position = None
            error_message = str(ex) if ex else "Spring worker 执行失败"
            self._execution_coordinator.transition_task(
                task,
                TaskStateTransition.error(
                    "FAILED",
                    task.progress,
                    _TaskStage.PIPELINE,
                    "task.failed",
                    "Spring worker 执行失败。",
                    {"error": error_message},
                ).with_attempt(AttemptStatus.FAILED.value, error_message),
            )
            self._execution_coordinator.touch_worker_instance(
                run_context.worker_instance_id,
                run_context.worker_type,
                WorkerStatus.RUNNING.value,
                {"lastTaskId": task.id, "lastTaskStatus": "FAILED"},
            )
        except Exception:
            self._execution_coordinator.touch_worker_instance(
                run_context.worker_instance_id,
                run_context.worker_type,
                WorkerStatus.FAILED.value,
                {"executionMode": run_context.execution_mode},
            )

    def _assert_task_still_active(self, task: TaskRecord) -> None:
        if self._task_repository is None:
            return
        if TaskStatus.is_execution_active(TaskStatus(task.status) if TaskStatus(task.status) else None):
            return
        raise TaskExecutionAbortedException(
            task.status,
            _first_non_blank(task.error_message, "任务已停止执行。"),
        )


# ===================================================================
# TaskWorkerRenderStageService
# ===================================================================

class TaskWorkerRenderStageService:
    """Handles the render stage of task execution — keyframe generation and clip rendering."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        generation_application_service: GenerationApplicationServiceStub | None = None,
        runtime_support: TaskExecutionRuntimeSupport | None = None,
        artifact_assembler: TaskExecutionArtifactAssembler | None = None,
        status_stage_service: TaskWorkerStatusStageService | None = None,
        join_stage_service: Optional[JoinOutputService] = None,
        video_run_poll_interval_ms: int = 1000,
        video_run_max_polls: int = 240,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        self._generation_application_service = generation_application_service or DefaultGenerationApplicationService()
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler()
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository, execution_coordinator=self._execution_coordinator,
        )
        self._join_stage_service = join_stage_service
        self._video_run_poll_interval_ms = max(0, video_run_poll_interval_ms)
        self._video_run_max_polls = max(1, video_run_max_polls)

    class RenderStageRequest:
        def __init__(
            self,
            reuse_storyboard: bool = False,
            render_start_index: int = 1,
            completed_clip_count: int = 0,
            requested_resume_stage: str = "",
            requested_resume_clip_index: int = 0,
            existing_video_clip_indices: list[int] | None = None,
            shot_plans: list | None = None,
            clip_duration_plan: list[list[int]] | None = None,
            width: int = 0,
            height: int = 0,
            duration_seconds: int = 0,
            video_size: str = "",
            previous_clip_last_frame_url: str = "",
        ) -> None:
            self._reuse_storyboard = reuse_storyboard
            self._render_start_index = render_start_index
            self._completed_clip_count = completed_clip_count
            self._requested_resume_stage = requested_resume_stage
            self._requested_resume_clip_index = requested_resume_clip_index
            self._existing_video_clip_indices = existing_video_clip_indices or []
            self._shot_plans = shot_plans or []
            self._clip_duration_plan = clip_duration_plan or []
            self._width = width
            self._height = height
            self._duration_seconds = duration_seconds
            self._video_size = video_size
            self._previous_clip_last_frame_url = previous_clip_last_frame_url

        @property
        def reuse_storyboard(self) -> bool: return self._reuse_storyboard
        @property
        def render_start_index(self) -> int: return self._render_start_index
        @property
        def completed_clip_count(self) -> int: return self._completed_clip_count
        @property
        def requested_resume_stage(self) -> str: return self._requested_resume_stage
        @property
        def requested_resume_clip_index(self) -> int: return self._requested_resume_clip_index
        @property
        def existing_video_clip_indices(self) -> list[int]: return self._existing_video_clip_indices
        @property
        def shot_plans(self) -> list: return self._shot_plans
        @property
        def clip_duration_plan(self) -> list[list[int]]: return self._clip_duration_plan
        @property
        def width(self) -> int: return self._width
        @property
        def height(self) -> int: return self._height
        @property
        def duration_seconds(self) -> int: return self._duration_seconds
        @property
        def video_size(self) -> str: return self._video_size
        @property
        def previous_clip_last_frame_url(self) -> str: return self._previous_clip_last_frame_url

    class RenderStageResult:
        def __init__(self, image_run_ids: list[str], video_run_ids: list[str], latest_video_output_url: str, clip_count: int) -> None:
            self._image_run_ids = image_run_ids
            self._video_run_ids = video_run_ids
            self._latest_video_output_url = latest_video_output_url
            self._clip_count = clip_count

        @property
        def image_run_ids(self) -> list[str]: return self._image_run_ids
        @property
        def video_run_ids(self) -> list[str]: return self._video_run_ids
        @property
        def latest_video_output_url(self) -> str: return self._latest_video_output_url
        @property
        def clip_count(self) -> int: return self._clip_count

    async def render(self, task: TaskRecord, run_context: TaskWorkerExecutionContext, request: "TaskWorkerRenderStageService.RenderStageRequest") -> "TaskWorkerRenderStageService.RenderStageResult":
        image_run_ids: list[str] = []
        video_run_ids: list[str] = []
        previous_clip_last_frame_url = request.previous_clip_last_frame_url
        latest_video_output_url = ""

        if request.reuse_storyboard and request.render_start_index > 1:
            self._execution_coordinator.record_trace(
                task, _TaskStage.PLANNING, "planning.keyframe_reused_for_resume",
                "检测到已有进度，跳过已完成镜头并从失败镜头继续。",
                "INFO",
                {
                    "completedClipCount": request.completed_clip_count,
                    "renderStartIndex": request.render_start_index,
                    "existingClipIndices": request.existing_video_clip_indices,
                    "lastFrameUrl": previous_clip_last_frame_url,
                    "resumeFromStage": request.requested_resume_stage,
                    "resumeFromClipIndex": request.requested_resume_clip_index,
                },
            )

        for index in range(max(0, request.render_start_index - 1), len(request.shot_plans)):
            self._runtime_support.assert_task_still_active(task)
            clip_index = index + 1
            shot_plan = request.shot_plans[index]

            clip_prompt = shot_plan.video_prompt()
            first_frame_prompt = _first_non_blank(
                getattr(shot_plan, 'first_frame_prompt', lambda: "")(),
                getattr(shot_plan, 'last_frame_prompt', lambda: "")(),
                clip_prompt,
            )
            last_frame_prompt = _first_non_blank(
                getattr(shot_plan, 'last_frame_prompt', lambda: "")(),
                getattr(shot_plan, 'first_frame_prompt', lambda: "")(),
                clip_prompt,
            )

            clip_duration = request.clip_duration_plan[index] if index < len(request.clip_duration_plan) else [0, 0, 0]
            clip_duration_seconds = clip_duration[0]
            clip_min_duration = clip_duration[1]
            clip_max_duration = clip_duration[2]

            reuse_previous_last_frame = clip_index > 1
            if reuse_previous_last_frame:
                if not previous_clip_last_frame_url.strip():
                    raise ValueError(f"clip {clip_index} requires previous clip last frame before generating its end frame")
                start_frame = self._reuse_frame(task, clip_index, previous_clip_last_frame_url, "first", "previous_video_last_frame")
                self._execution_coordinator.record_trace(
                    task, _TaskStage.PLANNING, "planning.keyframe_reused_from_last_frame",
                    "复用上一镜尾帧作为当前镜头首帧。", "INFO",
                    {"clipIndex": clip_index, "firstFrameUrl": start_frame.video_input_url(), "sourceLastFrameUrl": previous_clip_last_frame_url},
                )
            else:
                start_frame = await self._generate_frame(
                    task, clip_index, first_frame_prompt, request.width, request.height,
                    previous_clip_last_frame_url, clip_duration_seconds, "first",
                    "generated_start_frame_keyframe" if clip_index == 1 else "generated_start_frame_keyframe_fallback",
                    image_run_ids,
                )

            continuity_prompt = self._build_frame_continuity_prompt(
                shot_plan, last_frame_prompt, start_frame.prompt(), start_frame.video_input_url(), "last",
            )
            end_frame = await self._generate_frame(
                task, clip_index, continuity_prompt, request.width, request.height,
                start_frame.video_input_url(), clip_duration_seconds, "last",
                "generated_end_frame_keyframe", image_run_ids,
            )

            self._put_execution_context(task, "imageRunId", _first_non_blank(start_frame.run_id(), end_frame.run_id()))
            self._put_execution_context(task, "keyframeOutputUrl", start_frame.material_url())
            self._put_execution_context(task, "keyframeRemoteSourceUrl", start_frame.source_url())
            self._put_execution_context(task, "firstFrameUrl", start_frame.video_input_url())
            self._put_execution_context(task, "startFrameUrl", start_frame.video_input_url())
            self._put_execution_context(task, "startFrameSourceType", start_frame.source_type())
            self._put_execution_context(task, "startFrameSourceUrl", start_frame.source_url())
            self._put_execution_context(task, "startFrameKeyframeUrl", start_frame.material_url())
            self._put_execution_context(task, "startFrameKeyframeRemoteSourceUrl", start_frame.remote_url())
            self._put_execution_context(task, "startFrameKeyframeRunId", start_frame.run_id())
            self._put_execution_context(task, "lastFrameImageRunId", end_frame.run_id())
            self._put_execution_context(task, "requestedLastFrameUrl", end_frame.video_input_url())
            self._put_execution_context(task, "endFrameConstraintUrl", end_frame.video_input_url())
            self._put_execution_context(task, "endFrameConstraintSourceType", end_frame.source_type())
            self._put_execution_context(task, "endFrameConstraintSourceUrl", end_frame.source_url())
            self._put_execution_context(task, "endFrameKeyframeUrl", end_frame.material_url())
            self._put_execution_context(task, "endFrameKeyframeRemoteSourceUrl", end_frame.remote_url())
            self._put_execution_context(task, "endFrameKeyframeRunId", end_frame.run_id())
            self._put_clip_frame_execution_context(
                task, clip_index,
                self._build_clip_frame_context(shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame, "", "", "", ""),
            )
            await self._task_repository.save(task) if self._task_repository else None

            self._execution_coordinator.record_trace(
                task, _TaskStage.PLANNING, "planning.clip_frames_resolved",
                "当前分镜首尾帧约束已就绪。", "INFO",
                {
                    "clipIndex": clip_index,
                    "clipCount": len(request.shot_plans),
                    "startFrameUrl": start_frame.video_input_url(),
                    "startFrameSourceType": start_frame.source_type(),
                    "startFrameSourceUrl": start_frame.source_url(),
                    "endFrameConstraintUrl": end_frame.video_input_url(),
                    "endFrameConstraintSourceType": end_frame.source_type(),
                    "endFrameConstraintSourceUrl": end_frame.source_url(),
                },
            )
            self._status_stage_service.record_stage_run(
                task, run_context,
                100 + clip_index, _TaskStage.PLANNING, clip_index,
                self._build_planning_stage_request(task, clip_prompt, first_frame_prompt, last_frame_prompt, clip_duration_seconds),
                self._build_planning_stage_response(start_frame, end_frame, reuse_previous_last_frame),
            )

            if index == max(0, request.render_start_index - 1):
                self._status_stage_service.update_status(task, run_context, "RENDERING", 55, _TaskStage.RENDER, "task.rendering", "任务开始按分镜生成视频输出。")
            else:
                task.progress = min(94, 55 + int(35.0 * index / max(1, len(request.shot_plans))))
                await self._task_repository.save(task) if self._task_repository else None

            video_request = self._runtime_support.build_video_run_request(
                task, clip_index, clip_prompt, request.video_size,
                clip_duration_seconds, clip_min_duration, clip_max_duration,
                start_frame.video_input_url(), end_frame.video_input_url(),
            )
            pending_video_model_call = self._status_stage_service.create_pending_model_call(
                task, _TaskStage.RENDER, "generation.video", video_request, clip_index, _GenerationModelKinds.VIDEO,
            )
            self._execution_coordinator.record_model_call(task, pending_video_model_call)

            try:
                video_run = await self._generation_application_service.create_run(video_request)
            except Exception as ex:
                self._execution_coordinator.record_model_call(task, self._status_stage_service.fail_model_call(pending_video_model_call, ex))
                raise

            video_run = await self._await_completed_video_run(video_run)
            self._runtime_support.assert_task_still_active(task)

            video_result = self._result_map(video_run)
            video_metadata = _map_value(video_result.get("metadata"))
            extracted_last_frame_url = self._artifact_assembler.extract_last_frame_url(video_result)
            provider_requested_last_frame_url = _string_value(video_metadata.get("requestedLastFrameUrl"))

            resolved_first_frame_url = _first_non_blank(
                _string_value(video_metadata.get("firstFrameUrl")), start_frame.video_input_url(),
            )
            resolved_last_frame_url = _first_non_blank(
                extracted_last_frame_url, provider_requested_last_frame_url, end_frame.video_input_url(),
            )
            resolved_last_frame_source_type = self._resolved_last_frame_source_type(
                extracted_last_frame_url, provider_requested_last_frame_url, end_frame.video_input_url(),
            )
            resolved_last_frame_source_url = self._resolved_last_frame_source_url(
                extracted_last_frame_url, provider_requested_last_frame_url, end_frame.video_input_url(),
            )

            self._artifact_assembler.normalize_optional_task_artifact(
                task, resolved_last_frame_url,
                _TaskArtifactNaming.last_frame_file_name(clip_index, _file_ext_or_default(_file_name_from_url(resolved_last_frame_url), "png")),
            )

            self._put_execution_context(task, "videoRunId", _string_value(video_run.get("id")))
            self._put_execution_context(task, "videoOutputUrl", _string_value(video_result.get("outputUrl")))
            self._put_execution_context(task, "videoThumbnailUrl", _string_value(video_result.get("thumbnailUrl")))
            self._put_execution_context(task, "firstFrameUrl", resolved_first_frame_url)
            self._put_execution_context(task, "startFrameUrl", resolved_first_frame_url)
            self._put_execution_context(task, "lastFrameUrl", resolved_last_frame_url)
            self._put_execution_context(task, "lastFrameSourceType", resolved_last_frame_source_type)
            self._put_execution_context(task, "lastFrameSourceUrl", resolved_last_frame_source_url)
            self._put_execution_context(task, "requestedLastFrameUrl", end_frame.video_input_url())
            self._put_execution_context(task, "videoRemoteTaskId", _string_value(video_metadata.get("taskId")))
            self._put_execution_context(task, "videoRemoteSourceUrl", _string_value(video_metadata.get("remoteSourceUrl")))
            self._put_clip_frame_execution_context(
                task, clip_index,
                self._build_clip_frame_context(
                    shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame,
                    _string_value(video_run.get("id")),
                    _first_non_blank(_string_value(video_result.get("outputUrl")), _string_value(video_metadata.get("remoteSourceUrl"))),
                    resolved_last_frame_url, resolved_last_frame_source_type,
                ),
            )
            await self._task_repository.save(task) if self._task_repository else None

            video_model_call = self._status_stage_service.complete_model_call(pending_video_model_call, video_run, video_result)
            self._execution_coordinator.record_model_call(task, video_model_call)
            self._status_stage_service.record_run_call_chain(task, _TaskStage.RENDER, video_run, video_result)

            video_material = self._artifact_assembler.create_video_material(task, video_run, video_result, clip_index, clip_duration_seconds)
            self._execution_coordinator.record_material(task, video_material)

            self._put_execution_context(task, "videoOutputUrl", _string_value(video_material.get("fileUrl")))
            self._put_clip_frame_execution_context(
                task, clip_index,
                self._build_clip_frame_context(
                    shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame,
                    _string_value(video_run.get("id")),
                    _string_value(video_material.get("fileUrl")),
                    resolved_last_frame_url, resolved_last_frame_source_type,
                ),
            )
            latest_video_output_url = _string_value(video_material.get("fileUrl"))
            task.completed_output_count = max(task.completed_output_count, clip_index)
            await self._task_repository.save(task) if self._task_repository else None

            video_output = self._artifact_assembler.create_result(
                task, video_run, video_result, video_material, start_frame.material(),
                video_model_call, resolved_last_frame_url, clip_index,
                clip_duration_seconds, clip_min_duration, clip_max_duration,
            )
            self._execution_coordinator.record_result(task, video_output)

            self._status_stage_service.record_stage_run(
                task, run_context,
                200 + clip_index, _TaskStage.RENDER, clip_index,
                self._build_render_stage_request(start_frame, end_frame, clip_duration_seconds),
                self._build_render_stage_response(
                    video_run, video_material, video_metadata,
                    resolved_first_frame_url, resolved_last_frame_url, resolved_last_frame_source_type,
                    end_frame.video_input_url(),
                ),
            )
            self._execution_coordinator.record_trace(
                task, _TaskStage.RENDER, "render.clip_completed",
                "当前分镜片段已生成完成。", "INFO",
                {
                    "clipIndex": clip_index,
                    "clipCount": len(request.shot_plans),
                    "outputUrl": _string_value(video_material.get("fileUrl")),
                    "firstFrameUrl": resolved_first_frame_url,
                    "firstFrameSourceType": start_frame.source_type(),
                    "requestedLastFrameUrl": end_frame.video_input_url(),
                    "requestedLastFrameSourceType": end_frame.source_type(),
                    "lastFrameUrl": resolved_last_frame_url,
                    "lastFrameSourceType": resolved_last_frame_source_type,
                },
            )
            video_run_ids.append(_string_value(video_run.get("id")))
            previous_clip_last_frame_url = resolved_last_frame_url
            if self._join_stage_service:
                self._join_stage_service.schedule_join(task.id, clip_index)

        self._runtime_support.assert_task_still_active(task)
        if not latest_video_output_url:
            latest_video_output_url = self._resolve_latest_video_output_url(task)
        if self._join_stage_service:
            self._join_stage_service.schedule_join(task.id, len(request.shot_plans))
        self._put_execution_context(task, "clipImageRunIds", self._merge_string_list_context(task.execution_context.get("clipImageRunIds"), image_run_ids))
        self._put_execution_context(task, "clipVideoRunIds", self._merge_string_list_context(task.execution_context.get("clipVideoRunIds"), video_run_ids))
        task.completed_output_count = len(request.shot_plans)
        self._put_execution_context(task, "resumeExistingOutputCount", None)
        self._put_execution_context(task, "resumeExistingClipIndices", None)
        self._put_execution_context(task, "resumeRenderFromClipIndex", None)
        self._put_execution_context(task, "attemptResumeFromStage", None)
        self._put_execution_context(task, "attemptResumeFromClipIndex", None)
        await self._task_repository.save(task) if self._task_repository else None
        return self.RenderStageResult(image_run_ids, video_run_ids, latest_video_output_url, len(request.shot_plans))

    async def _await_completed_video_run(self, initial_run: dict[str, Any]) -> dict[str, Any]:
        current_status = self._normalized_run_status(initial_run)
        if not self._is_video_run_active(current_status):
            self._assert_video_run_succeeded(initial_run, current_status)
            return initial_run
        run_id = _string_value(initial_run.get("id"))
        if not run_id:
            raise ValueError("video run is active but missing run id")
        current_run = initial_run
        for _ in range(self._video_run_max_polls):
            current_run = await self._generation_application_service.get_run(run_id)
            current_status = self._normalized_run_status(current_run)
            if not self._is_video_run_active(current_status):
                self._assert_video_run_succeeded(current_run, current_status)
                return current_run
            self._sleep_before_next_video_poll()
        raise TimeoutError(f"video run wait timeout: runId={run_id}, status={current_status}, maxPolls={self._video_run_max_polls}")

    def _build_frame_continuity_prompt(self, shot_plan: Any, prompt: str, start_frame_prompt: str, reference_image_url: str, frame_role: str) -> str:
        base_prompt = _first_non_blank(
            prompt,
            getattr(shot_plan, 'last_frame_prompt', lambda: "")(),
            getattr(shot_plan, 'first_frame_prompt', lambda: "")(),
            getattr(shot_plan, 'video_prompt', lambda: "")(),
            getattr(shot_plan, 'scene', lambda: "")(),
        )
        if frame_role.lower() != "last" or not _string_value(reference_image_url):
            return base_prompt
        parts: list[str] = []
        parts.append("你现在要生成同一镜头连续动作后的尾帧，必须严格沿用参考图已经确定的同一场景、同一机位体系、同一空间锚点、同一人物外观与服装、同一道具位置关系，禁止漂移到新的场景。")
        parts.append("尾帧只允许在参考首帧基础上推进人物动作状态、视线方向、手部位置或道具使用结果，禁止新增、删除或替换背景布局、门窗桌椅书架等场景元素。")
        resolved_start_frame_prompt = _first_non_blank(
            start_frame_prompt,
            getattr(shot_plan, 'first_frame_prompt', lambda: "")(),
            getattr(shot_plan, 'last_frame_prompt', lambda: "")(),
        )
        if resolved_start_frame_prompt:
            parts.append(f"参考首帧描述：{resolved_start_frame_prompt}")
            parts.append(f"场景锁定基准：{resolved_start_frame_prompt}")
        if hasattr(shot_plan, 'scene') and shot_plan.scene:
            parts.append(f"场景锚点：{shot_plan.scene}")
        camera = getattr(shot_plan, 'camera_movement', lambda: "")()
        if camera and camera.lower() != "static":
            parts.append(f"运镜：{camera}")
        if base_prompt:
            parts.append(f"尾帧目标：{base_prompt}")
        return "\n".join(parts)

    async def _generate_frame(self, task: TaskRecord, clip_index: int, prompt: str, width: int, height: int,
                              reference_image_url: str, duration_seconds: int, frame_role: str,
                              source_type: str, image_run_ids: list[str]) -> "FrameResolution":
        image_request = self._runtime_support.build_image_run_request(
            task, clip_index, prompt, width, height, reference_image_url, duration_seconds, frame_role,
        )
        pending_image_model_call = self._status_stage_service.create_pending_model_call(
            task, _TaskStage.PLANNING, "generation.image", image_request, clip_index, _GenerationModelKinds.IMAGE,
        )
        self._execution_coordinator.record_model_call(task, pending_image_model_call)
        try:
            image_run = await self._generation_application_service.create_run(image_request)
        except Exception as ex:
            self._execution_coordinator.record_model_call(task, self._status_stage_service.fail_model_call(pending_image_model_call, ex))
            raise
        self._runtime_support.assert_task_still_active(task)
        image_result = self._result_map(image_run)
        image_metadata = _map_value(image_result.get("metadata"))
        keyframe_source_url = _first_non_blank(
            _string_value(image_metadata.get("remoteSourceUrl")),
            _string_value(image_result.get("outputUrl")),
        )
        image_model_call = self._status_stage_service.complete_model_call(pending_image_model_call, image_run, image_result)
        self._execution_coordinator.record_model_call(task, image_model_call)
        self._status_stage_service.record_run_call_chain(task, _TaskStage.PLANNING, image_run, image_result)
        image_material = self._artifact_assembler.create_image_material(task, image_run, image_result, clip_index, frame_role)
        self._execution_coordinator.record_material(task, image_material)
        image_run_ids.append(_string_value(image_run.get("id")))
        return self.FrameResolution(
            prompt=_string_value(prompt),
            frame_role=_string_value(frame_role),
            source_type=_string_value(source_type),
            source_url=keyframe_source_url,
            material_url=_string_value(image_material.get("fileUrl")),
            remote_url=_first_non_blank(_string_value(image_material.get("remoteUrl")), keyframe_source_url),
            video_input_url=_first_non_blank(keyframe_source_url, _string_value(image_material.get("remoteUrl")), _string_value(image_material.get("fileUrl"))),
            run_id=_string_value(image_run.get("id")),
            material=image_material,
        )

    def _reuse_frame(self, task: TaskRecord, clip_index: int, source_url: str, frame_role: str, source_type: str) -> "FrameResolution":
        image_material = self._artifact_assembler.create_reference_frame_material(task, clip_index, source_url, frame_role)
        self._execution_coordinator.record_material(task, image_material)
        remote_url = _first_non_blank(_string_value(image_material.get("remoteUrl")), source_url)
        return self.FrameResolution(
            prompt="",
            frame_role=_string_value(frame_role),
            source_type=_string_value(source_type),
            source_url=_string_value(source_url),
            material_url=_string_value(image_material.get("fileUrl")),
            remote_url=remote_url,
            video_input_url=_first_non_blank(remote_url, _string_value(image_material.get("fileUrl"))),
            run_id="",
            material=image_material,
        )

    def _build_planning_stage_request(self, task: TaskRecord, clip_prompt: str, first_frame_prompt: str, last_frame_prompt: str, clip_duration_seconds: int) -> dict[str, Any]:
        snapshot = task.request_snapshot or {}
        return {
            "aspectRatio": snapshot.get("aspectRatio", task.aspect_ratio),
            "clipPrompt": _truncate_text(clip_prompt, 160),
            "firstFramePrompt": _truncate_text(first_frame_prompt, 160),
            "lastFramePrompt": _truncate_text(last_frame_prompt, 160),
            "targetDurationSeconds": clip_duration_seconds,
        }

    def _build_planning_stage_response(self, start_frame: "FrameResolution", end_frame: "FrameResolution", reused_previous_start: bool) -> dict[str, Any]:
        return {
            "summary": "已复用上一镜尾帧作为首帧，并生成当前镜头尾帧关键画面" if reused_previous_start else "当前镜头首尾关键画面已生成",
            "imageRunId": _first_non_blank(start_frame.run_id(), end_frame.run_id()),
            "imageUrl": start_frame.material_url(),
            "remoteImageUrl": start_frame.video_input_url(),
            "startFrameUrl": start_frame.video_input_url(),
            "startFrameSourceType": start_frame.source_type(),
            "startFrameSourceUrl": start_frame.source_url(),
            "startFrameKeyframeUrl": start_frame.material_url(),
            "startFrameImageRunId": start_frame.run_id(),
            "endFrameConstraintUrl": end_frame.video_input_url(),
            "endFrameSourceType": end_frame.source_type(),
            "endFrameSourceUrl": end_frame.source_url(),
            "endFrameKeyframeUrl": end_frame.material_url(),
            "endFrameImageRunId": end_frame.run_id(),
        }

    def _build_render_stage_request(self, start_frame: "FrameResolution", end_frame: "FrameResolution", clip_duration_seconds: int) -> dict[str, Any]:
        return {
            "imageRunId": _first_non_blank(start_frame.run_id(), end_frame.run_id()),
            "posterUrl": start_frame.material_url(),
            "targetDurationSeconds": clip_duration_seconds,
            "firstFrameUrl": start_frame.video_input_url(),
            "firstFrameSourceType": start_frame.source_type(),
            "requestedLastFrameUrl": end_frame.video_input_url(),
            "requestedLastFrameSourceType": end_frame.source_type(),
        }

    def _build_render_stage_response(self, video_run: dict[str, Any], video_material: dict[str, Any], video_metadata: dict[str, Any],
                                      resolved_first_frame_url: str, resolved_last_frame_url: str, resolved_last_frame_source_type: str,
                                      requested_last_frame_url: str) -> dict[str, Any]:
        return {
            "videoRunId": _string_value(video_run.get("id")),
            "outputUrl": _string_value(video_material.get("fileUrl")),
            "remoteTaskId": _string_value(video_metadata.get("taskId")),
            "firstFrameUrl": resolved_first_frame_url,
            "requestedLastFrameUrl": requested_last_frame_url,
            "lastFrameUrl": resolved_last_frame_url,
            "lastFrameSourceType": resolved_last_frame_source_type,
        }

    def _build_clip_frame_context(self, shot_plan: Any, clip_index: int, clip_duration_seconds: int,
                                   start_frame: "FrameResolution", end_frame: "FrameResolution",
                                   video_run_id: str, video_output_url: str, resolved_last_frame_url: str,
                                   resolved_last_frame_source_type: str) -> dict[str, Any]:
        return {
            "clipIndex": clip_index,
            "shotLabel": getattr(shot_plan, 'shot_label', lambda: "")(),
            "scene": getattr(shot_plan, 'scene', lambda: "")(),
            "targetDurationSeconds": clip_duration_seconds,
            "startFramePrompt": _first_non_blank(start_frame.prompt(), getattr(shot_plan, 'first_frame_prompt', lambda: "")(), getattr(shot_plan, 'last_frame_prompt', lambda: "")()),
            "startFrameUrl": start_frame.video_input_url(),
            "startFrameSourceType": start_frame.source_type(),
            "startFrameSourceUrl": start_frame.source_url(),
            "startFrameKeyframeUrl": start_frame.material_url(),
            "startFrameKeyframeRemoteSourceUrl": start_frame.remote_url(),
            "startFrameKeyframeRunId": start_frame.run_id(),
            "endFramePrompt": _first_non_blank(end_frame.prompt(), getattr(shot_plan, 'last_frame_prompt', lambda: "")()),
            "endFrameConstraintUrl": end_frame.video_input_url(),
            "endFrameSourceType": end_frame.source_type(),
            "endFrameSourceUrl": end_frame.source_url(),
            "endFrameKeyframeUrl": end_frame.material_url(),
            "endFrameKeyframeRemoteSourceUrl": end_frame.remote_url(),
            "endFrameKeyframeRunId": end_frame.run_id(),
            "videoRunId": video_run_id,
            "videoOutputUrl": video_output_url,
            "returnedLastFrameUrl": resolved_last_frame_url,
            "returnedLastFrameSourceType": resolved_last_frame_source_type,
        }

    def _put_clip_frame_execution_context(self, task: TaskRecord, clip_index: int, clip_frame_context: dict[str, Any]) -> None:
        rows: list[dict[str, Any]] = []
        existing = task.execution_context.get("clipFrameContexts")
        if isinstance(existing, list):
            for item in existing:
                if isinstance(item, dict):
                    if _int_value(item.get("clipIndex"), 0) != clip_index:
                        rows.append(dict(item))
        rows.append(clip_frame_context)
        rows.sort(key=lambda r: _int_value(r.get("clipIndex"), 0))
        self._put_execution_context(task, "clipFrameContexts", rows)

    def _resolved_last_frame_source_type(self, extracted_last_frame_url: str, provider_requested_last_frame_url: str, requested_last_frame_url: str) -> str:
        if _string_value(extracted_last_frame_url):
            return "video_result_last_frame"
        if _string_value(provider_requested_last_frame_url):
            return "video_requested_last_frame"
        if _string_value(requested_last_frame_url):
            return "end_frame_keyframe_fallback"
        return ""

    def _resolved_last_frame_source_url(self, extracted_last_frame_url: str, provider_requested_last_frame_url: str, requested_last_frame_url: str) -> str:
        return _first_non_blank(extracted_last_frame_url, provider_requested_last_frame_url, requested_last_frame_url)

    def _result_map(self, run: dict[str, Any]) -> dict[str, Any]:
        result = run.get("result")
        return result if isinstance(result, dict) else {}

    def _resolve_latest_video_output_url(self, task: TaskRecord) -> str:
        latest_clip_index = 0
        latest_output_url = ""
        for output in task.outputs:
            if not _TaskResultTypes.is_primary_video(output.get("resultType")):
                continue
            clip_index = _int_value(output.get("clipIndex"), 0)
            if clip_index >= latest_clip_index:
                latest_clip_index = clip_index
                latest_output_url = _first_non_blank(
                    _string_value(output.get("downloadUrl")),
                    _string_value(output.get("previewUrl")),
                )
        return latest_output_url

    def _put_execution_context(self, task: TaskRecord, key: str, value: Any) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        if value is None:
            task.execution_context.pop(key, None)
            return
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                task.execution_context.pop(key, None)
                return
        task.execution_context[key] = value

    def _merge_string_list_context(self, existing: Any, appended: list[str]) -> list[str]:
        merged: set[str] = set()
        if isinstance(existing, list):
            for item in existing:
                v = _string_value(item)
                if v:
                    merged.add(v)
        for item in appended:
            v = _string_value(item)
            if v:
                merged.add(v)
        return list(merged)

    def _normalized_run_status(self, run: dict[str, Any] | None) -> str:
        return _string_value(run.get("status") if run else None).lower()

    def _is_video_run_active(self, status: str) -> bool:
        return _GenerationRunStatuses.is_active(status)

    def _assert_video_run_succeeded(self, run: dict[str, Any] | None, status: str) -> None:
        if _GenerationRunStatuses.is_successful(status):
            return
        result = self._result_map(run or {})
        metadata = _map_value(result.get("metadata"))
        message = _first_non_blank(
            _string_value(result.get("error")),
            _string_value(metadata.get("taskMessage")),
            _string_value(metadata.get("message")),
        )
        raise RuntimeError(
            f"video run did not complete successfully: runId={_string_value(run.get('id') if run else None)}, "
            f"status={status}{('', ', error=' + message) if message else ''}"
        )

    def _sleep_before_next_video_poll(self) -> None:
        if self._video_run_poll_interval_ms <= 0:
            return
        import time
        time.sleep(self._video_run_poll_interval_ms / 1000.0)

    class FrameResolution:
        def __init__(self, prompt: str = "", frame_role: str = "", source_type: str = "", source_url: str = "",
                     material_url: str = "", remote_url: str = "", video_input_url: str = "", run_id: str = "",
                     material: dict[str, Any] | None = None) -> None:
            self._prompt = prompt
            self._frame_role = frame_role
            self._source_type = source_type
            self._source_url = source_url
            self._material_url = material_url
            self._remote_url = remote_url
            self._video_input_url = video_input_url
            self._run_id = run_id
            self._material = material or {}

        def prompt(self) -> str: return self._prompt
        def frame_role(self) -> str: return self._frame_role
        def source_type(self) -> str: return self._source_type
        def source_url(self) -> str: return self._source_url
        def material_url(self) -> str: return self._material_url
        def remote_url(self) -> str: return self._remote_url
        def video_input_url(self) -> str: return self._video_input_url
        def run_id(self) -> str: return self._run_id
        def material(self) -> dict[str, Any]: return self._material


# ===================================================================
# JoinOutputService
# ===================================================================

class JoinOutputService:
    """Service for concatenating video clip outputs into a single joined output."""

    JOIN_OUTPUT_CLIP_INDEX_BASE = 10000

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        local_media_artifact_service: LocalMediaArtifactServiceStub | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        self._local_media_artifact_service = local_media_artifact_service
        self._join_worker_instance_id = f"spring_join_worker_{uuid.uuid4().hex}"

    def schedule_join(self, task_id: str, end_clip_index: int) -> None:
        """Stub: schedule join would use a thread pool in production."""
        pass

    def _join_output_name(self, end_clip_index: int) -> str:
        if end_clip_index <= 1:
            return "join-1"
        return _TaskArtifactNaming.join_name(end_clip_index)


# ===================================================================
# TaskWorkerPipelineHandler
# ===================================================================

class TaskWorkerPipelineHandler:
    """Orchestrates the full task execution pipeline: analysis -> planning -> rendering -> join."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        task_queue_port: TaskQueuePort | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        generation_application_service: GenerationApplicationServiceStub | None = None,
        runtime_support: TaskExecutionRuntimeSupport | None = None,
        artifact_assembler: TaskExecutionArtifactAssembler | None = None,
        storyboard_planner: TaskStoryboardPlannerStub | None = None,
        status_stage_service: TaskWorkerStatusStageService | None = None,
        render_stage_service: TaskWorkerRenderStageService | None = None,
        join_stage_service: JoinOutputService | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._task_queue_port = task_queue_port
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        self._generation_application_service = generation_application_service or DefaultGenerationApplicationService()
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler()
        self._storyboard_planner = storyboard_planner or TaskStoryboardPlannerStub()
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository, execution_coordinator=self._execution_coordinator,
        )
        self._render_stage_service = render_stage_service or TaskWorkerRenderStageService(
            task_repository=task_repository,
            execution_coordinator=self._execution_coordinator,
            generation_application_service=self._generation_application_service,
            runtime_support=self._runtime_support,
            artifact_assembler=self._artifact_assembler,
            status_stage_service=self._status_stage_service,
            join_stage_service=join_stage_service,
        )
        self._join_stage_service = join_stage_service

    async def _save_result(self, result: dict[str, Any] | None) -> None:
        if self._task_repository is None or not result:
            return
        mutation = result.get("mutation")
        if isinstance(mutation, TaskPersistenceMutation):
            await self._task_repository.save_mutation(mutation)

    async def process_task(
        self,
        task_id: str,
        worker_instance_id: str,
        worker_type: str,
        execution_mode: str,
    ) -> None:
        run_context = TaskWorkerExecutionContext(worker_instance_id, worker_type, execution_mode)
        await self._process_task(task_id, run_context)

    async def _process_task(self, task_id: str, run_context: TaskWorkerExecutionContext) -> None:
        if self._task_repository is None:
            return
        task = await self._task_repository.find_by_id(task_id)
        if task is None:
            if self._task_queue_port:
                result = self._task_queue_port.remove(task_id)
                if hasattr(result, "__await__"):
                    await result
            return
        if task.status != "PENDING" and TaskStatus(task.status) != TaskStatus.PENDING:
            if self._task_queue_port:
                result = self._task_queue_port.remove(task_id)
                if hasattr(result, "__await__"):
                    await result
            return
        try:
            if self._task_queue_port:
                result = self._task_queue_port.remove(task.id)
                if hasattr(result, "__await__"):
                    await result
            task.is_queued = False
            task.queue_position = None
            if not task.started_at:
                task.started_at = _now_iso()
            self._runtime_support.assert_task_still_active(task)
            active_attempt = self._runtime_support.active_attempt(task)
            dimensions = self._runtime_support.resolve_dimensions(task)

            if not self._is_video_generation_task(task):
                await self._process_workspace_image_task(task, run_context, dimensions)
                return

            duration_seconds = self._runtime_support.resolve_duration_seconds(task)
            video_size = f"{dimensions[0]}*{dimensions[1]}"
            existing_video_clip_indices = self._existing_video_clip_indices(task)
            completed_clip_count = self._last_contiguous_completed_clip_index(existing_video_clip_indices)
            render_start_index = max(1, completed_clip_count + 1)
            requested_resume_stage = _string_value(active_attempt.get("resumeFromStage") if active_attempt else None)
            requested_resume_clip_index = _int_value(
                active_attempt.get("resumeFromClipIndex") if active_attempt else None,
                render_start_index,
            )
            reuse_storyboard = bool(requested_resume_stage) or completed_clip_count > 0

            self._put_execution_context(task, "durationSeconds", duration_seconds)
            self._put_execution_context(task, "videoSize", video_size)
            self._put_execution_context(task, "workerInstanceId", run_context.worker_instance_id)
            self._put_execution_context(task, "resumeExistingClipIndices", existing_video_clip_indices)
            self._put_execution_context(task, "resumeExistingOutputCount", completed_clip_count)
            self._put_execution_context(task, "resumeRenderFromClipIndex", render_start_index)
            self._put_execution_context(task, "attemptResumeFromStage", requested_resume_stage)
            self._put_execution_context(task, "attemptResumeFromClipIndex", requested_resume_clip_index)

            await self._save_result(self._execution_coordinator.mark_active_attempt_running(task, run_context.worker_instance_id))
            await self._save_result(self._status_stage_service.update_status(
                task, run_context, "ANALYZING", 5, _TaskStage.ANALYSIS, "task.claimed", "任务已被 worker 领取。",
            ))
            self._runtime_support.assert_task_still_active(task)

            script_run: dict[str, Any] = {}
            storyboard_markdown = ""

            if reuse_storyboard and task.storyboard_script and task.storyboard_script.strip():
                storyboard_markdown = task.storyboard_script
                await self._save_result(self._execution_coordinator.record_trace(
                    task, _TaskStage.ANALYSIS, "analysis.reused",
                    "检测到已有分镜脚本，跳过分析并继续后续镜头。", "INFO",
                    {
                        "completedClipCount": completed_clip_count,
                        "renderStartIndex": render_start_index,
                        "resumeFromStage": requested_resume_stage,
                        "resumeFromClipIndex": requested_resume_clip_index,
                    },
                ))
            else:
                await self._save_result(self._status_stage_service.update_status(
                    task, run_context, "ANALYZING", 10, _TaskStage.ANALYSIS, "task.analyzing", "任务开始分析文本与镜头约束。",
                ))

                script_request = self._runtime_support.build_script_run_request(task)
                pending_model_call = self._status_stage_service.create_pending_model_call(
                    task, _TaskStage.ANALYSIS, "generation.script", script_request, 1, "script",
                )
                await self._save_result(self._execution_coordinator.record_model_call(task, pending_model_call))
                try:
                    script_run = await self._generation_application_service.create_run(script_request)
                except Exception as ex:
                    await self._save_result(self._execution_coordinator.record_model_call(task, self._status_stage_service.fail_model_call(pending_model_call, ex)))
                    raise

                self._runtime_support.assert_task_still_active(task)
                script_result = self._result_map(script_run)
                storyboard_markdown = _string_value(script_result.get("scriptMarkdown"))
                if not storyboard_markdown:
                    raise ValueError("分镜脚本为空，未生成有效输出。")
                task.storyboard_script = storyboard_markdown
                self._put_execution_context(task, "analysisRunId", _string_value(script_run.get("id")))
                self._put_execution_context(task, "scriptRunId", _string_value(script_run.get("id")))
                self._put_execution_context(task, "analysisScriptText", storyboard_markdown)
                self._put_execution_context(task, "analysisPrompt", _string_value(script_result.get("prompt")))
                await self._task_repository.save(task)

                await self._save_result(self._status_stage_service.record_stage_run(
                    task, run_context, 1, _TaskStage.ANALYSIS, 1,
                    {"title": task.title, "aspectRatio": task.aspect_ratio},
                    {"summary": "文本分析完成", "scriptRunId": _string_value(script_run.get("id"))},
                ))
                analysis_model_call = self._status_stage_service.complete_model_call(pending_model_call, script_run, script_result)
                await self._save_result(self._execution_coordinator.record_model_call(task, analysis_model_call))
                self._status_stage_service.record_run_call_chain(task, _TaskStage.ANALYSIS, script_run, script_result)
                script_material = self._artifact_assembler.create_text_material(task, script_run, script_result)
                await self._save_result(self._execution_coordinator.record_material(task, script_material))
                self._put_execution_context(task, "storyboardFileUrl", _string_value(script_material.get("fileUrl")))
                await self._task_repository.save(task)

            shot_plans = self._storyboard_planner.build_storyboard_shot_plans(task, storyboard_markdown)
            storyboard_clip_count = len(shot_plans)
            requested_output_count = self._storyboard_planner.resolve_requested_output_count(task, storyboard_clip_count)
            if requested_output_count < len(shot_plans):
                shot_plans = list(shot_plans[:requested_output_count])

            clip_prompts = [sp.video_prompt() for sp in shot_plans]
            storyboard_duration_ranges = self._storyboard_planner.extract_storyboard_shot_duration_ranges(storyboard_markdown)
            clip_duration_plan = self._storyboard_planner.build_clip_duration_plan(task, duration_seconds, len(clip_prompts), storyboard_markdown)
            snapshot = task.request_snapshot or {}
            clip_duration_plan = self._storyboard_planner.normalize_clip_duration_plan(
                _string_value(snapshot.get("videoModel", "")),
                clip_duration_plan,
            )
            self._put_execution_context(task, "storyboardClipCount", storyboard_clip_count)
            self._put_execution_context(task, "requestedOutputCount", self._storyboard_planner.request_snapshot_output_count(task))
            self._put_execution_context(task, "plannedClipCount", len(clip_prompts))
            self._put_execution_context(task, "clipPrompts", clip_prompts)
            self._put_execution_context(task, "clipDurationPlan", self._storyboard_planner.build_clip_duration_plan_context(clip_duration_plan, storyboard_duration_ranges))
            self._put_execution_context(task, "storyboardFormatVersion", "structured-md-v1")
            self._put_execution_context(task, "storyboardContinuityRule", "current_end_frame_matches_next_start_frame")
            self._put_execution_context(task, "storyboardClips", self._build_storyboard_clip_context(shot_plans, clip_duration_plan))
            await self._task_repository.save(task)

            await self._save_result(self._execution_coordinator.record_trace(
                task, _TaskStage.PLANNING, "planning.shots_resolved",
                "已完成分镜数量解析，按镜头顺序生成。", "INFO",
                {
                    "clipCount": len(clip_prompts),
                    "storyboardClipCount": storyboard_clip_count,
                    "requestedOutputCount": self._storyboard_planner.request_snapshot_output_count(task),
                    "completedClipCount": completed_clip_count,
                    "renderStartIndex": render_start_index,
                },
            ))

            await self._save_result(self._status_stage_service.update_status(
                task, run_context, "PLANNING", 35, _TaskStage.PLANNING, "task.planning", "任务开始按分镜生成关键画面。",
            ))

            render_request = TaskWorkerRenderStageService.RenderStageRequest(
                reuse_storyboard=reuse_storyboard,
                render_start_index=render_start_index,
                completed_clip_count=completed_clip_count,
                requested_resume_stage=requested_resume_stage,
                requested_resume_clip_index=requested_resume_clip_index,
                existing_video_clip_indices=existing_video_clip_indices,
                shot_plans=shot_plans,
                clip_duration_plan=clip_duration_plan,
                width=dimensions[0],
                height=dimensions[1],
                duration_seconds=duration_seconds,
                video_size=video_size,
                previous_clip_last_frame_url=self._resolve_resume_last_frame_url(task, completed_clip_count),
            )
            render_result = await self._render_stage_service.render(task, run_context, render_request)

            await self._save_result(self._status_stage_service.complete_task(
                task, run_context, script_run,
                render_result.image_run_ids,
                render_result.video_run_ids,
                render_result.clip_count,
                render_result.latest_video_output_url,
            ))
            if self._join_stage_service:
                self._join_stage_service.schedule_join(task.id, render_result.clip_count)

        except TaskExecutionAbortedException as ex:
            await self._save_result(self._status_stage_service.handle_abort(task, run_context, ex.task_status))
        except Exception as ex:
            await self._save_result(self._status_stage_service.fail_task(task, run_context, ex))

    async def _process_workspace_image_task(self, task: TaskRecord, run_context: TaskWorkerExecutionContext, dimensions: list[int]) -> None:
        self._put_execution_context(task, "imageSize", f"{dimensions[0]}x{dimensions[1]}")
        self._put_execution_context(task, "workerInstanceId", run_context.worker_instance_id)
        await self._save_result(self._execution_coordinator.mark_active_attempt_running(task, run_context.worker_instance_id))
        await self._save_result(self._status_stage_service.update_status(
            task, run_context, "RENDERING", 5, _TaskStage.RENDER, "task.claimed", "任务已被 worker 领取。",
        ))
        self._runtime_support.assert_task_still_active(task)

        await self._save_result(self._status_stage_service.update_status(
            task, run_context, "RENDERING", 40, _TaskStage.RENDER, "task.rendering", "工作台图片任务开始生成。",
        ))

        image_request = self._runtime_support.build_workspace_image_run_request(task, dimensions[0], dimensions[1])
        pending_model_call = self._status_stage_service.create_pending_model_call(
            task, _TaskStage.RENDER, "generation.image", image_request, 1, "workspace_image",
        )
        await self._save_result(self._execution_coordinator.record_model_call(task, pending_model_call))
        try:
            image_run = await self._generation_application_service.create_run(image_request)
        except Exception as ex:
            await self._save_result(self._execution_coordinator.record_model_call(task, self._status_stage_service.fail_model_call(pending_model_call, ex)))
            raise
        self._runtime_support.assert_task_still_active(task)
        image_result = self._result_map(image_run)
        image_metadata = _map_value(image_result.get("metadata"))
        output_url = _first_non_blank(
            _string_value(image_result.get("outputUrl")),
            _string_value(image_metadata.get("outputUrl")),
            _string_value(image_metadata.get("fileUrl")),
        )
        if not output_url:
            raise ValueError("图片生成结果为空，未返回可用输出地址。")

        image_model_call = self._status_stage_service.complete_model_call(pending_model_call, image_run, image_result)
        await self._save_result(self._execution_coordinator.record_model_call(task, image_model_call))
        self._status_stage_service.record_run_call_chain(task, _TaskStage.RENDER, image_run, image_result)
        image_material = self._artifact_assembler.create_workspace_image_material(task, image_run, image_result)
        await self._save_result(self._execution_coordinator.record_material(task, image_material))
        image_output = self._artifact_assembler.create_image_result(task, image_run, image_result, image_material, image_model_call)
        await self._save_result(self._execution_coordinator.record_result(task, image_output))
        self._put_execution_context(task, "latestImageRunId", _string_value(image_run.get("id")))
        self._put_execution_context(task, "latestImageOutputUrl", output_url)
        self._put_execution_context(task, "latestMaterialAssetId", _string_value(image_material.get("id")))
        await self._task_repository.save(task)
        await self._save_result(self._status_stage_service.record_stage_run(
            task, run_context, 1, _TaskStage.RENDER, 1,
            {"title": task.title, "taskType": task.task_type, "width": dimensions[0], "height": dimensions[1]},
            {"summary": "工作台图片生成完成", "imageRunId": _string_value(image_run.get("id")), "outputUrl": output_url, "materialAssetId": _string_value(image_material.get("id"))},
        ))
        await self._save_result(self._status_stage_service.complete_workspace_image_task(task, run_context, image_run, output_url))

    def _is_video_generation_task(self, task: TaskRecord) -> bool:
        return task.task_type is None or task.task_type == "video_generation"

    def _existing_video_clip_indices(self, task: TaskRecord) -> list[int]:
        indices: list[int] = []
        for output in task.outputs:
            if not _TaskResultTypes.is_primary_video(output.get("resultType")):
                continue
            clip_index = _int_value(output.get("clipIndex"), 0)
            if clip_index > 0:
                indices.append(clip_index)
        indices.sort()
        return indices

    def _last_contiguous_completed_clip_index(self, clip_indices: list[int]) -> int:
        expected = 1
        for clip_index in clip_indices:
            if clip_index is None or clip_index != expected:
                break
            expected += 1
        return expected - 1

    def _resolve_resume_last_frame_url(self, task: TaskRecord, completed_clip_count: int) -> str:
        ctx = task.execution_context or {}
        stored = _string_value(ctx.get("lastFrameUrl"))
        if stored:
            return stored
        if completed_clip_count <= 0:
            return ""
        for output in task.outputs:
            if not _TaskResultTypes.is_primary_video(output.get("resultType")):
                continue
            if _int_value(output.get("clipIndex"), 0) != completed_clip_count:
                continue
            extra = _map_value(output.get("extra"))
            return _first_non_blank(
                _string_value(extra.get("lastFrameUrl")),
                _string_value(extra.get("firstFrameUrl")),
            )
        return ""

    def _build_storyboard_clip_context(self, shot_plans: list, clip_duration_plan: list[list[int]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, shot_plan in enumerate(shot_plans):
            duration = clip_duration_plan[index] if index < len(clip_duration_plan) else [0, 0, 0]
            row: dict[str, Any] = {
                "clipIndex": shot_plan.sequential_index(),
                "shotLabel": shot_plan.shot_label(),
                "scene": shot_plan.scene(),
                "startFramePrompt": shot_plan.first_frame_prompt(),
                "endFramePrompt": shot_plan.last_frame_prompt(),
                "firstFramePrompt": shot_plan.first_frame_prompt(),
                "lastFramePrompt": shot_plan.last_frame_prompt(),
                "actionPath": shot_plan.motion(),
                "motion": shot_plan.motion(),
                "cameraMovement": shot_plan.camera_movement(),
                "durationHint": shot_plan.duration_hint(),
                "imagePrompt": shot_plan.image_prompt(),
                "videoPrompt": shot_plan.video_prompt(),
                "targetDurationSeconds": duration[0],
                "minDurationSeconds": duration[1],
                "maxDurationSeconds": duration[2],
                "continuityRule": "current_end_frame_matches_next_start_frame",
            }
            if index + 1 < len(shot_plans):
                next_shot = shot_plans[index + 1]
                row["nextClipIndex"] = next_shot.sequential_index()
                row["nextClipShotLabel"] = next_shot.shot_label()
                row["nextClipStartFramePrompt"] = next_shot.first_frame_prompt()
            rows.append(row)
        return rows

    def _put_execution_context(self, task: TaskRecord, key: str, value: Any) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        if value is None:
            task.execution_context.pop(key, None)
            return
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                task.execution_context.pop(key, None)
                return
        task.execution_context[key] = value

    def _result_map(self, run: dict[str, Any]) -> dict[str, Any]:
        result = run.get("result")
        return result if isinstance(result, dict) else {}


# ===================================================================
# TaskViewMapper
# ===================================================================

class TaskViewMapper:
    """Maps raw task records to view models (list item, detail, showcase)."""

    def __init__(self, local_media_artifact_service: LocalMediaArtifactServiceStub | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service

    def to_list_item(self, task: TaskRecord) -> dict[str, Any]:
        monitoring = self._monitoring_summary(task)
        diagnosis = self._diagnosis_summary(task, monitoring)
        failure = self._failure_summary(task)
        return {
            "id": task.id,
            "taskType": task.task_type,
            "title": task.title,
            "status": task.status,
            "progress": task.progress,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
            "sourceFileName": task.source_file_name,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "retryCount": task.retry_count,
            "startedAt": task.started_at,
            "finishedAt": task.finished_at,
            "completedOutputCount": task.completed_output_count,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "effectRatingNote": task.effect_rating_note,
            "ratedAt": task.rated_at,
            "hasTranscript": task.has_transcript,
            "hasTimedTranscript": task.has_timed_transcript,
            "sourceAssetCount": task.source_asset_count,
            "editingMode": task.editing_mode,
            "isQueued": task.is_queued,
            "queuePosition": task.queue_position,
            "currentStage": monitoring.get("currentStage"),
            "activeWorkerInstanceId": monitoring.get("activeWorkerInstanceId"),
            "plannedClipCount": monitoring.get("plannedClipCount", 0),
            "renderedClipCount": monitoring.get("renderedClipCount", 0),
            "diagnosisSeverity": diagnosis.get("severity"),
            "diagnosisCode": diagnosis.get("code"),
            "diagnosisHint": diagnosis.get("hint"),
            "recommendedAction": diagnosis.get("recommendedAction"),
            "failureReason": failure.get("reason"),
            "failureStage": failure.get("stage"),
            "failureClipIndex": failure.get("clipIndex"),
            "thumbnailUrl": self._task_thumbnail_url(task, monitoring),
        }

    def to_detail(self, task: TaskRecord) -> dict[str, Any]:
        row = dict(self.to_list_item(task))
        monitoring = self._monitoring_summary(task)
        row["artifactDirectories"] = monitoring.get("artifactDirectories", {})
        row["introTemplate"] = task.intro_template
        row["outroTemplate"] = task.outro_template
        row["creativePrompt"] = task.creative_prompt
        row["taskSeed"] = task.task_seed
        row["effectRating"] = task.effect_rating
        row["effectRatingNote"] = task.effect_rating_note
        row["ratedAt"] = task.rated_at
        row["errorMessage"] = task.error_message
        row["failureReason"] = self._failure_summary(task).get("reason")
        row["failureStage"] = self._failure_summary(task).get("stage")
        row["failureClipIndex"] = self._failure_summary(task).get("clipIndex")
        row["transcriptPreview"] = task.transcript_text[:min(220, len(task.transcript_text))] if task.transcript_text else None
        row["transcriptCueCount"] = 0
        row["source"] = None
        row["sourceAssets"] = []
        row["storyboardScript"] = task.storyboard_script
        row["materials"] = task.materials
        row["executionContext"] = task.execution_context
        row["requestSnapshot"] = task.request_snapshot or {}
        row["durationDiagnostics"] = []
        row["sourceAssetIds"] = []
        row["sourceFileNames"] = []
        row["plan"] = []
        row["activeAttemptId"] = task.active_attempt_id
        row["attempts"] = task.attempts
        row["stageRuns"] = task.stage_runs
        row["outputs"] = task.outputs
        row["monitoring"] = monitoring
        return row

    def to_showcase_item(self, task: TaskRecord) -> dict[str, Any]:
        monitoring = self._monitoring_summary(task)
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
            "sourceFileName": task.source_file_name,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "completedOutputCount": task.completed_output_count,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "description": task.title,
            "previewUrl": monitoring.get("latestVideoOutputUrl", ""),
            "downloadUrl": monitoring.get("latestVideoOutputUrl", ""),
            "joinName": monitoring.get("latestJoinName", ""),
            "models": task.request_snapshot or {},
            "media": {},
        }

    def _monitoring_summary(self, task: TaskRecord) -> dict[str, Any]:
        active_attempt = None
        if task.active_attempt_id:
            for attempt in task.attempts:
                if attempt.get("attemptId") == task.active_attempt_id:
                    active_attempt = attempt
                    break
        if active_attempt is None and task.attempts:
            active_attempt = max(task.attempts, key=lambda a: _string_value(a.get("startedAt", "")))
        active_attempt = active_attempt or {}

        latest_trace = max(task.trace, key=lambda t: _string_value(t.get("timestamp", "")), default={}) if task.trace else {}
        latest_stage_run = max(task.stage_runs, key=lambda s: _string_value(s.get("startedAt", "")), default={}) if task.stage_runs else {}
        latest_video_output = max(
            [o for o in task.outputs if _TaskResultTypes.is_primary_video(o.get("resultType"))],
            key=lambda o: _int_value(o.get("clipIndex"), 0), default={},
        )
        latest_join_output = max(
            [o for o in task.outputs if _TaskResultTypes.is_join(o.get("resultType"))],
            key=lambda o: _int_value(o.get("clipIndex"), 0), default={},
        )

        rendered_clip_indices = sorted([
            _int_value(o.get("clipIndex"), 0)
            for o in task.outputs if _TaskResultTypes.is_primary_video(o.get("resultType")) and _int_value(o.get("clipIndex"), 0) > 0
        ])
        planned_clip_count = _int_value((task.execution_context or {}).get("plannedClipCount"), 0)
        if planned_clip_count <= 0:
            planned_clip_count = len(_list_value((task.execution_context or {}).get("clipPrompts")))

        ctx = task.execution_context or {}

        return {
            "currentStage": _first_non_blank(
                _string_value(ctx.get("currentStage")),
                _string_value(latest_stage_run.get("stageName")),
                _string_value(latest_stage_run.get("stage")),
                _string_value(active_attempt.get("stageName")),
                _string_value(active_attempt.get("resumeFromStage")),
                _string_value(latest_trace.get("stage")),
            ),
            "activeWorkerInstanceId": _first_non_blank(
                _string_value(active_attempt.get("workerInstanceId")),
                _string_value(ctx.get("workerInstanceId")),
                _string_value(latest_stage_run.get("workerInstanceId")),
                _string_value(latest_trace.get("workerInstanceId")),
            ),
            "plannedClipCount": planned_clip_count,
            "renderedClipCount": len(rendered_clip_indices),
            "latestVideoOutputUrl": _first_non_blank(
                _string_value(latest_video_output.get("downloadUrl")),
                _string_value(latest_video_output.get("previewUrl")),
            ),
            "latestJoinName": _first_non_blank(
                _string_value(ctx.get("latestJoinName")),
                _string_value(_map_value(latest_join_output.get("extra")).get("joinName")),
            ),
            "latestJoinOutputUrl": _first_non_blank(
                _string_value(ctx.get("latestJoinOutputUrl")),
                _string_value(latest_join_output.get("downloadUrl")),
            ),
            "artifactDirectories": {},
            "latestVideoOutput": latest_video_output,
            "latestJoinOutput": latest_join_output,
        }

    def _diagnosis_summary(self, task: TaskRecord, monitoring: dict[str, Any]) -> dict[str, Any]:
        return {"severity": "info", "code": "healthy", "hint": "任务正常", "recommendedAction": "继续观察"}

    def _failure_summary(self, task: TaskRecord) -> dict[str, Any]:
        return {"reason": None, "stage": None, "clipIndex": None}

    def _task_thumbnail_url(self, task: TaskRecord, monitoring: dict[str, Any]) -> str:
        return ""


# ===================================================================
# Re-exports
# ===================================================================

__all__ = [
    "TaskWorkerPipelineHandler",
    "TaskWorkerRenderStageService",
    "TaskWorkerStatusStageService",
    "TaskExecutionRuntimeSupport",
    "TaskExecutionArtifactAssembler",
    "JoinOutputService",
    "TaskViewMapper",
    "TaskWorkerExecutionContext",
    "TaskExecutionAbortedException",
    "GenerationProviderException",
    "GenerationApplicationServiceStub",
    "LocalMediaArtifactServiceStub",
    "TaskStoryboardPlannerStub",
    "ModelRuntimePropertiesResolverStub",
]
