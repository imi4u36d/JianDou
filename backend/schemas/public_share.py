from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import camel_alias


class PublicShareModel(BaseModel):
    model_config = ConfigDict(alias_generator=camel_alias, populate_by_name=True)


class CreatePublicShareRequest(PublicShareModel):
    material_asset_id: str = Field(default="", min_length=1)
    source_type: str = Field(default="material")
    source_id: str = Field(default="")


class PublicShareItem(PublicShareModel):
    id: str = ""
    share_id: str = ""
    material_asset_id: str = ""
    source_type: str = ""
    source_id: str = ""
    owner_user_id: int = 0
    author_name: str = ""
    title: str = ""
    media_type: str = ""
    public_url: str = ""
    file_url: str = ""
    preview_url: str = ""
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    like_count: int = 0
    liked_by_me: bool = False
    shared_at: str = ""
    updated_at: str = ""
    status: str = "ACTIVE"


class PublicShareListResponse(PublicShareModel):
    items: list[PublicShareItem] = []
    total: int = 0
    offset: int = 0
    limit: int = 30
    has_more: bool = False
    next_offset: int | None = None


class PublicShareDeleteResult(PublicShareModel):
    deleted: bool = False
    share_id: str = ""
