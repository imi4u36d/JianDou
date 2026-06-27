from __future__ import annotations

import pytest

from backend.services.material_favorite_service import MaterialFavoriteService

pytestmark = pytest.mark.service


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


async def test_material_favorite_service_creates_and_batches_assets() -> None:
    service = MaterialFavoriteService(FakeRedis())

    folder = await service.create_folder(7, name="喜欢", asset_ids=["mat_1", "mat_1", "mat_2"])
    updated = await service.add_assets(7, folder["id"], ["mat_3", "mat_2"])

    assert updated is not None
    assert updated["assetIds"] == ["mat_3", "mat_2", "mat_1"]
    assert await service.list_folders(8) == []


async def test_material_favorite_service_rejects_duplicate_names() -> None:
    service = MaterialFavoriteService(FakeRedis())

    first = await service.create_folder(7, name="喜欢")
    await service.create_folder(7, name="备用")

    with pytest.raises(ValueError, match="favorite_folder_name_exists"):
        await service.rename_folder(7, first["id"], name="备用")


async def test_material_favorite_service_removes_deleted_asset_from_all_folders() -> None:
    service = MaterialFavoriteService(FakeRedis())

    first = await service.create_folder(7, name="喜欢", asset_ids=["mat_1", "mat_2"])
    second = await service.create_folder(7, name="备选", asset_ids=["mat_2", "mat_3"])

    await service.remove_asset_from_all(7, "mat_2")

    folders = {folder["id"]: folder for folder in await service.list_folders(7)}
    assert folders[first["id"]]["assetIds"] == ["mat_1"]
    assert folders[second["id"]]["assetIds"] == ["mat_3"]
