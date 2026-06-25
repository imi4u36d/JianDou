"""Workflow stage generation strategy — resolves provider and model info for each workflow stage.

Mirrors the Java WorkflowStageGenerationStrategy and WorkflowStageGenerationStrategyResolver classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _blank_to(value: str | None, fallback: str) -> str:
    """Return the first argument if non-blank, else the fallback."""
    v = _trim(value)
    return v if v else fallback


def _trim(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _string_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


@dataclass
class WorkflowStageGenerationStrategy:
    """Strategy info for a single workflow generation stage.

    Mirrors the Java WorkflowStageGenerationStrategy record.
    """

    stage: str = ""
    strategy_key: str = ""
    run_kind: str = ""
    model_kind: str = ""
    requested_model: str = ""
    provider: str = ""
    provider_model: str = ""
    supports_seed: bool = False
    supports_image_data_uri_references: bool = False
    reference_input_mode: str = ""
    generation_mode: str = ""
    config_source: str = ""

    def __post_init__(self) -> None:
        self.stage = _blank_to(self.stage, "")
        self.strategy_key = _blank_to(self.strategy_key, "")
        self.run_kind = _blank_to(self.run_kind, "")
        self.model_kind = _blank_to(self.model_kind, "")
        self.requested_model = _blank_to(self.requested_model, "")
        self.provider = _blank_to(self.provider, "")
        self.provider_model = _blank_to(self.provider_model, "")
        self.supports_seed = bool(self.supports_seed)
        self.supports_image_data_uri_references = bool(self.supports_image_data_uri_references)
        self.reference_input_mode = _blank_to(self.reference_input_mode, "")
        self.generation_mode = _blank_to(self.generation_mode, "")
        self.config_source = _blank_to(self.config_source, "")

    def model_section(self, text_analysis_model: str) -> dict[str, Any]:
        """Build the model configuration section dict for this strategy."""
        model: dict[str, Any] = {}
        if self.run_kind in ("script", "script_adjust"):
            model["textAnalysisModel"] = self.requested_model
            return model
        model["textAnalysisModel"] = _blank_to(text_analysis_model, "")
        model["providerModel"] = self.requested_model
        return model

    def metadata(self) -> dict[str, Any]:
        """Return metadata dict describing this strategy."""
        return {
            "stage": self.stage,
            "key": self.strategy_key,
            "strategyKey": self.strategy_key,
            "runKind": self.run_kind,
            "modelKind": self.model_kind,
            "requestedModel": self.requested_model,
            "provider": self.provider,
            "providerModel": self.provider_model,
            "supportsSeed": self.supports_seed,
            "supportsImageDataUriReferences": self.supports_image_data_uri_references,
            "referenceInputMode": self.reference_input_mode,
            "generationMode": self.generation_mode,
            "configSource": self.config_source,
        }


class WorkflowStageGenerationStrategyResolver:
    """Resolves generation strategies for each workflow stage from model config.

    Mirrors the Java WorkflowStageGenerationStrategyResolver class.
    """

    # Stage constants (mirrors WorkflowConstants)
    STAGE_STORYBOARD = "storyboard"
    STAGE_KEYFRAME = "keyframe"
    STAGE_VIDEO = "video"

    # Run kind constants (mirrors GenerationRunKinds)
    RUN_KIND_SCRIPT = "script"
    RUN_KIND_SCRIPT_ADJUST = "script_adjust"
    RUN_KIND_IMAGE = "image"
    RUN_KIND_VIDEO = "video"

    # Model kind constants (mirrors GenerationModelKinds)
    MODEL_KIND_TEXT = "text"
    MODEL_KIND_IMAGE = "image"
    MODEL_KIND_VIDEO = "video"

    def __init__(self, model_resolver: Any) -> None:
        self._model_resolver = model_resolver

    def storyboard(self, workflow: Any) -> WorkflowStageGenerationStrategy:
        """Resolve strategy for the storyboard (script) stage."""
        requested_model = _trim(workflow.get("textAnalysisModel", "") if isinstance(workflow, dict)
                                else (getattr(workflow, "text_analysis_model", "") or
                                      getattr(workflow, "getTextAnalysisModel", lambda: "")()))
        profile = self._resolve_text_profile(requested_model, workflow)
        return WorkflowStageGenerationStrategy(
            stage=self.STAGE_STORYBOARD,
            strategy_key="storyboard.text",
            run_kind=self.RUN_KIND_SCRIPT,
            model_kind=self.MODEL_KIND_TEXT,
            requested_model=requested_model,
            provider=_string_value(getattr(profile, "provider", "") if profile else ""),
            provider_model=_string_value(getattr(profile, "model_name", requested_model) if profile else requested_model),
            supports_seed=getattr(profile, "supports_seed", False) if profile else self._supports_seed_fallback(requested_model),
            supports_image_data_uri_references=False,
            reference_input_mode="none",
            generation_mode="",
            config_source=_string_value(getattr(profile, "source", "") if profile else ""),
        )

    def storyboard_adjust(self, workflow: Any) -> WorkflowStageGenerationStrategy:
        """Resolve strategy for storyboard adjustment (re-prompt)."""
        base = self.storyboard(workflow)
        meta = base.metadata()
        return WorkflowStageGenerationStrategy(
            stage=self.STAGE_STORYBOARD,
            strategy_key="storyboard.adjust.text",
            run_kind=self.RUN_KIND_SCRIPT_ADJUST,
            model_kind=self.MODEL_KIND_TEXT,
            requested_model=base.requested_model,
            provider=_string_value(meta.get("provider")),
            provider_model=_string_value(meta.get("providerModel")),
            supports_seed=base.supports_seed,
            supports_image_data_uri_references=False,
            reference_input_mode="none",
            generation_mode="",
            config_source=_string_value(meta.get("configSource")),
        )

    def character_sheet(self, workflow: Any) -> WorkflowStageGenerationStrategy:
        """Resolve strategy for character sheet image generation."""
        return self._image(workflow, "character_sheet")

    def keyframe(self, workflow: Any) -> WorkflowStageGenerationStrategy:
        """Resolve strategy for keyframe image generation."""
        return self._image(workflow, "keyframe")

    def material_image(self, user_id: int, image_model: str, asset_type: str) -> WorkflowStageGenerationStrategy:
        """Resolve strategy for material image generation."""
        return self._image_for(user_id, image_model, f"material_{_trim(asset_type)}")

    def video(self, workflow: Any) -> WorkflowStageGenerationStrategy:
        """Resolve strategy for the video generation stage."""
        requested_model = _trim(workflow.get("videoModel", "") if isinstance(workflow, dict)
                                else (getattr(workflow, "video_model", "") or
                                      getattr(workflow, "getVideoModel", lambda: "")()))
        profile = self._resolve_media_profile(requested_model, self.MODEL_KIND_VIDEO, workflow)
        provider_key = self._provider_key(profile, requested_model)
        return WorkflowStageGenerationStrategy(
            stage=self.STAGE_VIDEO,
            strategy_key=f"video.{provider_key}",
            run_kind=self.RUN_KIND_VIDEO,
            model_kind=self.MODEL_KIND_VIDEO,
            requested_model=requested_model,
            provider=_string_value(getattr(profile, "provider", "") if profile else ""),
            provider_model=_string_value(getattr(profile, "model_name", requested_model) if profile else requested_model),
            supports_seed=getattr(profile, "supports_seed", False) if profile else self._supports_seed_fallback(requested_model),
            supports_image_data_uri_references=False,
            reference_input_mode="frame_url",
            generation_mode=_string_value(getattr(profile, "generation_mode", "") if profile else ""),
            config_source=_string_value(getattr(profile, "source", "") if profile else ""),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _image(self, workflow: Any, strategy_suffix: str) -> WorkflowStageGenerationStrategy:
        user_id = workflow.get("ownerUserId") if isinstance(workflow, dict) else getattr(workflow, "owner_user_id", None) or getattr(workflow, "getOwnerUserId", lambda: None)()
        image_model = _trim(workflow.get("imageModel", "") if isinstance(workflow, dict)
                            else (getattr(workflow, "image_model", "") or
                                  getattr(workflow, "getImageModel", lambda: "")()))
        return self._image_for(user_id, image_model, strategy_suffix)

    def _image_for(self, user_id: int | None, image_model: str, strategy_suffix: str) -> WorkflowStageGenerationStrategy:
        requested_model = _trim(image_model)
        profile = self._resolve_media_profile(requested_model, self.MODEL_KIND_IMAGE, user_id)
        supports_data_uri_refs = (
            getattr(profile, "supports_image_data_uri_references", False) if profile
            else "gpt-image" in requested_model.lower()
        )
        provider_key = self._provider_key(profile, requested_model)
        return WorkflowStageGenerationStrategy(
            stage=self.STAGE_KEYFRAME,
            strategy_key=f"{_trim(strategy_suffix)}.{provider_key}",
            run_kind=self.RUN_KIND_IMAGE,
            model_kind=self.MODEL_KIND_IMAGE,
            requested_model=requested_model,
            provider=_string_value(getattr(profile, "provider", "") if profile else ""),
            provider_model=_string_value(getattr(profile, "model_name", requested_model) if profile else requested_model),
            supports_seed=getattr(profile, "supports_seed", False) if profile else self._supports_seed_fallback(requested_model),
            supports_image_data_uri_references=supports_data_uri_refs,
            reference_input_mode="http_or_data_uri" if supports_data_uri_refs else "http_only",
            generation_mode=_string_value(getattr(profile, "generation_mode", "") if profile else ""),
            config_source=_string_value(getattr(profile, "source", "") if profile else ""),
        )

    def _resolve_text_profile(self, requested_model: str, workflow: Any) -> Any:
        """Resolve text model profile."""
        if self._model_resolver is None:
            return None
        user_id = workflow.get("ownerUserId") if isinstance(workflow, dict) else getattr(workflow, "owner_user_id", None) or getattr(workflow, "getOwnerUserId", lambda: None)()
        if hasattr(self._model_resolver, "resolve_text_profile"):
            return self._model_resolver.resolve_text_profile(requested_model, user_id)
        return None

    def _resolve_media_profile(self, requested_model: str, model_kind: str, workflow_or_user: Any) -> Any:
        """Resolve media provider profile."""
        if self._model_resolver is None:
            return None
        if isinstance(workflow_or_user, int) or workflow_or_user is None:
            user_id = workflow_or_user
        elif isinstance(workflow_or_user, dict):
            user_id = workflow_or_user.get("ownerUserId") or workflow_or_user.get("owner_user_id")
        else:
            user_id = getattr(workflow_or_user, "owner_user_id", None) or getattr(workflow_or_user, "getOwnerUserId", lambda: None)()
        resolver = getattr(self._model_resolver, "resolve_media_profile", None)
        if resolver:
            return resolver(requested_model, model_kind, user_id)
        # fallback: try image/video-specific resolvers
        if model_kind == self.MODEL_KIND_IMAGE and hasattr(self._model_resolver, "resolve_image_profile"):
            return self._model_resolver.resolve_image_profile(requested_model, user_id)
        if model_kind == self.MODEL_KIND_VIDEO and hasattr(self._model_resolver, "resolve_video_profile"):
            return self._model_resolver.resolve_video_profile(requested_model, user_id)
        return None

    def _supports_seed_fallback(self, requested_model: str) -> bool:
        if self._model_resolver is None:
            return False
        if hasattr(self._model_resolver, "supports_seed"):
            return bool(self._model_resolver.supports_seed(requested_model))
        return False

    @staticmethod
    def _provider_key(profile: Any, requested_model: str) -> str:
        """Derive a provider key string from the profile or model name."""
        if profile is not None:
            provider = _string_value(getattr(profile, "provider", ""))
            if provider:
                return provider
        model = _trim(requested_model).lower()
        if "gpt-image" in model:
            return "gpt-image"
        return model if model else "default"
