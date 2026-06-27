from __future__ import annotations

import pytest

import backend.infrastructure.task_repository as task_repository_module
from backend.infrastructure.task_repository import TaskRepository


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
