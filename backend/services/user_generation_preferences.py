from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import SysUserPreference

SessionFactory = Callable[[], Any]


class UserGenerationPreferenceService:
    """Database-backed generation preferences scoped to a user identity."""

    DEFAULT_ASPECT_RATIO_KEY = "generation.default_aspect_ratio"

    def __init__(self, session_factory: SessionFactory | None = None) -> None:
        if session_factory is None:
            import backend.database as database

            session_factory = database.async_session_factory
        self._session_factory = session_factory

    async def default_aspect_ratio(self, user_id: int) -> str | None:
        if user_id <= 0:
            return None
        async with self._session_factory() as session:
            row = await self._preference_row(session, user_id, self.DEFAULT_ASPECT_RATIO_KEY)
            return self._normalize_aspect_ratio(row.preference_value if row else None)

    async def set_default_aspect_ratio(self, user_id: int, aspect_ratio: str | None) -> str | None:
        normalized = self._normalize_aspect_ratio(aspect_ratio)
        if user_id <= 0 or not normalized:
            return normalized
        async with self._session_factory() as session:
            row = await self._preference_row(session, user_id, self.DEFAULT_ASPECT_RATIO_KEY)
            now = self._now_iso()
            if row is None:
                row = SysUserPreference(
                    user_id=user_id,
                    preference_key=self.DEFAULT_ASPECT_RATIO_KEY,
                    preference_value=normalized,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.preference_value = normalized
                row.updated_at = now
            await session.commit()
        return normalized

    @staticmethod
    async def _preference_row(
        session: AsyncSession,
        user_id: int,
        preference_key: str,
    ) -> SysUserPreference | None:
        result = await session.execute(
            select(SysUserPreference).where(
                SysUserPreference.user_id == user_id,
                SysUserPreference.preference_key == preference_key,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _normalize_aspect_ratio(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _now_iso() -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()
