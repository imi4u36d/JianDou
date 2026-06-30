from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class GenerationCatalogService:
    """Builds the public generation catalog from checked-in YAML config."""

    def __init__(self, config_dir: str | Path = "./config") -> None:
        self._config_dir = Path(config_dir)
        self._cached_catalog: dict[str, Any] | None = None

    def catalog(self) -> dict[str, Any]:
        if self._cached_catalog is None:
            self._cached_catalog = self._build_catalog()
        return self._cached_catalog

    def refresh(self) -> dict[str, Any]:
        self._cached_catalog = self._build_catalog()
        return self._cached_catalog

    def _build_catalog(self) -> dict[str, Any]:
        catalog_options = self._load_yaml(self._config_dir / "catalog" / "options.yml")
        catalog = self._section(catalog_options, "catalog")

        catalog_defaults = self._load_yaml(self._config_dir / "catalog" / "defaults.yml")
        defaults = self._section(self._section(catalog_defaults, "catalog"), "defaults")

        models_data = self._load_yaml(self._config_dir / "model" / "models.yml")
        models_section = self._section(self._section(models_data, "model"), "models")

        text_models, image_models, video_models = self._model_options(models_section)
        image_sizes = self._size_options(self._section(catalog, "image_sizes"))
        video_sizes = self._size_options(self._section(catalog, "video_sizes"))
        video_durations = self._duration_options(self._section(catalog, "video_durations"))

        return {
            "aspectRatios": self._aspect_ratio_options(self._section(catalog, "aspect_ratios")),
            "defaultAspectRatio": defaults.get("aspect_ratio", "16:9"),
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
            "defaultVideoDurationSeconds": defaults.get(
                "video_duration_seconds",
                video_durations[0]["value"] if video_durations else None,
            ),
        }

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
        value = data.get(key)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _csv(raw: Any) -> list[str]:
        return [item.strip() for item in str(raw).split(",") if item.strip()]

    def _model_options(
        self,
        models_section: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        text_models: list[dict[str, Any]] = []
        image_models: list[dict[str, Any]] = []
        video_models: list[dict[str, Any]] = []

        for model_key, model_value in models_section.items():
            if not isinstance(model_value, dict):
                continue
            kind = str(model_value.get("kind", "")).lower()
            item: dict[str, Any] = {
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
                    item["supportedSizes"] = self._csv(model_value["supported_sizes"])
                image_models.append(item)
            elif kind == "video":
                if model_value.get("supported_sizes"):
                    item["supportedSizes"] = self._csv(model_value["supported_sizes"])
                if model_value.get("supported_durations"):
                    item["supportedDurations"] = self._integer_csv(model_value["supported_durations"])
                item["supportsSeed"] = bool(model_value.get("supports_seed", False))
                item["generationMode"] = model_value.get("generation_mode", "i2v")
                video_models.append(item)

        return text_models, image_models, video_models

    @staticmethod
    def _integer_csv(raw: Any) -> list[int]:
        values: list[int] = []
        for item in str(raw).split(","):
            try:
                values.append(int(item.strip()))
            except ValueError:
                continue
        return values

    @staticmethod
    def _aspect_ratio_options(aspect_ratios: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"value": key, "label": value.get("label", key)}
            for key, value in aspect_ratios.items()
            if isinstance(value, dict)
        ]

    @staticmethod
    def _size_options(raw_sizes: dict[str, Any]) -> list[dict[str, Any]]:
        sizes: list[dict[str, Any]] = []
        for key, value in raw_sizes.items():
            label = value.get("label", key) if isinstance(value, dict) else key
            item: dict[str, Any] = {"value": key, "label": label}
            if isinstance(value, dict):
                if "width" in value:
                    item["width"] = value["width"]
                if "height" in value:
                    item["height"] = value["height"]
            sizes.append(item)
        return sizes

    @staticmethod
    def _duration_options(raw_durations: dict[str, Any]) -> list[dict[str, Any]]:
        durations: list[dict[str, Any]] = []
        for key, value in raw_durations.items():
            try:
                seconds = int(key)
            except ValueError:
                continue
            label = value.get("label", f"{seconds} 秒") if isinstance(value, dict) else f"{seconds} 秒"
            durations.append({"value": seconds, "label": label})
        durations.sort(key=lambda item: item["value"])
        return durations
