"""Persist generated workflow keyframes and their material assets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage
from backend.models.workflow import BizStageWorkflow
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.shared import random_id, trim

STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"


@dataclass(frozen=True)
class KeyframeTarget:
    character: dict[str, Any] | None
    clip: dict[str, Any] | None

    @property
    def is_character_sheet(self) -> bool:
        return self.character is not None


@dataclass(frozen=True)
class GeneratedFrame:
    output_url: str
    remote_url: str
    mime_type: str
    width: int
    height: int
    run_id: str = ""
    model_info: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    generation_result_id: str = ""


class WorkflowKeyframePersistence:
    """Create material and stage-version rows for generated keyframes."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        row_factory: WorkflowPersistenceRowFactory,
        thumbnail_resolver: Any,
    ) -> None:
        self._db = db
        self._row_factory = row_factory
        self._thumbnail_resolver = thumbnail_resolver

    def persist_complete(
        self,
        workflow: BizStageWorkflow,
        target: KeyframeTarget,
        clip_index: int,
        version_no: int,
        version_id: str,
        start: GeneratedFrame,
        end: GeneratedFrame | None,
        prompt: str,
        reused_previous_tail: bool,
    ) -> None:
        character = target.character
        clip = target.clip
        asset = self._row_factory.create_material_asset(
            wf=workflow,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_no,
            media_type="image",
            title=f"{character.get('name')} 三视图" if character else f"镜头 {clip_index} 关键帧",
            public_url=start.output_url,
            mime_type=start.mime_type,
            width=start.width,
            height=start.height,
            duration_seconds=0,
            origin_provider=trim((start.metadata or {}).get("provider")),
            origin_model=trim((start.metadata or {}).get("providerModel")),
            remote_url=start.remote_url,
            thumbnail_url=self._thumbnail_resolver("image", start.output_url),
            metadata={
                "runId": start.generation_result_id,
                "prompt": prompt,
                "remoteSourceUrl": start.remote_url,
                "reusedPreviousTailFrame": reused_previous_tail,
                "characterName": character.get("name") if character else "",
                "clip": clip or {},
            },
        )
        self._db.add(asset)
        output_summary: dict[str, Any] = {
            "fileUrl": start.output_url,
            "previewUrl": start.output_url,
            "width": start.width,
            "height": start.height,
            "prompt": prompt,
            "runId": start.run_id,
            "remoteSourceUrl": start.remote_url,
        }
        input_summary: dict[str, Any] = {"clipIndex": clip_index, "prompt": prompt}
        title = f"镜头 {clip_index} 关键帧 {version_no}"
        if character:
            output_summary.update(
                {
                    "sheetUrl": start.output_url,
                    "characterName": character.get("name", ""),
                    "characterAppearance": character.get("appearance", ""),
                }
            )
            input_summary.update(
                {
                    "variantKind": VARIANT_KIND_CHARACTER_SHEET,
                    "characterName": character.get("name", ""),
                    "appearance": character.get("appearance", ""),
                }
            )
            title = f"{character.get('name')} 三视图 {version_no}"
        else:
            end_remote_url = (end.remote_url or end.output_url) if end else ""
            output_summary.update(
                {
                    "startFrameUrl": start.output_url,
                    "endFrameUrl": end.output_url if end else "",
                    "startFrameRemoteUrl": start.remote_url,
                    "endFrameRemoteUrl": end_remote_url,
                    "selectedFirstFrame": True,
                    "selectedLastFrame": True,
                    "reusedPreviousTailFrame": reused_previous_tail,
                }
            )
            input_summary.update(
                {
                    "variantKind": "keyframe",
                    "shotLabel": (clip or {}).get("shotLabel", ""),
                    "scene": (clip or {}).get("scene", ""),
                }
            )
        version = self._row_factory.create_stage_version(
            wf=workflow,
            stage_version_id=version_id,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_no,
            title=title,
            status="COMPLETED",
            selected=1,
            material_asset_id=asset.material_asset_id,
            preview_url=start.output_url,
            download_url=start.output_url,
            input_summary=input_summary,
            output_summary=output_summary,
            model_call_summary={"runId": start.run_id, "modelInfo": start.model_info or {}},
        )
        self._db.add(version)
    def persist_single_frame(
        self,
        workflow: BizStageWorkflow,
        target: KeyframeTarget,
        clip_index: int,
        version_no: int,
        frame_role: str,
        is_first: bool,
        frame: GeneratedFrame,
        prompt: str,
        reused_previous_tail: bool,
    ) -> None:
        character = target.character
        clip = target.clip
        asset = self._row_factory.create_material_asset(
            wf=workflow,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_no,
            media_type="image",
            title=f"{character.get('name')} 三视图" if character else f"镜头 {clip_index} 关键帧-{frame_role}",
            public_url=frame.output_url,
            mime_type=frame.mime_type,
            width=frame.width,
            height=frame.height,
            duration_seconds=0,
            origin_provider=trim((frame.metadata or {}).get("provider")),
            origin_model=trim((frame.metadata or {}).get("providerModel")),
            remote_url=frame.remote_url,
            thumbnail_url=self._thumbnail_resolver("image", frame.output_url),
            metadata={
                "runId": frame.generation_result_id,
                "prompt": prompt,
                "remoteSourceUrl": frame.remote_url,
                "reusedPreviousTailFrame": reused_previous_tail,
                "characterName": character.get("name") if character else "",
                "clip": clip or {},
                "frameRole": frame_role,
            },
        )
        self._db.add(asset)
        output_summary: dict[str, Any] = {
            "fileUrl": frame.output_url,
            "previewUrl": frame.output_url,
            "width": frame.width,
            "height": frame.height,
            "prompt": prompt,
            "runId": frame.run_id,
            "remoteSourceUrl": frame.remote_url,
            "frameRole": frame_role,
        }
        input_summary: dict[str, Any] = {"clipIndex": clip_index, "prompt": prompt, "frameRole": frame_role}
        if is_first:
            output_summary.update(
                {
                    "startFrameUrl": frame.output_url,
                    "startFrameRemoteUrl": frame.remote_url,
                    "selectedFirstFrame": True,
                    "reusedPreviousTailFrame": reused_previous_tail,
                }
            )
            input_summary.update(
                {
                    "variantKind": "keyframe",
                    "shotLabel": (clip or {}).get("shotLabel", ""),
                    "scene": (clip or {}).get("scene", ""),
                }
            )
        else:
            output_summary.update(
                {
                    "endFrameUrl": frame.output_url,
                    "endFrameRemoteUrl": frame.remote_url,
                    "selectedLastFrame": True,
                }
            )
            input_summary.update(
                {
                    "variantKind": "keyframe_end",
                    "shotLabel": (clip or {}).get("shotLabel", ""),
                    "scene": (clip or {}).get("scene", ""),
                }
            )
        version = self._row_factory.create_stage_version(
            wf=workflow,
            stage_version_id=f"fv_{random_id()[:12]}",
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_no,
            title=f"镜头 {clip_index} 关键帧 {frame_role} {version_no}",
            status="COMPLETED",
            selected=0,
            material_asset_id=asset.material_asset_id,
            preview_url=frame.output_url,
            download_url=frame.output_url,
            input_summary=input_summary,
            output_summary=output_summary,
            model_call_summary={"runId": frame.run_id, "modelInfo": frame.model_info or {}},
        )
        self._db.add(version)
