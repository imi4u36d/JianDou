from __future__ import annotations

from typing import Any

from backend.domain.enums import WorkflowStage
from backend.models.workflow import BizStageWorkflow

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"


def _trim(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = str(value).strip()
    return stripped if stripped else fallback.strip()


class WorkflowGenerationRequestBuilder:
    """Build generation-service request payloads for workflow stages."""

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
            "options": {
                "visualStyle": _trim(wf.style_preset, "cinematic"),
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
    ) -> tuple[dict[str, Any], str]:
        is_character_sheet = character is not None
        prompt = (
            self.character_sheet_prompt(character)
            if is_character_sheet
            else self.keyframe_prompt(wf, clip or {})
        )
        request = {
            "kind": "image",
            "input": {
                "prompt": prompt,
                "width": width,
                "height": height,
                "frameRole": "sheet" if is_character_sheet else "first",
                "seed": wf.keyframe_seed,
            },
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": wf.image_model,
            },
            "options": {
                "stylePreset": wf.style_preset,
            },
            "storage": {
                "relativeDir": f"gen/_runs/workflows/{workflow_id}",
                "fileStem": f"clip{clip_index}-first",
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
        request = {
            "kind": "image",
            "input": {
                "prompt": prompt,
                "width": width,
                "height": height,
                "frameRole": "last",
                "referenceImageUrl": start_frame_remote_url,
                "seed": wf.keyframe_seed,
            },
            "model": {
                "textAnalysisModel": wf.text_analysis_model,
                "providerModel": wf.image_model,
            },
            "options": {
                "stylePreset": wf.style_preset,
            },
            "storage": {
                "relativeDir": f"gen/_runs/workflows/{workflow_id}",
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

    @staticmethod
    def keyframe_prompt(wf: BizStageWorkflow, clip: dict[str, Any]) -> str:
        return (
            f"{wf.style_preset} cinematic keyframe, aspect ratio {wf.aspect_ratio}. "
            f"Shot: {clip.get('shotLabel', '')}. "
            f"Start frame: {clip.get('startFrame', '')}. "
            f"End frame: {clip.get('endFrame', '')}. "
            f"Scene action: {clip.get('scene', '')}. "
            "Generate a polished production keyframe, no text, no watermark."
        )

    @staticmethod
    def video_prompt(wf: BizStageWorkflow, clip: dict[str, Any]) -> str:
        return (
            f"{wf.style_preset} short drama video clip. "
            f"Shot: {clip.get('shotLabel', '')}. "
            f"Scene action: {clip.get('scene', '')}. "
            f"Start frame: {clip.get('startFrame', '')}. "
            f"End frame: {clip.get('endFrame', '')}. "
            "Keep character identity consistent, natural camera motion, no subtitles, no watermark."
        )
