from __future__ import annotations

from typing import Any

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_generation_request_factory import TaskGenerationRequestFactory
from backend.services.task_worker_status_stage_service import TaskExecutionAbortedException
from backend.shared import first_non_blank, string_value


def _resolver_int_value(resolver: Any, section: str, key: str, fallback: int) -> int:
    try:
        return resolver.int_value(section, key, fallback=fallback)
    except TypeError:
        return resolver.int_value(section, key, default=fallback)


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
        self._request_factory = TaskGenerationRequestFactory(
            self._model_resolver,
            local_media_artifact_service,
        )

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
            "16:9": [2560, 1440],
            "9:16": [1440, 2560],
            "9:20": [1728, 3840],
            "1:1": [3072, 3072],
            "21:9": [3024, 1296],
            "3:2": [2496, 1664],
            "2:3": [1664, 2496],
            "4:3": [3072, 2304],
            "3:4": [2304, 3072],
        }
        return aspect_map.get(task.aspect_ratio, [1440, 2560])

    def resolve_workspace_image_dimensions(self, task: TaskRecord) -> list[int]:
        snapshot = task.request_snapshot or {}
        image_size = string_value(snapshot.get("imageSize", ""))
        if image_size:
            parsed = self._parse_dimensions(image_size)
            if parsed:
                return parsed
        aspect_map = {
            "16:9": [3840, 2160],
            "9:16": [2160, 3840],
            "9:20": [1728, 3840],
            "1:1": [2880, 2880],
            "21:9": [3808, 1632],
            "3:2": [3504, 2336],
            "2:3": [2336, 3504],
            "4:3": [3264, 2448],
            "3:4": [2448, 3264],
        }
        return aspect_map.get(task.aspect_ratio, [2160, 3840])

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
        configured_default = _resolver_int_value(self._model_resolver, "catalog.defaults", "video_duration_seconds", 10)
        return max(1, configured_default)

    def resolve_workspace_image_output_count(self, task: TaskRecord, max_count: int = 4) -> int:
        snapshot = task.request_snapshot or {}
        raw = snapshot.get("outputCount")
        if isinstance(raw, dict):
            if raw.get("auto", True):
                return 1
            raw = raw.get("count")
        elif raw is None or string_value(raw).lower() == "auto":
            return 1
        try:
            count = int(raw)
        except (TypeError, ValueError):
            return 1
        return max(1, min(max_count, count))

    def assert_task_still_active(self, task: TaskRecord) -> None:
        if self._task_repository is None:
            return
        if TaskStatus.is_execution_active(TaskStatus(task.status) if TaskStatus(task.status) else None):
            return
        raise TaskExecutionAbortedException(task.status, first_non_blank(task.error_message, "任务已停止执行。"))

    def build_script_run_request(self, task: TaskRecord) -> dict[str, Any]:
        return self._request_factory.build_script_run_request(task)

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
        reference_image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._request_factory.build_image_run_request(
            task,
            clip_index,
            prompt,
            width,
            height,
            reference_image_url,
            duration_seconds,
            frame_role,
            reference_image_urls,
        )

    def build_character_sheet_run_request(
        self,
        task: TaskRecord,
        character_index: int,
        character: Any,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        return self._request_factory.build_character_sheet_run_request(
            task,
            character_index,
            character,
            width,
            height,
        )

    def build_workspace_image_run_request(
        self,
        task: TaskRecord,
        width: int,
        height: int,
        output_index: int = 1,
    ) -> dict[str, Any]:
        return self._request_factory.build_workspace_image_run_request(task, width, height, output_index)

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
        return self._request_factory.build_video_run_request(
            task,
            clip_index,
            prompt,
            video_size,
            duration_seconds,
            min_duration_seconds,
            max_duration_seconds,
            first_frame_url,
            last_frame_url,
        )

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
        return self._request_factory.text_analysis_model(task)

    def _image_model(self, task: TaskRecord) -> str:
        return self._request_factory.image_model(task)

    def _video_model(self, task: TaskRecord) -> str:
        return self._request_factory.video_model(task)

    def _required_snapshot_model(self, task: TaskRecord, field_name: str, label: str) -> str:
        return self._request_factory.required_snapshot_model(task, field_name, label)

    def _task_seed(self, task: TaskRecord) -> int | None:
        return self._request_factory.task_seed(task)

    def _image_seed(self, task: TaskRecord, clip_index: int) -> int | None:
        return self._request_factory.image_seed(task, clip_index)

    def _normalize_frame_role(self, frame_role: str) -> str:
        return self._request_factory.normalize_frame_role(frame_role)

    def _default_video_generate_audio(self) -> bool:
        return self._request_factory.default_video_generate_audio()

    def _put_user_auth(self, request: dict[str, Any], task: TaskRecord) -> None:
        self._request_factory.put_user_auth(request, task)
