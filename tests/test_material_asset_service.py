from __future__ import annotations

import pytest

pytestmark = pytest.mark.service

from backend.services.material_asset_service import MaterialAssetService


async def test_material_asset_service_rejects_cross_owner_upsert(db_session) -> None:
    service = MaterialAssetService(db_session)
    await service.create_asset(1, asset_id="mat_shared", title="owner one")

    with pytest.raises(ValueError, match="material_asset_id_already_exists"):
        await service.upsert_asset(2, asset_id="mat_shared", title="owner two")


async def test_material_asset_service_hides_workflow_artifacts_by_default(db_session) -> None:
    service = MaterialAssetService(db_session)
    await service.create_asset(1, asset_id="mat_single_task", title="single task", mediaType="image")
    await service.create_asset(1, asset_id="mat_workflow", title="workflow", mediaType="image", workflowId="wf_material")

    default_page = await service.list_assets(1, media_type="image")

    assert default_page["total"] == 1
    assert [item["id"] for item in default_page["items"]] == ["mat_single_task"]

    included_page = await service.list_assets(1, media_type="image", include_workflow_artifacts=True)

    assert included_page["total"] == 2
    assert {item["id"] for item in included_page["items"]} == {"mat_single_task", "mat_workflow"}
