from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Any

class PaginatedResponse(BaseModel):
    items: list
    total: int
    offset: int = 0
    limit: int = 20

class MessageResponse(BaseModel):
    message: str
