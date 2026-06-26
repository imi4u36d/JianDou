from __future__ import annotations

import pytest

from backend.models.public_share import BizPublicShare
from backend.models.task import BizMaterialAsset

pytestmark = pytest.mark.api


def _asset_row(**overrides):
    row = {
        "material_asset_id": "asset_public_image",
        "remark": "",
        "owner_user_id": 1,
        "task_id": "task_public",
        "workflow_id": None,
        "source_task_id": None,
        "source_material_id": None,
        "asset_role": "final",
        "stage_type": "joined",
        "clip_index": 0,
        "version_no": 1,
        "selected_for_next": 0,
        "user_rating": None,
        "rating_note": None,
        "media_type": "image",
        "title": "公开图片",
        "origin_provider": "",
        "origin_model": "",
        "remote_task_id": "",
        "remote_asset_id": "",
        "original_file_name": "image.png",
        "stored_file_name": "image.png",
        "file_ext": "png",
        "storage_provider": "local",
        "mime_type": "image/png",
        "size_bytes": 100,
        "sha256": None,
        "duration_seconds": None,
        "width": 1024,
        "height": 1024,
        "has_audio": 0,
        "local_storage_path": "",
        "local_file_path": "",
        "public_url": "/storage/image.png",
        "thumbnail_url": "/storage/thumb.png",
        "third_party_url": None,
        "remote_url": None,
        "metadata_json": "{}",
        "captured_at": "2026-01-01T00:00:00+00:00",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
    }
    row.update(overrides)
    return BizMaterialAsset(**row)


async def _seed_assets(db_session_factory):
    async with db_session_factory() as session:
        session.add_all([
            _asset_row(),
            _asset_row(
                material_asset_id="asset_public_video",
                media_type="video",
                title="公开视频",
                mime_type="video/mp4",
                public_url="/storage/video.mp4",
                thumbnail_url="/storage/video.jpg",
                width=1280,
                height=720,
                duration_seconds=8.0,
            ),
            _asset_row(
                material_asset_id="asset_other_user",
                owner_user_id=2,
                task_id="task_other",
                title="别人的图",
                public_url="/storage/other.png",
            ),
        ])
        await session.commit()


async def test_create_public_share_requires_auth(client):
    response = await client.post(
        "/api/v3/public-shares",
        json={"materialAssetId": "asset_public_image", "sourceType": "task", "sourceId": "task_public"},
    )

    assert response.status_code == 401


async def test_create_public_share_reuses_existing_material_share(auth_client, db_session_factory):
    await _seed_assets(db_session_factory)

    payload = {"materialAssetId": "asset_public_image", "sourceType": "material", "sourceId": "asset_public_image"}
    first = await auth_client.post("/api/v3/public-shares", json=payload)
    second = await auth_client.post("/api/v3/public-shares", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["shareId"] == second.json()["shareId"]
    assert second.json()["mediaType"] == "image"
    assert second.json()["publicUrl"] == "/storage/image.png"
    assert second.json()["fileUrl"] == "/storage/image.png"
    assert second.json()["thumbnailUrl"] == "/storage/thumb.png"
    assert second.json()["previewUrl"] == "/storage/thumb.png"


async def test_public_share_rejects_unowned_asset(auth_client, db_session_factory):
    await _seed_assets(db_session_factory)

    response = await auth_client.post(
        "/api/v3/public-shares",
        json={"materialAssetId": "asset_other_user", "sourceType": "task", "sourceId": "task_other"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "material_asset_not_found"


async def test_list_public_shares_filters_and_sorts(auth_client, db_session_factory):
    await _seed_assets(db_session_factory)
    image = await auth_client.post(
        "/api/v3/public-shares",
        json={"materialAssetId": "asset_public_image", "sourceType": "task", "sourceId": "task_public"},
    )
    video = await auth_client.post(
        "/api/v3/public-shares",
        json={"materialAssetId": "asset_public_video", "sourceType": "task", "sourceId": "task_public"},
    )
    assert image.status_code == 200
    assert video.status_code == 200
    await auth_client.post(f"/api/v3/public-shares/{video.json()['shareId']}/like")

    images = await auth_client.get("/api/v3/public-shares?type=image&sort=popular")
    videos = await auth_client.get("/api/v3/public-shares?type=video&sort=popular")

    assert images.status_code == 200
    assert [item["mediaType"] for item in images.json()["items"]] == ["image"]
    assert videos.status_code == 200
    assert videos.json()["items"][0]["shareId"] == video.json()["shareId"]
    assert videos.json()["items"][0]["publicUrl"] == "/storage/video.mp4"
    assert videos.json()["items"][0]["thumbnailUrl"] == "/storage/video.jpg"
    assert videos.json()["items"][0]["previewUrl"] == "/storage/video.jpg"
    assert videos.json()["items"][0]["likedByMe"] is True
    assert videos.json()["items"][0]["likeCount"] == 1


async def test_like_public_share_is_idempotent(auth_client, db_session_factory):
    await _seed_assets(db_session_factory)
    created = await auth_client.post(
        "/api/v3/public-shares",
        json={"materialAssetId": "asset_public_image", "sourceType": "task", "sourceId": "task_public"},
    )
    share_id = created.json()["shareId"]

    first = await auth_client.post(f"/api/v3/public-shares/{share_id}/like")
    second = await auth_client.post(f"/api/v3/public-shares/{share_id}/like")
    removed = await auth_client.delete(f"/api/v3/public-shares/{share_id}/like")
    removed_again = await auth_client.delete(f"/api/v3/public-shares/{share_id}/like")

    assert first.json()["likeCount"] == 1
    assert second.json()["likeCount"] == 1
    assert removed.json()["likeCount"] == 0
    assert removed_again.json()["likeCount"] == 0


async def test_remove_public_share_hides_from_gallery(auth_client, db_session_factory):
    await _seed_assets(db_session_factory)
    created = await auth_client.post(
        "/api/v3/public-shares",
        json={"materialAssetId": "asset_public_image", "sourceType": "task", "sourceId": "task_public"},
    )
    share_id = created.json()["shareId"]

    deleted = await auth_client.delete(f"/api/v3/public-shares/{share_id}")
    listed = await auth_client.get("/api/v3/public-shares?type=image")

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "shareId": share_id}
    assert listed.json()["items"] == []


async def test_other_user_cannot_remove_share(auth_client, db_session_factory):
    async with db_session_factory() as session:
        session.add(_asset_row(material_asset_id="asset_other_active", owner_user_id=2, task_id="task_other"))
        session.add(
            BizPublicShare(
                share_id="share_other_user",
                owner_user_id=2,
                material_asset_id="asset_other_active",
                source_type="task",
                source_id="task_other",
                media_type="image",
                title="别人的分享",
                status="ACTIVE",
                like_count=0,
                create_time="2026-01-01T00:00:00+00:00",
                update_time="2026-01-01T00:00:00+00:00",
                is_deleted=0,
                remark="",
            )
        )
        await session.commit()

    response = await auth_client.delete("/api/v3/public-shares/share_other_user")

    assert response.status_code == 404
