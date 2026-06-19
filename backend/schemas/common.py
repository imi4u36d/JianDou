from __future__ import annotations

from pydantic import AliasGenerator, BaseModel


def _to_camel(name: str) -> str:
    """Convert snake_case to camelCase for JSON field aliases."""
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


# Reusable alias generator for Pydantic models that need camelCase JSON keys.
camel_alias = AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    offset: int = 0
    limit: int = 20


class MessageResponse(BaseModel):
    message: str
