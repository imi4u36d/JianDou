from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from backend_core.schemas import (
    GenerationOptionsResponse,
    GenerateTextMediaRequest,
    GenerateTextMediaResponse,
    GenerateTextScriptRequest,
    GenerateTextScriptResponse,
    TextMediaKind,
)


router = APIRouter(prefix="/generations", tags=["generations"])


def _resolve_method(service: object, candidates: Sequence[str]) -> Callable[..., Any]:
    for method_name in candidates:
        method = getattr(service, method_name, None)
        if callable(method):
            return method
    raise RuntimeError(f"generation service method not available: {', '.join(candidates)}")


def _resolve_text_generator(request: Request) -> Any:
    runtime = request.app.state.runtime
    service = runtime.service
    generator = getattr(service, "text_generator", None)
    if generator is not None:
        return generator

    # Compatibility fallback: some runtime service implementations may not expose
    # generation methods, so lazily construct a generator from runtime settings.
    cached = getattr(request.app.state, "_compat_text_generator", None)
    if cached is not None:
        return cached

    from backend_core.text_generation import TextGenerationEngine

    generator = TextGenerationEngine(settings=runtime.settings, storage=runtime.storage)
    setattr(request.app.state, "_compat_text_generator", generator)
    return generator


def _call_service(request: Request, method_candidates: Sequence[str], *args: object) -> Any:
    service = request.app.state.runtime.service
    try:
        method = _resolve_method(service, method_candidates)
        return method(*args)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="generation runtime error") from exc


def _call_generation(
    request: Request,
    *,
    service_candidates: Sequence[str],
    generator_method: str,
    args: tuple[object, ...] = (),
) -> Any:
    service = request.app.state.runtime.service
    service_method = None
    for method_name in service_candidates:
        candidate = getattr(service, method_name, None)
        if callable(candidate):
            service_method = candidate
            break

    try:
        if service_method is not None:
            return service_method(*args)
        generator = _resolve_text_generator(request)
        candidate = getattr(generator, generator_method, None)
        if callable(candidate):
            return candidate(*args)
        raise RuntimeError(f"generation service method not available: {', '.join(service_candidates)}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="generation runtime error") from exc


@router.get("/versions", response_model=GenerationOptionsResponse)
def list_generation_versions(request: Request) -> GenerationOptionsResponse:
    return _call_generation(
        request,
        service_candidates=("list_generation_options", "list_generation_versions", "get_generation_versions"),
        generator_method="get_generation_options",
    )


@router.post("/image", response_model=GenerateTextMediaResponse)
def generate_text_image(request: Request, payload: GenerateTextMediaRequest) -> GenerateTextMediaResponse:
    if payload.kind != TextMediaKind.IMAGE:
        raise HTTPException(status_code=400, detail="kind must be image for this endpoint")
    return _call_generation(
        request,
        service_candidates=("generate_text_image", "generate_image_from_text", "generate_image", "generate_text_media"),
        generator_method="generate_text_image",
        args=(payload,),
    )


@router.post("/video", response_model=GenerateTextMediaResponse)
def generate_text_video(request: Request, payload: GenerateTextMediaRequest) -> GenerateTextMediaResponse:
    if payload.kind != TextMediaKind.VIDEO:
        raise HTTPException(status_code=400, detail="kind must be video for this endpoint")
    return _call_generation(
        request,
        service_candidates=("generate_text_video", "generate_video_from_text", "generate_video", "generate_text_media"),
        generator_method="generate_text_video",
        args=(payload,),
    )


@router.post("/script", response_model=GenerateTextScriptResponse)
def generate_text_script(request: Request, payload: GenerateTextScriptRequest) -> GenerateTextScriptResponse:
    return _call_generation(
        request,
        service_candidates=("generate_text_script", "generate_script_from_text", "generate_script"),
        generator_method="generate_text_script",
        args=(payload,),
    )
