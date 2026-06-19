from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str

class AuthSessionResponse(BaseModel):
    authenticated: bool = False
    user: Optional[dict] = None

class ActivateInviteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    username: str
    display_name: str = Field(alias="displayName")
    password: str
