"""Pure payload builders for generation runs."""

from __future__ import annotations

from typing import Any

from backend.domain.generation_run import GenerationModelKinds


def append_negative_prompt(prompt: str, negative_prompt: str) -> str:
    if not prompt or not prompt.strip():
        return f"写实影视风格。负面约束：{negative_prompt}"
    return f"{prompt.strip()}\n负面约束：{negative_prompt}"


def infer_camera_fixed(prompt: str, fallback: bool) -> bool:
    normalized = _string_value(prompt).lower()
    if not normalized:
        return fallback
    keywords = [
        "固定镜头",
        "固定机位",
        "镜头固定",
        "机位固定",
        "镜头保持固定",
        "监控视角",
        "监控镜头",
        "鱼眼监控",
    ]
    return True if any(keyword in normalized for keyword in keywords) else fallback


def build_model_info(
    profile: dict[str, Any],
    requested_model: str,
    media_kind: str,
    response: dict[str, Any] | None,
    source_tag: str,
) -> dict[str, Any]:
    return {
        "provider": profile.get("provider", ""),
        "modelName": profile.get("modelName", ""),
        "providerModel": profile.get("modelName", ""),
        "requestedModel": requested_model,
        "resolvedModel": profile.get("modelName", ""),
        "textAnalysisModel": profile.get("modelName", ""),
        "mediaKind": media_kind,
        "endpointHost": (response or {}).get("endpointHost", profile.get("endpointHost", "")),
        "configSource": profile.get("source", ""),
        "generationSource": source_tag,
    }


def build_media_model_info(
    text_profile: dict[str, Any],
    rewrite_profile: dict[str, Any] | None,
    vision_profile: dict[str, Any] | None,
    media_profile: dict[str, Any],
    requested_model: str,
    media_kind: str,
    text_response: dict[str, Any] | None,
    vision_response: dict[str, Any] | None,
    resolved_model: str,
    endpoint_host: str,
    task_endpoint_host: str,
    source_tag: str,
) -> dict[str, Any]:
    info: dict[str, Any] = {
        "provider": media_profile.get("provider", ""),
        "modelName": resolved_model,
        "providerModel": resolved_model,
        "requestedModel": requested_model,
        "resolvedModel": resolved_model,
        "textAnalysisModel": text_profile.get("modelName", ""),
        "textAnalysisProvider": text_profile.get("provider", ""),
        "textAnalysisEndpointHost": text_profile.get("endpointHost", ""),
        "mediaKind": media_kind,
        "endpointHost": endpoint_host,
        "taskEndpointHost": task_endpoint_host,
        "configSource": media_profile.get("source", ""),
        "generationSource": source_tag,
    }
    if rewrite_profile:
        info["promptRewriteModel"] = rewrite_profile.get("modelName", "")
        info["promptRewriteProvider"] = rewrite_profile.get("provider", "")
        info["promptRewriteEndpointHost"] = (
            (text_response or {}).get("endpointHost", rewrite_profile.get("endpointHost", ""))
        )
    if vision_profile:
        info["visionAnalysisModel"] = vision_profile.get("modelName", "")
        info["visionAnalysisProvider"] = vision_profile.get("provider", "")
        info["visionAnalysisEndpointHost"] = (
            (vision_response or {}).get("endpointHost", vision_profile.get("endpointHost", ""))
        )
    return info


def build_negative_prompt(media_kind: str) -> str:
    if media_kind == GenerationModelKinds.VIDEO:
        video_only = ""
    else:
        video_only = ""
    return f" {video_only}"


def build_script_user_prompt(source_text: str, visual_style: str) -> str:
    style_line = (
        ""
        if not visual_style or visual_style.strip().lower() == "ai  "
        else f"  {visual_style}"
    )
    return f"  \n{style_line}\n\n【 】：\n{source_text}\n\n---\n\n  system prompt     。"


def build_script_adjust_user_prompt(
    source_text: str, visual_style: str, source_script: str, adjustment_prompt: str
) -> str:
    style_line = ""
    if visual_style and visual_style.strip().lower() != "ai  ":
        style_line = f"  {visual_style}"
    requirement = (
        f"  \n{adjustment_prompt.strip()}"
        if adjustment_prompt and adjustment_prompt.strip()
        else ""
    )
    source_section = source_text if source_text else ""
    return f"  {source_section}\n{style_line}\n{requirement}\n\n{source_script}"


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()
