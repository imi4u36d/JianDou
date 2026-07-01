from __future__ import annotations

import pytest

pytestmark = pytest.mark.service

from sqlalchemy import select

from backend.models.task import BizMaterialAsset
from backend.services.material_asset_service import MaterialAssetService


async def test_material_asset_service_rejects_cross_owner_upsert(db_session) -> None:
    service = MaterialAssetService(db_session)
    await service.create_asset(1, asset_id="mat_shared", title="owner one")

    with pytest.raises(ValueError, match="material_asset_id_already_exists"):
        await service.upsert_asset(2, asset_id="mat_shared", title="owner two")


async def test_material_asset_service_renames_owned_asset(db_session) -> None:
    service = MaterialAssetService(db_session)
    await service.create_asset(1, asset_id="mat_rename", title="old name")

    renamed = await service.rename_asset(1, "mat_rename", title="new name")
    missing = await service.rename_asset(2, "mat_rename", title="intruder name")

    assert renamed is not None
    assert renamed["title"] == "new name"
    assert missing is None

    row_result = await db_session.execute(
        select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == "mat_rename")
    )
    row = row_result.scalar_one()
    assert row.title == "new name"


async def test_material_asset_service_hides_workflow_artifacts_by_default(db_session) -> None:
    service = MaterialAssetService(db_session)
    await service.create_asset(1, asset_id="mat_single_task", title="single task", mediaType="image")
    await service.create_asset(1, asset_id="mat_workflow", title="workflow", mediaType="image", workflowId="wf_material")
    await service.create_asset(1, asset_id="mat_legacy_workflow", title="legacy workflow", mediaType="image", assetType="workflow")

    default_page = await service.list_assets(1, media_type="image")

    assert default_page["total"] == 1
    assert [item["id"] for item in default_page["items"]] == ["mat_single_task"]

    included_page = await service.list_assets(1, media_type="image", include_workflow_artifacts=True)

    assert included_page["total"] == 3
    assert {item["id"] for item in included_page["items"]} == {
        "mat_single_task",
        "mat_workflow",
        "mat_legacy_workflow",
    }

    workflow_page = await service.list_assets(1, media_type="image", asset_type="workflow")

    assert workflow_page["total"] == 2
    assert {item["id"] for item in workflow_page["items"]} == {"mat_workflow", "mat_legacy_workflow"}


async def test_material_asset_service_normalizes_legacy_url_inputs(db_session) -> None:
    service = MaterialAssetService(db_session)

    view = await service.create_asset(
        1,
        asset_id="mat_legacy_urls",
        title="legacy",
        mediaType="image",
        remoteUrl="https://cdn.example.test/original.png",
        thirdPartyUrl="https://provider.example.test/original.png",
        previewUrl="/storage/thumb.jpg",
    )

    row_result = await db_session.execute(
        select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == "mat_legacy_urls")
    )
    row = row_result.scalar_one()
    assert row.public_url == "https://cdn.example.test/original.png"
    assert row.thumbnail_url == "/storage/thumb.jpg"
    assert row.remote_url is None
    assert row.third_party_url is None
    assert view["publicUrl"] == "https://cdn.example.test/original.png"
    assert view["fileUrl"] == "https://cdn.example.test/original.png"
    assert view["thumbnailUrl"] == "/storage/thumb.jpg"
    assert view["previewUrl"] == "/storage/thumb.jpg"
    assert view["remoteUrl"] == ""
