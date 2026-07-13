from __future__ import annotations

import pytest

import backend.infrastructure.task_repository as task_repository_module
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.infrastructure.task_repository_aggregate_loader import TaskRepositoryAggregateLoader
from backend.infrastructure.task_repository_detail_collections import TaskRepositoryDetailCollectionQueryService
from backend.infrastructure.task_repository_detail_queries import TaskRepositoryDetailQueryService
from backend.infrastructure.task_repository_mutations import TaskRepositoryMutationService
from backend.infrastructure.task_repository_queries import TaskRepositoryQueryService
from backend.infrastructure.task_repository_queue import TaskRepositoryQueueService


class _FakeSession:
    def __init__(self, name: str) -> None:
        self.name = name
        self.closed = False

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()

    async def close(self) -> None:
        self.closed = True


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[_FakeSession] = []

    def __call__(self) -> _FakeSession:
        session = _FakeSession(f"session-{len(self.sessions) + 1}")
        self.sessions.append(session)
        return session


@pytest.mark.asyncio
async def test_default_repository_session_scope_uses_short_lived_session(monkeypatch) -> None:
    factory = _FakeSessionFactory()
    monkeypatch.setattr(task_repository_module, "async_session_factory", factory)
    repository = TaskRepository()

    long_lived_session = repository.session
    async with repository._session_scope() as scoped:
        assert scoped is not long_lived_session
        assert scoped.name == "session-2"

    assert len(factory.sessions) == 2
    assert factory.sessions[1].closed is True
    await repository.close()


@pytest.mark.asyncio
async def test_external_repository_session_scope_reuses_injected_session(monkeypatch) -> None:
    factory = _FakeSessionFactory()
    monkeypatch.setattr(task_repository_module, "async_session_factory", factory)
    external_session = _FakeSession("external")
    repository = TaskRepository(external_session)

    async with repository._session_scope() as scoped:
        assert scoped is external_session

    assert factory.sessions == []
    assert external_session.closed is False


def test_repository_delegates_read_models_to_query_service() -> None:
    repository = TaskRepository()
    detail_service = repository._query_service()._detail_service()

    assert isinstance(repository._query_service(), TaskRepositoryQueryService)
    assert isinstance(detail_service, TaskRepositoryDetailQueryService)
    assert isinstance(detail_service._collection_service(), TaskRepositoryDetailCollectionQueryService)


def test_repository_delegates_atomic_writes_to_mutation_service() -> None:
    repository = TaskRepository()

    assert isinstance(repository._mutation_service(), TaskRepositoryMutationService)


def test_repository_delegates_full_aggregate_loading() -> None:
    repository = TaskRepository()

    assert isinstance(repository._aggregate_loader(), TaskRepositoryAggregateLoader)


def test_repository_delegates_queue_and_worker_persistence() -> None:
    repository = TaskRepository()

    assert isinstance(repository._queue_service(), TaskRepositoryQueueService)


@pytest.mark.asyncio
async def test_load_sub_collections_delegates_each_collection_in_order(monkeypatch) -> None:
    repository = TaskRepository()
    aggregate_loader = TaskRepositoryAggregateLoader(repository)
    task = TaskRecord(id="task-1")
    calls: list[tuple[str, TaskRecord, str]] = []

    def loader(name: str):
        async def load(record: TaskRecord, task_id: str) -> None:
            calls.append((name, record, task_id))

        return load

    for name in ("attempts", "status_history", "model_calls", "materials", "results"):
        monkeypatch.setattr(aggregate_loader, f"_load_{name}", loader(name))

    await aggregate_loader._load_sub_collections(task)

    assert calls == [
        ("attempts", task, "task-1"),
        ("status_history", task, "task-1"),
        ("model_calls", task, "task-1"),
        ("materials", task, "task-1"),
        ("results", task, "task-1"),
    ]
