"""Build script, image, character-sheet, workspace-image, and video run requests."""

from __future__ import annotations

import uuid
from typing import Any

from backend.domain.generation_run import DEFAULT_OPENAI_IMAGE_MODEL
from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_assembler import _TaskArtifactNaming
from backend.services.task_execution_prompt_support import (
    append_aspect_ratio_instruction,
    build_character_sheet_prompt,
    build_video_clip_execution_prompt,
    build_workspace_image_prompt,
)
from backend.services.task_reference_image_support import compatible_image_reference_urls, reference_image_urls
from backend.shared import first_non_blank, string_value


class TaskGenerationRequestFactory:
    """Create provider-neutral generation requests from immutable task snapshots."""

    def __init__(self, model_resolver: Any, local_media_artifact_service: Any | None = None) -> None:
        self._model_resolver = model_resolver
        self._local_media_artifact_service = local_media_artifact_service

    def build_script_run_request(self, task: TaskRecord) -> dict[str, Any]:
        request: dict[str, Any] = {
            "kind": "script",
            "input": {"text": first_non_blank(task.transcript_text, task.creative_prompt, task.title)},
            "model": {"textAnalysisModel": self.text_analysis_model(task)},
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileName": _TaskArtifactNaming.storyboard_file_name(task, "md"),
            },
        }
        self.put_user_auth(request, task)
        return request

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
        normalized_frame_role = self.normalize_frame_role(frame_role)
        input_data: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": normalized_frame_role,
        }
        if duration_seconds > 0:
            input_data["durationSeconds"] = duration_seconds
        image_model = self.image_model(task)
        image_seed = self.image_seed(task, clip_index)
        if image_seed is not None and self._model_resolver.supports_seed(image_model):
            input_data["seed"] = image_seed
        raw_references = ([reference_image_url] if reference_image_url else []) + list(reference_image_urls or [])
        compatible = compatible_image_reference_urls(raw_references, self._local_media_artifact_service)
        if compatible:
            input_data["referenceImageUrl"] = compatible[0]
            input_data["referenceImageUrls"] = compatible
        request: dict[str, Any] = {
            "kind": "image",
            "input": input_data,
            "model": {
                "textAnalysisModel": self.text_analysis_model(task),
                "providerModel": image_model,
            },
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
        self.put_user_auth(request, task)
        return request

    def build_character_sheet_run_request(
        self,
        task: TaskRecord,
        character_index: int,
        character: Any,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        name = string_value(getattr(character, "name", ""))
        appearance = string_value(getattr(character, "appearance", ""))
        definition = string_value(getattr(character, "definition", ""))
        image_model = self.image_model(task)
        input_data: dict[str, Any] = {
            "prompt": build_character_sheet_prompt(name, first_non_blank(definition, appearance)),
            "width": width,
            "height": height,
            "frameRole": "sheet",
        }
        image_seed = self.image_seed(task, 1000 + max(1, character_index))
        if image_seed is not None and self._model_resolver.supports_seed(image_model):
            input_data["seed"] = image_seed
        request: dict[str, Any] = {
            "kind": "image",
            "input": input_data,
            "model": {
                "textAnalysisModel": self.text_analysis_model(task),
                "providerModel": image_model,
            },
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileStem": f"character{max(1, character_index)}-sheet",
            },
            "metadata": {
                "relatedTaskId": string_value(task.id),
                "clipIndex": 1000 + max(1, character_index),
                "frameRole": "sheet",
                "variantKind": "character_sheet",
                "characterIndex": max(1, character_index),
                "characterName": name,
            },
        }
        self.put_user_auth(request, task)
        return request

    def build_workspace_image_run_request(
        self,
        task: TaskRecord,
        width: int,
        height: int,
        output_index: int = 1,
    ) -> dict[str, Any]:
        snapshot = task.request_snapshot or {}
        asset_type = string_value(snapshot.get("assetType", "")) or (
            "character_sheet" if task.task_type == "character_sheet" else "free"
        )
        prompt = first_non_blank(string_value(snapshot.get("creativePrompt", "")), task.creative_prompt, task.title)
        references = reference_image_urls(task)
        prompt = build_workspace_image_prompt(asset_type, task.title, prompt, bool(references))
        prompt = append_aspect_ratio_instruction(prompt, task.aspect_ratio)
        input_data: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": asset_type,
        }
        if asset_type == "free":
            input_data["promptPassthrough"] = True
        image_model = self.image_model(task)
        compatible = compatible_image_reference_urls(references, self._local_media_artifact_service)
        if compatible:
            input_data["referenceImageUrl"] = compatible[0]
            input_data["referenceImageUrls"] = compatible
        seed = self.task_seed(task)
        if seed is not None and self._model_resolver.supports_seed(image_model):
            input_data["seed"] = seed
        request: dict[str, Any] = {
            "kind": "image",
            "input": input_data,
            "model": {
                "textAnalysisModel": self.text_analysis_model(task),
                "providerModel": image_model,
            },
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileStem": "workspace-image" if output_index <= 1 else f"workspace-image-{output_index}",
                "requireRemoteSourceUrl": False,
            },
            "metadata": {
                "relatedTaskId": string_value(task.id),
                "taskType": task.task_type,
                "assetType": asset_type,
                "outputIndex": max(1, output_index),
                "referenceImageCount": len(compatible),
            },
        }
        self.put_user_auth(request, task)
        return request

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
            "prompt": build_video_clip_execution_prompt(prompt),
            "videoSize": video_size,
            "durationSeconds": duration_seconds,
            "minDurationSeconds": min_duration_seconds,
            "maxDurationSeconds": max_duration_seconds,
            "firstFrameUrl": first_frame_url,
            "generateAudio": self.default_video_generate_audio(),
            "returnLastFrame": True,
        }
        if last_frame_url:
            input_data["lastFrameUrl"] = last_frame_url
        seed = self.task_seed(task)
        if seed is not None:
            input_data["seed"] = seed
        request: dict[str, Any] = {
            "kind": "video",
            "input": input_data,
            "model": {
                "textAnalysisModel": self.text_analysis_model(task),
                "providerModel": self.video_model(task),
            },
            "storage": {
                "relativeDir": _TaskArtifactNaming.task_running_relative_dir(task),
                "fileStem": f"clip{max(1, clip_index)}",
            },
            "metadata": {"relatedTaskId": string_value(task.id), "clipIndex": max(1, clip_index)},
        }
        self.put_user_auth(request, task)
        return request

    def text_analysis_model(self, task: TaskRecord) -> str:
        return self.required_snapshot_model(task, "textAnalysisModel", "文本模型")

    def image_model(self, task: TaskRecord) -> str:
        snapshot = task.request_snapshot or {}
        return first_non_blank(string_value(snapshot.get("imageModel", "")), DEFAULT_OPENAI_IMAGE_MODEL)

    def video_model(self, task: TaskRecord) -> str:
        return self.required_snapshot_model(task, "videoModel", "视频模型")

    @staticmethod
    def required_snapshot_model(task: TaskRecord, field_name: str, label: str) -> str:
        configured = string_value((task.request_snapshot or {}).get(field_name, ""))
        if configured:
            return configured
        raise ValueError(f"任务缺少必选模型：{label}（{field_name}）")

    @staticmethod
    def task_seed(task: TaskRecord) -> int | None:
        configured = (task.request_snapshot or {}).get("seed")
        return configured if isinstance(configured, int) else task.task_seed

    def image_seed(self, task: TaskRecord, clip_index: int) -> int | None:
        seed = self.task_seed(task)
        if seed is not None:
            return seed
        identity = first_non_blank(task.id, task.title, task.creative_prompt, "task")
        raw = uuid.uuid5(uuid.NAMESPACE_OID, f"{identity}:clip:{max(1, clip_index)}:keyframe").int >> 64
        return (raw % (2**31 - 2)) + 1

    @staticmethod
    def normalize_frame_role(frame_role: str) -> str:
        return "last" if frame_role.lower() == "last" else "first"

    def default_video_generate_audio(self) -> bool:
        try:
            value = self._model_resolver.value(
                "catalog.defaults",
                "video_generate_audio",
                fallback="true",
            )
        except TypeError:
            value = self._model_resolver.value(
                "catalog.defaults",
                "video_generate_audio",
                default="true",
            )
        return bool(value) and value.lower() in ("true", "1", "yes")

    @staticmethod
    def put_user_auth(request: dict[str, Any], task: TaskRecord) -> None:
        if task.owner_user_id is not None:
            request["auth"] = {"userId": str(task.owner_user_id)}
