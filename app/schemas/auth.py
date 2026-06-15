from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthSessionResponse(BaseModel):
    authenticated: bool = False
    user: Optional[dict] = None

class ActivateInviteRequest(BaseModel):
    code: str
    username: str
    display_name: str
    password: str
