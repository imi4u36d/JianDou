from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
import pytest

from backend.services.material_asset_service import MaterialAssetService


async def test_material_asset_service_rejects_cross_owner_upsert(db_session) -> None:
    service = MaterialAssetService(db_session)
    await service.create_asset(1, asset_id="mat_shared", title="owner one")

    with pytest.raises(ValueError, match="material_asset_id_already_exists"):
        await service.upsert_asset(2, asset_id="mat_shared", title="owner two")
