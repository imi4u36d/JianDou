from __future__ import annotations

from typing import Any

from backend.domain.enums import WorkflowStage
from backend.domain.generation_run import DEFAULT_OPENAI_IMAGE_MODEL
from backend.models.workflow import BizStageWorkflow

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"
VARIANT_KIND_VISUAL_ASSET = "visual_asset"


def _trim(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = str(value).strip()
    return stripped if stripped else fallback.strip()


class WorkflowGenerationRequestBuilder:
    """Build generation-service request payloads for workflow stages."""

    @staticmethod
    def image_model(wf: BizStageWorkflow) -> str:
        return _trim(wf.image_model, DEFAULT_OPENAI_IMAGE_MODEL)

    def build_storyboard_request(self, wf: BizStageWorkflow) -> dict[str, Any]:
        return {
            "kind": "script",
            "input": {
                "text": wf.transcript_text,
                "sourceText": wf.transcript_text,
            },
            "model": {
                "textAnalysisModel": _trim(wf.text_analysis_model),
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        }

    def build_keyframe_request(
        self,
        wf: BizStageWorkflow,
        *,
        workflow_id: str,
        clip_index: int,
        width: int,
        height: int,
        character: dict[str, Any] | None,
        clip: dict[str, Any] | None,
        character_sheet_urls: list[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        is_visual_asset = character is not None
        asset_type = _trim((character or {}).get("assetType"), "character")
        prompt = (
            self.visual_asset_prompt(character)
            if is_visual_asset
            else self.keyframe_prompt(wf, clip or {})
        )
        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": "sheet" if is_visual_asset else "first",
            "seed": wf.keyframe_seed,
        }
        if character_sheet_urls:
            input_payload["referenceImageUrls"] = character_sheet_urls
        metadata = {
            "workflowId": workflow_id,
            "stage": STAGE_KEYFRAME,
            "clipIndex": clip_index,
            "variantKind": (
                VARIANT_KIND_CHARACTER_SHEET
                if is_visual_asset and asset_type == "character"
                else VARIANT_KIND_VISUAL_ASSET if is_visual_asset else "keyframe"
            ),
        }
        if is_visual_asset:
            metadata["assetType"] = asset_type
        request = {
            "kind": "image",
            "input": input_payload,
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": self.image_model(wf),
            },
            "storage": {
                "relativeDir": f"tasks/{workflow_id}/running",
                "fileStem": f"clip{clip_index}-first",
            },
            "metadata": metadata,
            "auth": {
                "userId": wf.owner_user_id,
            },
        }
        return request, prompt

    def build_start_keyframe_from_tail_frame_request(
        self,
        wf: BizStageWorkflow,
        *,
        workflow_id: str,
        clip_index: int,
        width: int,
        height: int,
        clip: dict[str, Any] | None,
        previous_tail_frame_remote_url: str,
        character_sheet_urls: list[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Build an image-to-image request for the start frame using the
        previous clip's tail frame as reference.

        This preserves visual continuity between consecutive clips by
        generating the next clip's start frame from the previous clip's end.
        """
        base_prompt = self.keyframe_prompt(wf, clip or {})
        prompt = (
            f"{base_prompt} "
            "This is the opening frame of a new shot that continues from the "
            "previous shot's final frame. Preserve the same character identity, "
            "and scene lighting from the reference image while "
            "advancing to the new composition described above."
        )
        # Combine tail frame + character sheets into a single reference list.
        all_refs = [previous_tail_frame_remote_url] + (character_sheet_urls or [])
        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": "first",
            "referenceImageUrl": previous_tail_frame_remote_url,
            "referenceImageUrls": all_refs,
            "seed": wf.keyframe_seed,
        }
        request = {
            "kind": "image",
            "input": input_payload,
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": self.image_model(wf),
            },
            "storage": {
                "relativeDir": f"tasks/{workflow_id}/running",
                "fileStem": f"clip{clip_index}-first",
            },
            "metadata": {
                "workflowId": workflow_id,
                "stage": STAGE_KEYFRAME,
                "clipIndex": clip_index,
                "variantKind": "keyframe",
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        }
        return request, prompt

    def build_end_keyframe_request(
        self,
        wf: BizStageWorkflow,
        *,
        workflow_id: str,
        clip_index: int,
        width: int,
        height: int,
        clip: dict[str, Any] | None,
        start_frame_remote_url: str,
        character_sheet_urls: list[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Build an image-to-image request for the end frame keyframe.

        Uses the start frame as reference image so the model produces a
        distinct end frame that preserves scene/character continuity.
        """
        base_prompt = self.keyframe_prompt(wf, clip or {})
        prompt = (
            f"{base_prompt} "
            "Focus on the end frame — advance character action, posture, "
            "or camera position from the reference image while preserving "
            "the same scene, lighting, and character identity. "
            "Do NOT reproduce the reference image exactly."
        )
        # Combine start frame + character sheets into a single reference list.
        # The generation service passes referenceImageUrls to the model;
        # referenceImageUrl alone would be dropped when referenceImageUrls is set.
        all_refs = [start_frame_remote_url] + (character_sheet_urls or [])
        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "frameRole": "last",
            "referenceImageUrl": start_frame_remote_url,
            "referenceImageUrls": all_refs,
            "seed": wf.keyframe_seed,
        }
        request = {
            "kind": "image",
            "input": input_payload,
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": self.image_model(wf),
            },
            "storage": {
                "relativeDir": f"tasks/{workflow_id}/running",
                "fileStem": f"clip{clip_index}-last",
            },
            "metadata": {
                "workflowId": workflow_id,
                "stage": STAGE_KEYFRAME,
                "clipIndex": clip_index,
                "variantKind": "keyframe_end",
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        }
        return request, prompt

    def build_video_request(
        self,
        wf: BizStageWorkflow,
        *,
        workflow_id: str,
        clip_index: int,
        clip: dict[str, Any],
        width: int,
        height: int,
        duration_seconds: int,
        first_frame_url: str,
        last_frame_url: str,
    ) -> tuple[dict[str, Any], str]:
        prompt = self.video_prompt(wf, clip)
        request = {
            "kind": "video",
            "input": {
                "prompt": prompt,
                "videoSize": wf.video_size,
                "width": width,
                "height": height,
                "durationSeconds": duration_seconds,
                "minDurationSeconds": duration_seconds,
                "maxDurationSeconds": duration_seconds,
                "firstFrameUrl": first_frame_url,
                "lastFrameUrl": last_frame_url,
                "seed": wf.video_seed,
            },
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": wf.video_model,
            },
            "metadata": {
                "workflowId": workflow_id,
                "stage": STAGE_VIDEO,
                "clipIndex": clip_index,
            },
            "auth": {
                "userId": wf.owner_user_id,
            },
        }
        return request, prompt

    @staticmethod
    def character_sheet_prompt(character: dict[str, Any] | None) -> str:
        if not character:
            return ""
        return (
            f"Create a clean character turnaround sheet for {character.get('name', '角色')}. "
            f"Show front view, side view, and back view in one image, full body, consistent outfit and face. "
            f"Character definition: {character.get('appearance', '')}. "
            "Plain light background, no text labels, no props, no logo, no watermark."
        )

    @classmethod
    def visual_asset_prompt(cls, asset: dict[str, Any] | None) -> str:
        if not asset:
            return ""
        asset_type = _trim(asset.get("assetType"), "character")
        if asset_type == "character":
            return cls.character_sheet_prompt(asset)
        name = asset.get("name", "素材")
        description = asset.get("description") or asset.get("appearance", "")
        instructions = {
            "prop": "Show a clean multi-angle prop design sheet with front, side, back, and a useful detail view; preserve exact shape, proportions, material, color, wear, and markings.",
            "building": "Show a clean architectural reference sheet with main facade, side elevation, entrance, and a spatial anchor view; preserve structure, materials, windows, doors, and fixed landmarks.",
            "scene": "Show a clean environment reference sheet with establishing view, reverse angle, and important spatial anchors; preserve layout, fixed objects, materials, palette, and lighting logic.",
            "vehicle": "Show a clean vehicle turnaround with front, side, rear, and a detail view; preserve silhouette, color, materials, fixed markings, and persistent damage.",
        }.get(asset_type, "Show a clean reusable visual reference sheet from multiple useful angles and preserve all stable identity anchors.")
        return (
            f"Create a production-ready visual asset reference for {name}. {instructions} "
            f"Asset definition: {description}. Plain light background where applicable, no text labels, no people, no logo, no watermark."
        )

    @staticmethod
    def keyframe_prompt(wf: BizStageWorkflow, clip: dict[str, Any]) -> str:
        return (
            f"Keyframe, aspect ratio {wf.aspect_ratio}. "
            f"Shot: {clip.get('shotLabel', '')}. "
            f"Start frame: {clip.get('startFrame', '')}. "
            f"End frame: {clip.get('endFrame', '')}. "
            f"Scene action: {clip.get('scene', '')}. "
            "Generate a polished production keyframe, no text, no watermark."
        )

    @staticmethod
    def video_prompt(wf: BizStageWorkflow, clip: dict[str, Any]) -> str:
        return (
            "Video clip. "
            f"Shot: {clip.get('shotLabel', '')}. "
            f"Scene action: {clip.get('scene', '')}. "
            f"Start frame: {clip.get('startFrame', '')}. "
            f"End frame: {clip.get('endFrame', '')}. "
            "Keep character identity consistent, natural camera motion, no subtitles, no watermark."
        )
