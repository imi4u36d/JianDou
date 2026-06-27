from __future__ import annotations

import pytest
from sqlalchemy import func, select

from backend.models.user import SysUserPreference
from backend.routers.generation import _catalog_with_user_default, _supported_aspect_ratios
from backend.services.user_generation_preferences import UserGenerationPreferenceService

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_user_aspect_ratio_preference_is_database_backed_and_scoped_by_user_id(db_session_factory) -> None:
    service = UserGenerationPreferenceService(db_session_factory)

    await service.set_default_aspect_ratio(7, "9:16")
    await service.set_default_aspect_ratio(8, "1:1")
    await service.set_default_aspect_ratio(7, "16:9")

    assert await service.default_aspect_ratio(7) == "16:9"
    assert await service.default_aspect_ratio(8) == "1:1"

    async with db_session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(SysUserPreference))
        rows = (await session.execute(select(SysUserPreference))).scalars().all()

    assert count == 2
    assert {(row.user_id, row.preference_key, row.preference_value) for row in rows} == {
        (7, UserGenerationPreferenceService.DEFAULT_ASPECT_RATIO_KEY, "16:9"),
        (8, UserGenerationPreferenceService.DEFAULT_ASPECT_RATIO_KEY, "1:1"),
    }


def test_catalog_user_default_accepts_explicit_and_size_derived_ratios() -> None:
    catalog = {
        "aspectRatios": [{"value": "16:9", "label": "横版 16:9"}],
        "imageSizes": [{"value": "2048x2048", "width": 2048, "height": 2048}],
        "defaultAspectRatio": "16:9",
    }

    assert _supported_aspect_ratios(catalog) == {"智能", "16:9", "1:1"}
    assert _catalog_with_user_default(catalog, "1:1")["defaultAspectRatio"] == "1:1"
    assert _catalog_with_user_default(catalog, "智能")["defaultAspectRatio"] == "智能"
    assert catalog["defaultAspectRatio"] == "16:9"


def test_catalog_user_default_ignores_unsupported_ratio() -> None:
    catalog = {
        "aspectRatios": [{"value": "16:9", "label": "横版 16:9"}],
        "imageSizes": [],
        "defaultAspectRatio": "16:9",
    }

    assert _catalog_with_user_default(catalog, "123:456") is catalog
