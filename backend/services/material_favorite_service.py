from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class MaterialFavoriteService:
    """Store material favorite folders in Redis, scoped by owner user id."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def list_folders(self, owner_user_id: int) -> list[dict[str, Any]]:
        return await self._load(owner_user_id)

    async def create_folder(
        self,
        owner_user_id: int,
        *,
        name: str,
        asset_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        folders = await self._load(owner_user_id)
        cleaned_name = name.strip()
        if any(folder["name"] == cleaned_name for folder in folders):
            raise ValueError("favorite_folder_name_exists")
        folder = {
            "id": self._folder_id(),
            "name": cleaned_name,
            "assetIds": self._unique_asset_ids(asset_ids or []),
            "createdAt": self._now(),
        }
        folders.append(folder)
        await self._save(owner_user_id, folders)
        return folder

    async def rename_folder(self, owner_user_id: int, folder_id: str, *, name: str) -> dict[str, Any] | None:
        folders = await self._load(owner_user_id)
        cleaned_name = name.strip()
        if any(folder["id"] != folder_id and folder["name"] == cleaned_name for folder in folders):
            raise ValueError("favorite_folder_name_exists")
        renamed: dict[str, Any] | None = None
        next_folders: list[dict[str, Any]] = []
        for folder in folders:
            if folder["id"] == folder_id:
                folder = {**folder, "name": cleaned_name}
                renamed = folder
            next_folders.append(folder)
        if renamed is None:
            return None
        await self._save(owner_user_id, next_folders)
        return renamed

    async def delete_folder(self, owner_user_id: int, folder_id: str) -> bool:
        folders = await self._load(owner_user_id)
        next_folders = [folder for folder in folders if folder["id"] != folder_id]
        if len(next_folders) == len(folders):
            return False
        await self._save(owner_user_id, next_folders)
        return True

    async def add_assets(self, owner_user_id: int, folder_id: str, asset_ids: list[str]) -> dict[str, Any] | None:
        folders = await self._load(owner_user_id)
        added_ids = self._unique_asset_ids(asset_ids)
        updated: dict[str, Any] | None = None
        next_folders: list[dict[str, Any]] = []
        for folder in folders:
            if folder["id"] == folder_id:
                existing = self._unique_asset_ids(folder.get("assetIds", []))
                folder = {**folder, "assetIds": self._unique_asset_ids([*added_ids, *existing])}
                updated = folder
            next_folders.append(folder)
        if updated is None:
            return None
        await self._save(owner_user_id, next_folders)
        return updated

    async def remove_asset(self, owner_user_id: int, folder_id: str, asset_id: str) -> dict[str, Any] | None:
        folders = await self._load(owner_user_id)
        updated: dict[str, Any] | None = None
        next_folders: list[dict[str, Any]] = []
        for folder in folders:
            if folder["id"] == folder_id:
                folder = {
                    **folder,
                    "assetIds": [item for item in self._unique_asset_ids(folder.get("assetIds", [])) if item != asset_id],
                }
                updated = folder
            next_folders.append(folder)
        if updated is None:
            return None
        await self._save(owner_user_id, next_folders)
        return updated

    async def remove_asset_from_all(self, owner_user_id: int, asset_id: str) -> None:
        folders = await self._load(owner_user_id)
        next_folders = [
            {
                **folder,
                "assetIds": [item for item in self._unique_asset_ids(folder.get("assetIds", [])) if item != asset_id],
            }
            for folder in folders
        ]
        await self._save(owner_user_id, next_folders)

    async def _load(self, owner_user_id: int) -> list[dict[str, Any]]:
        raw = await self._redis.get(self._key(owner_user_id))
        if raw is None:
            return []
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        folders: list[dict[str, Any]] = []
        for item in parsed:
            folder = self._normalize_folder(item)
            if folder is not None:
                folders.append(folder)
        return folders

    async def _save(self, owner_user_id: int, folders: list[dict[str, Any]]) -> None:
        await self._redis.set(self._key(owner_user_id), json.dumps(folders, ensure_ascii=False))

    @staticmethod
    def _key(owner_user_id: int) -> str:
        return f"material:favorites:{owner_user_id}"

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _folder_id() -> str:
        return f"favorite-{uuid4().hex}"

    @classmethod
    def _normalize_folder(cls, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        folder_id = item.get("id")
        name = item.get("name")
        if not isinstance(folder_id, str) or not folder_id.strip():
            return None
        if not isinstance(name, str) or not name.strip():
            return None
        created_at = item.get("createdAt")
        return {
            "id": folder_id,
            "name": name.strip(),
            "assetIds": cls._unique_asset_ids(item.get("assetIds", [])),
            "createdAt": created_at if isinstance(created_at, str) and created_at else cls._now(),
        }

    @staticmethod
    def _unique_asset_ids(asset_ids: list[str] | Any) -> list[str]:
        if not isinstance(asset_ids, list):
            return []
        seen: set[str] = set()
        result: list[str] = []
        for asset_id in asset_ids:
            if not isinstance(asset_id, str):
                continue
            cleaned = asset_id.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            result.append(cleaned)
        return result
