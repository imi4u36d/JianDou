from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str

class AuthSessionResponse(BaseModel):
    authenticated: bool = False
    user: dict | None = None

class ActivateInviteRequest(BaseModel):
    code: str
    username: str
    password: str
