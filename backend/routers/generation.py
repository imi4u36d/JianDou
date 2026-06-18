from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
import yaml

from backend.services.generation_service import GenerationRunNotFoundException, UnsupportedGenerationKindException

router = APIRouter(prefix="/api/v3/generation", tags=["generation"])

_cached_catalog: dict | None = None


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _build_catalog() -> dict:
    global _cached_catalog
    if _cached_catalog is not None:
        return _cached_catalog

    config_dir = Path("./config")

    # Load catalog options
    catalog_options = _load_yaml(config_dir / "catalog" / "options.yml")
    catalog = catalog_options.get("catalog", {}) if isinstance(catalog_options.get("catalog"), dict) else {}

    # Load catalog defaults
    catalog_defaults = _load_yaml(config_dir / "catalog" / "defaults.yml")
    defaults = catalog_defaults.get("catalog", {}).get("defaults", {}) if isinstance(catalog_defaults.get("catalog"), dict) else {}

    # Load models
    models_data = _load_yaml(config_dir / "model" / "models.yml")
    models_section = models_data.get("model", {}).get("models", {}) if isinstance(models_data.get("model"), dict) else {}

    # Categorize models
    text_models = []
    image_models = []
    video_models = []

    for model_key, model_value in models_section.items():
        if not isinstance(model_value, dict):
            continue
        kind = str(model_value.get("kind", "")).lower()
        item = {
            "value": model_key,
            "label": model_value.get("label", model_key),
            "description": model_value.get("description", ""),
            "provider": model_value.get("provider", ""),
            "vendor": model_value.get("vendor", ""),
            "family": model_value.get("family", ""),
        }
        if kind == "text":
            text_models.append(item)
        elif kind == "image":
            if model_value.get("supported_sizes"):
                item["supportedSizes"] = [s.strip() for s in str(model_value["supported_sizes"]).split(",") if s.strip()]
            image_models.append(item)
        elif kind == "video":
            if model_value.get("supported_sizes"):
                item["supportedSizes"] = [s.strip() for s in str(model_value["supported_sizes"]).split(",") if s.strip()]
            if model_value.get("supported_durations"):
                try:
                    item["supportedDurations"] = [int(d.strip()) for d in str(model_value["supported_durations"]).split(",") if d.strip()]
                except ValueError:
                    pass
            item["supportsSeed"] = bool(model_value.get("supports_seed", False))
            item["generationMode"] = model_value.get("generation_mode", "i2v")
            video_models.append(item)

    # Build aspect ratios
    aspect_ratios_raw = catalog.get("aspect_ratios", {})
    aspect_ratios = [{"value": k, "label": v.get("label", k)} for k, v in aspect_ratios_raw.items()] if isinstance(aspect_ratios_raw, dict) else []

    # Build image sizes
    image_sizes_raw = catalog.get("image_sizes", {})
    image_sizes = []
    if isinstance(image_sizes_raw, dict):
        for k, v in image_sizes_raw.items():
            item = {"value": k, "label": v.get("label", k)}
            if isinstance(v, dict):
                if "width" in v:
                    item["width"] = v["width"]
                if "height" in v:
                    item["height"] = v["height"]
            image_sizes.append(item)

    # Build video sizes
    video_sizes_raw = catalog.get("video_sizes", {})
    video_sizes = []
    if isinstance(video_sizes_raw, dict):
        for k, v in video_sizes_raw.items():
            item = {"value": k, "label": v.get("label", k)}
            if isinstance(v, dict):
                if "width" in v:
                    item["width"] = v["width"]
                if "height" in v:
                    item["height"] = v["height"]
            video_sizes.append(item)

    # Build video durations
    video_durations_raw = catalog.get("video_durations", {})
    video_durations = []
    if isinstance(video_durations_raw, dict):
        for k, v in video_durations_raw.items():
            try:
                val = int(k)
            except ValueError:
                continue
            label = v.get("label", f"{val} 秒") if isinstance(v, dict) else f"{val} 秒"
            video_durations.append({"value": val, "label": label})
    video_durations.sort(key=lambda x: x["value"])

    # Style presets
    style_presets_raw = catalog.get("style_presets", {})
    style_presets = []
    if isinstance(style_presets_raw, dict):
        for k, v in style_presets_raw.items():
            item = {"key": k}
            if isinstance(v, dict):
                item["label"] = v.get("label", k)
                item["description"] = v.get("description", "")
            style_presets.append(item)

    _cached_catalog = {
        "aspectRatios": aspect_ratios,
        "defaultAspectRatio": defaults.get("aspect_ratio", "16:9"),
        "stylePresets": style_presets,
        "defaultStylePreset": defaults.get("style_preset"),
        "imageSizes": image_sizes,
        "defaultImageSize": defaults.get("image_size", image_sizes[0]["value"] if image_sizes else None),
        "textAnalysisModels": text_models,
        "defaultTextAnalysisModel": text_models[0]["value"] if text_models else None,
        "imageModels": image_models,
        "defaultImageModel": image_models[0]["value"] if image_models else None,
        "videoModels": video_models,
        "defaultVideoModel": video_models[0]["value"] if video_models else None,
        "videoSizes": video_sizes,
        "defaultVideoSize": defaults.get("video_size", video_sizes[0]["value"] if video_sizes else None),
        "videoDurations": video_durations,
        "defaultVideoDurationSeconds": defaults.get("video_duration_seconds", video_durations[0]["value"] if video_durations else None),
    }
    return _cached_catalog


@router.get("/options")
async def generation_options():
    return _build_catalog()


@router.get("/catalog")
async def generation_catalog():
    return _build_catalog()


@router.post("/runs")
async def create_generation_run(request: Request):
    body = await request.json()
    service = request.app.state.generation_application_service
    try:
        return await service.create_run(body if isinstance(body, dict) else {})
    except UnsupportedGenerationKindException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs")
async def list_generation_runs(request: Request, limit: int = Query(100, ge=1, le=200)):
    service = request.app.state.generation_application_service
    return await service.list_runs(limit)


@router.get("/runs/{run_id}")
async def get_generation_run(run_id: str, request: Request):
    service = request.app.state.generation_application_service
    try:
        return await service.get_run(run_id)
    except GenerationRunNotFoundException:
        raise HTTPException(status_code=404, detail="generation_run_not_found")


@router.get("/usage")
async def generation_usage(request: Request):
    service = request.app.state.generation_application_service
    return await service.usage()
