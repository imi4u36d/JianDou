from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class MaterialRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel),
        populate_by_name=True,
    )


class CreateMaterialGenerationRequest(MaterialRequestModel):
    title: str = "素材生成"
    asset_type: str = Field(default="free", alias="assetType")
    description: Optional[str] = None
    style_keywords: list[str] = Field(default_factory=list, alias="styleKeywords")
    aspect_ratio: Optional[str] = Field(default=None, alias="aspectRatio")
    image_size: Optional[str] = Field(default=None, alias="imageSize")
    text_analysis_model: Optional[str] = Field(default=None, alias="textAnalysisModel")
    image_model: Optional[str] = Field(default=None, alias="imageModel")
    seed: Optional[int] = None

    def metadata(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "styleKeywords": self.style_keywords,
            "aspectRatio": self.aspect_ratio,
            "imageSize": self.image_size,
            "textAnalysisModel": self.text_analysis_model,
            "imageModel": self.image_model,
            "seed": self.seed,
        }


class RateMaterialAssetRequest(MaterialRequestModel):
    effect_rating: int = Field(alias="effectRating", ge=1, le=5)
    effect_rating_note: Optional[str] = Field(default=None, alias="effectRatingNote")
