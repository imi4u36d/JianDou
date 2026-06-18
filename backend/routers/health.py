from __future__ import annotations
from fastapi import APIRouter, Request
from backend.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/v3/health")
async def health(request: Request):
    model_resolver = getattr(request.app.state, "model_resolver", None)
    model_info = {
        "provider": None,
        "primary_model": None,
        "text_analysis_provider": None,
        "text_analysis_model": None,
        "endpoint_host": None,
        "api_key_present": False,
        "ready": False,
        "temperature": None,
        "max_tokens": None,
        "config_errors": [],
    }

    if model_resolver is not None:
        try:
            primary_model_key = model_resolver.value("model", "primary_model", "") or "claude-sonnet"
            text_profile = model_resolver.resolve_text_profile(primary_model_key)
            model_info = {
                "provider": text_profile.provider or None,
                "primary_model": text_profile.config.model or None,
                "text_analysis_provider": None,
                "text_analysis_model": None,
                "endpoint_host": text_profile.endpoint_host or None,
                "api_key_present": bool(text_profile.api_key),
                "ready": text_profile.ready,
                "temperature": text_profile.config.temperature,
                "max_tokens": text_profile.config.max_tokens,
                "config_errors": list(model_resolver.config_errors()),
            }
        except Exception:
            pass

    return {
        "ok": True,
        "runtime": {
            "name": "jiandou-api",
            "env": settings.app_env,
            "execution_mode": settings.execution_mode,
            "database_url": settings.database_url,
            "storage_root": settings.storage_root,
            "model": model_info,
            "planning_capabilities": {
                "timed_transcript_supported": False,
                "transcript_semantic_planning": False,
                "visual_content_analysis": False,
                "visual_event_reasoning": False,
                "subtitle_visual_fusion": False,
                "audio_peak_signal": False,
                "scene_boundary_signal": False,
                "fusion_timeline_planning": False,
                "fallback_heuristic_enabled": False,
            },
        },
    }
