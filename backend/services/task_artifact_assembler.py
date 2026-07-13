from __future__ import annotations

from typing import Any

from backend.domain.media_artifacts import file_ext_or_default, file_name_from_url
from backend.domain.media_result import (
    media_output_url,
    remote_source_url,
    result_metadata,
)
from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import TEXT, VIDEO, VIDEO_JOIN
from backend.services.task_artifact_storage import TaskArtifactStorage
from backend.services.task_artifact_support import (
    _JOIN_OUTPUT_CLIP_INDEX_BASE,
    _artifact_public_url,
    _bool_value,
    _float_value,
    _int_value,
    _TaskArtifactNaming,
)
from backend.services.task_image_material_assembler import TaskImageMaterialAssembler
from backend.services.task_material_factory import TaskMaterialFactory
from backend.services.task_result_assembler import TaskResultAssembler
from backend.shared import string_value


class TaskExecutionArtifactAssembler:
    """Assembles execution artifacts, material rows, and result rows from task data."""

    def __init__(self, local_media_artifact_service: Any | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service
        self._material_factory = TaskMaterialFactory(local_media_artifact_service)
        self._storage = TaskArtifactStorage(local_media_artifact_service)
        self._image_materials = TaskImageMaterialAssembler(self._storage, self._material_factory)
        self._result_assembler = TaskResultAssembler(self)

    def create_text_material(self, task: TaskRecord, run: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        file_url = string_value(result.get("markdownUrl", ""))
        artifact = self._storage.normalize(
            task,
            file_url,
            _TaskArtifactNaming.storyboard_file_name(task, file_ext_or_default(file_name_from_url(file_url), "md")),
            "storyboard",
        )
        return self._create_material(
            task,
            run,
            TEXT,
            f"{task.title} 分镜脚本",
            _artifact_public_url(artifact, file_url),
            _artifact_public_url(artifact, file_url),
            string_value(result.get("mimeType", "text/markdown")),
            0.0,
            0,
            0,
            False,
            1,
            "storyboard",
            {},
            {"taskArtifact": True},
            "",
        )

    def create_image_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        clip_index: int,
        frame_role: str,
    ) -> dict[str, Any]:
        return self._image_materials.create_image_material(task, run, result, clip_index, frame_role)

    def create_character_sheet_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        character_index: int,
        character: Any,
    ) -> dict[str, Any]:
        return self._image_materials.create_character_sheet_material(task, run, result, character_index, character)

    def create_workspace_image_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        output_index: int = 1,
    ) -> dict[str, Any]:
        return self._image_materials.create_workspace_image_material(task, run, result, output_index)

    def create_reference_frame_material(
        self,
        task: TaskRecord,
        clip_index: int,
        source_url: str,
        frame_role: str,
    ) -> dict[str, Any]:
        return self._image_materials.create_reference_frame_material(task, clip_index, source_url, frame_role)

    def create_video_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        clip_index: int,
        fallback_duration_seconds: int,
    ) -> dict[str, Any]:
        metadata = result_metadata(result)
        output_url = media_output_url(result, metadata)
        artifact = self._storage.normalize(
            task,
            output_url,
            _TaskArtifactNaming.clip_file_name(clip_index, file_ext_or_default(file_name_from_url(output_url), "mp4")),
            "clip",
        )
        return self._create_material(
            task,
            run,
            VIDEO,
            f"{task.title} 片段输出",
            _artifact_public_url(artifact, output_url),
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "video/mp4")),
            _float_value(result.get("durationSeconds"), float(fallback_duration_seconds)),
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            _bool_value(result.get("hasAudio")),
            clip_index,
            "clip",
            metadata,
            {
                "taskArtifact": True,
                "clipIndex": clip_index,
                "firstFrameUrl": string_value(metadata.get("firstFrameUrl")),
                "lastFrameUrl": self.extract_last_frame_url(result),
                "requestedLastFrameUrl": string_value(metadata.get("requestedLastFrameUrl")),
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
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
        return self._result_assembler.create_result(
            task,
            video_run,
            video_result,
            video_material,
            image_material,
            video_model_call,
            resolved_last_frame_url,
            clip_index,
            fallback_duration_seconds,
            min_duration_seconds,
            max_duration_seconds,
        )

    def create_join_material(
        self,
        task: TaskRecord,
        artifact: Any,
        end_clip_index: int,
        source_video_urls: list[str],
        total_duration_seconds: float,
    ) -> dict[str, Any]:
        public_url = _artifact_public_url(artifact, "")
        clip_index = _JOIN_OUTPUT_CLIP_INDEX_BASE + max(1, end_clip_index)
        metadata = {
            "taskId": task.id,
            "kind": VIDEO_JOIN,
            "clipIndex": clip_index,
            "joinName": _TaskArtifactNaming.join_name(end_clip_index),
            "clipIndices": list(range(1, max(1, end_clip_index) + 1)),
            "sourceVideoUrls": source_video_urls,
        }
        return self._create_material(
            task,
            {
                "id": f"join_{task.id}_{end_clip_index}",
                "result": {
                    "modelInfo": {
                        "provider": "local",
                        "providerModel": "ffmpeg",
                        "resolvedModel": "ffmpeg",
                    }
                },
            },
            VIDEO,
            f"{task.title} 完整视频",
            public_url,
            public_url,
            "video/mp4",
            total_duration_seconds,
            0,
            0,
            True,
            clip_index,
            VIDEO_JOIN,
            metadata,
            metadata,
            "",
        )

    def create_join_result(
        self,
        task: TaskRecord,
        join_material: dict[str, Any],
        end_clip_index: int,
        source_video_urls: list[str],
        total_duration_seconds: float,
    ) -> dict[str, Any]:
        return self._result_assembler.create_join_result(
            task, join_material, end_clip_index, source_video_urls, total_duration_seconds
        )

    def create_image_result(
        self,
        task: TaskRecord,
        image_run: dict[str, Any],
        image_result: dict[str, Any],
        image_material: dict[str, Any],
        model_call: dict[str, Any],
        output_index: int = 1,
    ) -> dict[str, Any]:
        return self._result_assembler.create_image_result(
            task, image_run, image_result, image_material, model_call, output_index
        )

    def normalize_optional_task_artifact(self, task: TaskRecord, source_url: str, target_file_name: str) -> None:
        self._storage.normalize_optional(task, source_url, target_file_name)

    def extract_last_frame_url(self, value: Any) -> str:
        return self._storage.extract_last_frame_url(value)

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
        return self._material_factory.create(
            task,
            run,
            media_type,
            title,
            file_url,
            preview_url,
            mime_type,
            duration_seconds,
            width,
            height,
            has_audio,
            clip_index,
            kind,
            source_metadata,
            extra_metadata,
            remote_url,
        )

    def _file_size(self, absolute_path: str) -> int:
        return self._storage.file_size(absolute_path)

    def _resolve_absolute_path(self, file_url: str) -> str:
        return self._storage.resolve_absolute_path(file_url)
