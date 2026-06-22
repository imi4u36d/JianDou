from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend.config import settings

router = APIRouter(tags=["health"])


def _database_summary() -> dict[str, Any]:
    try:
        url = make_url(settings.database_url)
    except Exception:
        return {"configured": bool(settings.database_url), "dialect": None}

    return {
        "configured": bool(settings.database_url),
        "dialect": url.drivername,
        "database": Path(url.database).name if url.database else None,
    }


def _storage_summary() -> dict[str, Any]:
    root = Path(settings.storage_root)
    return {
        "configured": bool(settings.storage_root),
        "root": str(root),
        "uploads_dir": settings.uploads_dir,
        "generation_runs_dir": settings.generation_runs_dir,
    }


def _model_info(request: Request) -> dict[str, Any]:
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
        except Exception:  # noqa: S110 — best-effort health probe
            pass

    return model_info


async def _check_database() -> dict[str, Any]:
    import backend.database as database

    try:
        async with database.async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        return {
            "ready": False,
            "detail": exc.__class__.__name__,
            **_database_summary(),
        }

    return {"ready": True, **_database_summary()}


def _check_storage() -> dict[str, Any]:
    root = Path(settings.storage_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise RuntimeError("storage_root_is_not_directory")
        probe = root / ".jiandou-ready-check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        return {
            "ready": False,
            "detail": exc.__class__.__name__,
            **_storage_summary(),
        }

    return {"ready": True, **_storage_summary()}


def _runtime_payload(request: Request) -> dict[str, Any]:
    model_info = _model_info(request)
    return {
        "name": "jiandou-api",
        "env": settings.app_env,
        "execution_mode": settings.execution_mode,
        "database": _database_summary(),
        "storage": _storage_summary(),
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
    }


@router.get("/api/v3/health")
async def health(request: Request):
    return {
        "ok": True,
        "healthy": True,
        "env": settings.app_env,
        "runtime": _runtime_payload(request),
    }


@router.get("/api/v3/ready")
async def ready(request: Request):
    checks = {
        "database": await _check_database(),
        "storage": _check_storage(),
    }
    is_ready = all(check["ready"] for check in checks.values())
    payload = {
        "ok": is_ready,
        "ready": is_ready,
        "env": settings.app_env,
        "checks": checks,
        "runtime": _runtime_payload(request),
    }
    return JSONResponse(status_code=200 if is_ready else 503, content=payload)
