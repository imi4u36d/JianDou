"""Request contract tests for schema-backed routers."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from backend.auth import create_access_token, create_token_data, hash_password
from backend.domain.enums import UserRole, UserStatus
from backend.models.task import BizMaterialAsset
from backend.models.user import SysUser
from backend.models.workflow import BizStageWorkflow


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _create_user_session(client, db_session_factory, *, username: str, role: str = UserRole.USER.value) -> int:
    now = _now_iso()
    async with db_session_factory() as session:
        user = SysUser(
            username=username,
            display_name=username,
            password_hash=hash_password("test-password"),
            role=role,
            status=UserStatus.ACTIVE.value,
            task_concurrency_limit=1,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = int(user.id)
    token = create_access_token(create_token_data(user_id, username, role))
    client.cookies.set("access_token", token)
    return user_id


async def test_material_generation_accepts_camel_case_payload(auth_client, db_session_factory):
    response = await auth_client.post(
        "/api/v3/material-center/generations",
        json={
            "title": "Opening frame",
            "assetType": "reference",
            "description": "A polished product shot",
            "styleKeywords": ["clean", "studio"],
            "aspectRatio": "16:9",
            "imageSize": "1024x576",
            "seed": 42,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Opening frame"
    assert data["asset"]["assetType"] == "reference"
    assert data["metadata"]["styleKeywords"] == ["clean", "studio"]
    assert data["metadata"]["seed"] == 42
    async with db_session_factory() as session:
        result = await session.execute(
            select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == data["id"])
        )
        row = result.scalar_one()
        assert row.title == "Opening frame"
        assert row.asset_role == "reference"


async def test_material_rating_rejects_out_of_range_score(client):
    response = await client.patch(
        "/api/v3/material-assets/mat_contract/rating",
        json={"effectRating": 6, "effectRatingNote": "too high"},
    )

    assert response.status_code == 422


async def test_material_assets_require_authentication(client):
    response = await client.get("/api/v3/material-assets")

    assert response.status_code == 401


async def test_material_asset_library_is_database_backed(auth_client):
    create_response = await auth_client.post("/api/v3/material-assets/images")
    assert create_response.status_code == 200
    asset = create_response.json()

    list_response = await auth_client.get("/api/v3/material-assets?type=image")
    assert list_response.status_code == 200
    page = list_response.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == asset["id"]

    rate_response = await auth_client.patch(
        f"/api/v3/material-assets/{asset['id']}/rating",
        json={"effectRating": 5, "effectRatingNote": "useful"},
    )
    assert rate_response.status_code == 200
    assert rate_response.json()["userRating"] == 5

    delete_response = await auth_client.delete(f"/api/v3/material-assets/{asset['id']}")
    assert delete_response.status_code == 200

    empty_response = await auth_client.get("/api/v3/material-assets?type=image")
    assert empty_response.status_code == 200
    assert empty_response.json()["total"] == 0


async def test_material_asset_reuse_creates_persisted_workflow(auth_client, db_session_factory):
    create_response = await auth_client.post("/api/v3/material-assets/images")
    assert create_response.status_code == 200
    asset = create_response.json()

    reuse_response = await auth_client.post(f"/api/v3/material-assets/{asset['id']}/reuse", json={"mode": "clone"})
    assert reuse_response.status_code == 200
    workflow = reuse_response.json()
    assert workflow["finalResult"]["id"] == asset["id"]

    async with db_session_factory() as session:
        result = await session.execute(
            select(BizStageWorkflow).where(BizStageWorkflow.workflow_id == workflow["id"])
        )
        row = result.scalar_one()
        assert row.final_join_asset_id == asset["id"]
        assert row.owner_user_id > 0

    detail_response = await auth_client.get(f"/api/v3/workflows/{workflow['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == workflow["id"]
    assert detail["finalResult"]["id"] == asset["id"]


async def test_workflow_detail_and_mutations_enforce_owner_boundary(auth_client, db_session_factory):
    create_response = await auth_client.post("/api/v3/material-assets/images")
    assert create_response.status_code == 200
    asset = create_response.json()

    reuse_response = await auth_client.post(f"/api/v3/material-assets/{asset['id']}/reuse", json={"mode": "clone"})
    assert reuse_response.status_code == 200
    workflow = reuse_response.json()

    await _create_user_session(auth_client, db_session_factory, username="workflow_intruder")

    detail_response = await auth_client.get(f"/api/v3/workflows/{workflow['id']}")
    assert detail_response.status_code == 404

    rating_response = await auth_client.post(
        f"/api/v3/workflows/{workflow['id']}/rating",
        json={"effectRating": 5, "effectRatingNote": "not mine"},
    )
    assert rating_response.status_code == 404

    async with db_session_factory() as session:
        result = await session.execute(
            select(BizStageWorkflow).where(BizStageWorkflow.workflow_id == workflow["id"])
        )
        row = result.scalar_one()
        assert row.effect_rating is None


async def test_generation_run_requires_object_payload(client):
    response = await client.post("/api/v3/generation/runs", json=["invalid"])

    assert response.status_code == 422


async def test_workflow_create_requires_title(auth_client):
    response = await auth_client.post(
        "/api/v3/workflows",
        json={"aspectRatio": "16:9"},
    )

    assert response.status_code == 422


async def test_workflow_select_character_asset_requires_asset_id(auth_client):
    response = await auth_client.post(
        "/api/v3/workflows/wf_missing/character-sheets/0/select-asset",
        json={"assetId": ""},
    )

    assert response.status_code == 422
