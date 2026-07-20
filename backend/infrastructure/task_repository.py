from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session_factory
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository_aggregate_loader import TaskRepositoryAggregateLoader
from backend.infrastructure.task_repository_mapping import (
    _biz_task_from_record,
    _record_from_biz_task,
)
from backend.infrastructure.task_repository_mutations import TaskRepositoryMutationService
from backend.infrastructure.task_repository_overview import TaskRepositoryOverviewService
from backend.infrastructure.task_repository_queries import TaskRepositoryQueryService
from backend.infrastructure.task_repository_queue import TaskRepositoryQueueService
from backend.models.task import (
    BizMaterialAsset,
    BizTask,
    BizTaskAttempt,
    BizWorkerInstance,
)
from backend.shared import now_iso


class TaskRepository:
    """SQLAlchemy-based repository for TaskRecord aggregates.

    Mirrors the Java MybatisTaskRepository.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._uses_external_session = session is not None
        self._lock = asyncio.Lock()

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            self._session = async_session_factory()
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    @asynccontextmanager
    async def _session_scope(self):
        if self._uses_external_session and self._session is not None:
            yield self._session
            return
        async with async_session_factory() as session:
            yield session

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def _find_task_row(self, task_id: str) -> BizTask | None:
        result = await self.session.execute(
            select(BizTask).where(
                BizTask.task_id == task_id,
                BizTask.is_deleted == 0,
            )
        )
        return result.scalars().first()

    async def _find_attempt_row(self, attempt_id: str) -> BizTaskAttempt | None:
        result = await self.session.execute(select(BizTaskAttempt).where(BizTaskAttempt.task_attempt_id == attempt_id))
        return result.scalars().first()

    async def _find_worker_row(self, worker_instance_id: str) -> BizWorkerInstance | None:
        result = await self.session.execute(
            select(BizWorkerInstance).where(BizWorkerInstance.worker_instance_id == worker_instance_id)
        )
        return result.scalars().first()

    async def _find_material_row(self, material_asset_id: str) -> BizMaterialAsset | None:
        result = await self.session.execute(
            select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == material_asset_id)
        )
        return result.scalars().first()

    async def _load_task_record_without_lock(self, task_id: str) -> TaskRecord | None:
        return await self._aggregate_loader().load_task_record_without_lock(task_id)

    async def _save_without_lock(self, task_record: TaskRecord) -> None:
        row = _biz_task_from_record(task_record)
        existing = await self._find_task_row(task_record.id)
        if existing:
            for col in BizTask.__table__.columns:
                col_name = col.name
                if col_name in {"id", "task_id"}:
                    continue
                if hasattr(row, col_name):
                    setattr(existing, col_name, getattr(row, col_name))
        else:
            self.session.add(row)

    async def save(self, task_record: TaskRecord) -> None:
        await self._mutation_service().save(task_record)

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        await self._mutation_service().save_mutation(mutation)

    async def find_by_id(self, task_id: str) -> TaskRecord | None:
        """Load a task with all related sub-collections."""
        async with self._lock:
            return await self._load_task_record_without_lock(task_id)

    def _aggregate_loader(self) -> TaskRepositoryAggregateLoader:
        return TaskRepositoryAggregateLoader(self)

    def _mutation_service(self) -> TaskRepositoryMutationService:
        return TaskRepositoryMutationService(self)

    def _query_service(self) -> TaskRepositoryQueryService:
        return TaskRepositoryQueryService(self)

    def _queue_service(self) -> TaskRepositoryQueueService:
        return TaskRepositoryQueueService(self)

    def _overview_service(self) -> TaskRepositoryOverviewService:
        return TaskRepositoryOverviewService(self)

    async def list_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return await self._query_service().list_task_summaries(
            owner_user_id, q, status, sort, task_type, exclude_task_type, offset, limit
        )

    async def count_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
    ) -> int:
        return await self._query_service().count_task_summaries(owner_user_id, q, status, task_type, exclude_task_type)

    async def admin_overview_snapshot(self) -> dict[str, Any]:
        return await self._overview_service().snapshot()

    async def find_detail_light(self, task_id: str, owner_user_id: int | None = None) -> dict[str, Any] | None:
        return await self._query_service().find_detail_light(task_id, owner_user_id)

    async def get_task_trace(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service().get_task_trace(task_id, owner_user_id, limit)

    async def get_task_outputs_light(
        self,
        task_id: str,
        owner_user_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        return await self._query_service().get_task_outputs_light(task_id, owner_user_id, session)

    async def get_task_materials_light(
        self,
        task_id: str,
        owner_user_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        return await self._query_service().get_task_materials_light(task_id, owner_user_id, session)

    async def list_queued_task_ids(self, limit: int = 500) -> list[str]:
        return await self._queue_service().list_queued_task_ids(limit)

    async def claim_next_queued_task(self, worker_instance_id: str) -> str | None:
        return await self._queue_service().claim_next_queued_task(worker_instance_id)

    async def remove_queued_task(self, task_id: str) -> None:
        await self._queue_service().remove_queued_task(task_id)

    async def find_all(self) -> list[TaskRecord]:
        """Load all non-deleted tasks."""
        async with self._lock:
            stmt = select(BizTask).where(BizTask.is_deleted == 0).order_by(BizTask.create_time.desc())
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            records = [_record_from_biz_task(r) for r in rows]
            for rec in records:
                await self._load_sub_collections(rec)
            return records

    async def delete(self, task_id: str) -> None:
        """Soft delete a task."""
        async with self._lock:
            try:
                stmt = update(BizTask).where(BizTask.task_id == task_id).values(is_deleted=1, update_time=now_iso())
                await self.session.execute(stmt)
                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    # ------------------------------------------------------------------
    # Query helpers (matching Java TaskPersistencePort)
    # ------------------------------------------------------------------

    async def list_traces(
        self,
        task_id: str | None,
        stage: str | None,
        level: str | None,
        q: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await self._query_service().list_traces(task_id, stage, level, q, limit)

    async def list_queue_events(
        self,
        task_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await self._queue_service().list_queue_events(task_id, limit)

    async def list_worker_instances(self, limit: int) -> list[dict[str, Any]]:
        return await self._queue_service().list_worker_instances(limit)

    async def find_worker_instance(self, worker_instance_id: str) -> dict[str, Any] | None:
        return await self._queue_service().find_worker_instance(worker_instance_id)

    async def list_stale_worker_instance_ids(
        self,
        stale_before: Any,
        limit: int,
    ) -> list[str]:
        return await self._queue_service().list_stale_worker_instance_ids(stale_before, limit)

    async def list_stale_running_claims(
        self,
        stale_before: Any,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await self._queue_service().list_stale_running_claims(stale_before, limit)

    async def list_orphaned_running_claims(self, limit: int) -> list[dict[str, Any]]:
        return await self._queue_service().list_orphaned_running_claims(limit)

    async def list_user_queue_stats(self) -> list[dict[str, Any]]:
        return await self._queue_service().list_user_queue_stats()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
