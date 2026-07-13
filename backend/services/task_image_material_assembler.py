"""Assemble image-like task material rows."""

from __future__ import annotations

from typing import Any

from backend.domain.media_artifacts import file_ext_or_default, file_name_from_url, image_mime_type
from backend.domain.media_result import media_output_url, remote_source_url, result_metadata
from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import IMAGE
from backend.services.task_artifact_storage import TaskArtifactStorage
from backend.services.task_artifact_support import _artifact_public_url, _int_value, _TaskArtifactNaming
from backend.services.task_material_factory import TaskMaterialFactory
from backend.shared import string_value


class TaskImageMaterialAssembler:
    """Own image material normalization, naming and metadata projection."""

    def __init__(
        self,
        storage: TaskArtifactStorage,
        material_factory: TaskMaterialFactory,
    ) -> None:
        self._storage = storage
        self._material_factory = material_factory

    def create_image_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        clip_index: int,
        frame_role: str,
    ) -> dict[str, Any]:
        output_url = string_value(result.get("outputUrl", ""))
        metadata = result_metadata(result)
        normalized_role = "last" if frame_role.lower() == "last" else "first"
        artifact = self._storage.normalize(
            task,
            output_url,
            _TaskArtifactNaming.clip_frame_file_name(
                clip_index,
                normalized_role,
                file_ext_or_default(file_name_from_url(output_url), "png"),
            ),
            "keyframe",
        )
        return self._create(
            task,
            run,
            f"{task.title} {'尾帧关键画面' if normalized_role == 'last' else '首帧关键画面'}",
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "image/png")),
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            clip_index,
            f"keyframe-{normalized_role}",
            metadata,
            {
                "taskArtifact": True,
                "clipIndex": clip_index,
                "frameRole": normalized_role,
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_character_sheet_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        character_index: int,
        character: Any,
    ) -> dict[str, Any]:
        output_url = string_value(result.get("outputUrl", ""))
        metadata = result_metadata(result)
        index = max(1, character_index)
        artifact = self._storage.normalize(
            task,
            output_url,
            f"character{index}-sheet.{file_ext_or_default(file_name_from_url(output_url), 'png')}",
            "keyframe",
        )
        name = string_value(getattr(character, "name", ""))
        appearance = string_value(getattr(character, "appearance", ""))
        return self._create(
            task,
            run,
            f"{task.title} {name or f'角色{index}'} 三视图",
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "image/png")),
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            1000 + index,
            "character_sheet",
            metadata,
            {
                "taskArtifact": True,
                "variantKind": "character_sheet",
                "characterIndex": index,
                "characterName": name,
                "characterAppearance": appearance,
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_workspace_image_material(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        result: dict[str, Any],
        output_index: int = 1,
    ) -> dict[str, Any]:
        metadata = result_metadata(result)
        output_url = media_output_url(result, metadata)
        index = max(1, output_index)
        suffix = "" if index <= 1 else f"-{index}"
        artifact = self._storage.normalize(
            task,
            output_url,
            f"workspace-image-{task.id}{suffix}.{file_ext_or_default(file_name_from_url(output_url), 'png')}",
            "keyframe",
        )
        asset_type = string_value((task.request_snapshot or {}).get("assetType", ""))
        if not asset_type or asset_type in {"image_generation", "image_to_image", "video_generation", "generation"}:
            asset_type = "free"
        return self._create(
            task,
            run,
            task.title,
            _artifact_public_url(artifact, output_url),
            string_value(result.get("mimeType", "image/png")),
            _int_value(result.get("width"), 0),
            _int_value(result.get("height"), 0),
            index,
            asset_type or "free",
            metadata,
            {
                "taskArtifact": True,
                "assetType": asset_type,
                "taskType": task.task_type,
                "outputIndex": index,
                "remoteSourceUrl": remote_source_url(metadata),
            },
            remote_source_url(metadata),
        )

    def create_reference_frame_material(
        self,
        task: TaskRecord,
        clip_index: int,
        source_url: str,
        frame_role: str,
    ) -> dict[str, Any]:
        normalized_role = "last" if frame_role.lower() == "last" else "first"
        target_name = _TaskArtifactNaming.clip_frame_file_name(
            clip_index, normalized_role, file_ext_or_default(file_name_from_url(source_url), "png")
        )
        file_url = string_value(source_url)
        try:
            artifact = self._storage.normalize(task, source_url, target_name, "keyframe")
            file_url = _artifact_public_url(artifact, file_url)
        except Exception:  # noqa: S110 — best-effort artifact normalization
            pass
        return self._create(
            task,
            {},
            f"{task.title} {'尾帧关键画面' if normalized_role == 'last' else '首帧关键画面'}",
            file_url,
            image_mime_type(target_name),
            0,
            0,
            clip_index,
            f"keyframe-{normalized_role}",
            {},
            {
                "taskArtifact": file_url.startswith("/storage/"),
                "clipIndex": clip_index,
                "frameRole": normalized_role,
                "remoteSourceUrl": string_value(source_url),
                "reusedFromPreviousClip": True,
            },
            string_value(source_url),
        )

    def _create(
        self,
        task: TaskRecord,
        run: dict[str, Any],
        title: str,
        file_url: str,
        mime_type: str,
        width: int,
        height: int,
        clip_index: int,
        kind: str,
        source_metadata: dict[str, Any],
        extra_metadata: dict[str, Any],
        remote_url: str,
    ) -> dict[str, Any]:
        return self._material_factory.create(
            task,
            run,
            IMAGE,
            title,
            file_url,
            file_url,
            mime_type,
            0.0,
            width,
            height,
            False,
            clip_index,
            kind,
            source_metadata,
            extra_metadata,
            remote_url,
        )
