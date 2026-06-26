from __future__ import annotations

from typing import Any

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field

from backend.schemas.common import _to_camel


class MaterialRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel),
        populate_by_name=True,
    )


class CreateMaterialGenerationRequest(MaterialRequestModel):
    title: str = "素材生成"
    asset_type: str = Field(default="free", alias="assetType")
    description: str | None = None
    style_keywords: list[str] = Field(default_factory=list, alias="styleKeywords")
    aspect_ratio: str | None = Field(default=None, alias="aspectRatio")
    image_size: str | None = Field(default=None, alias="imageSize")
    text_analysis_model: str | None = Field(default=None, alias="textAnalysisModel")
    image_model: str | None = Field(default=None, alias="imageModel")
    seed: int | None = None

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
    effect_rating_note: str | None = Field(default=None, alias="effectRatingNote")


class MaterialAssetDeleteResult(BaseModel):
    deleted: bool = False
    asset_id: str = ""


class MaterialFavoriteFolder(MaterialRequestModel):
    id: str = ""
    name: str = ""
    asset_ids: list[str] = Field(default_factory=list, alias="assetIds")
    created_at: str = Field(default="", alias="createdAt")


class MaterialFavoriteFolderList(MaterialRequestModel):
    folders: list[MaterialFavoriteFolder] = Field(default_factory=list)


class CreateMaterialFavoriteFolderRequest(MaterialRequestModel):
    name: str
    asset_ids: list[str] = Field(default_factory=list, alias="assetIds")


class RenameMaterialFavoriteFolderRequest(MaterialRequestModel):
    name: str


class MaterialFavoriteAssetIdsRequest(MaterialRequestModel):
    asset_ids: list[str] = Field(default_factory=list, alias="assetIds")


class MaterialFavoriteFolderDeleteResult(MaterialRequestModel):
    deleted: bool = False
    folder_id: str = Field(default="", alias="folderId")


class MaterialAssetResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel),
    )

    id: str = ""
    title: str = ""
    asset_type: str = ""
    media_type: str = ""
    public_url: str = ""
    file_url: str = ""
    remote_url: str | None = None
    thumbnail_url: str | None = None
    preview_url: str | None = None
    effect_rating: int | None = None
    effect_rating_note: str = ""
    rated_at: str | None = None
    width: int | None = None
    height: int | None = None
    clip_index: int | None = None
    origin_model: str | None = None
    origin_provider: str | None = None
    workflow_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""
