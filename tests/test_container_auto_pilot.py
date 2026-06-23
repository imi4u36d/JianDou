"""Tests for backend/container.py — auto-pilot runner wiring."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api

from backend.container import AppContainer


@pytest.fixture
def container():
    from backend.config import Settings

    settings = Settings(_env_file=None)
    settings.app_env = "dev"
    return AppContainer(settings)


class TestAutoPilotRunner:
    def test_auto_pilot_runner_singleton(self, container):
        r1 = container.auto_pilot_runner
        r2 = container.auto_pilot_runner
        assert r1 is r2

    def test_auto_pilot_runner_is_lazy(self, container):
        """auto_pilot_runner should only be created on first access."""
        assert "_auto_pilot_runner" not in container.__dict__
        _ = container.auto_pilot_runner
        assert "_auto_pilot_runner" in container.__dict__

    def test_auto_pilot_runner_has_is_running(self, container):
        runner = container.auto_pilot_runner
        assert hasattr(runner, "is_running")
        assert runner.is_running is False

    def test_auto_pilot_runner_has_enqueue(self, container):
        runner = container.auto_pilot_runner
        assert hasattr(runner, "enqueue")
        assert callable(runner.enqueue)

    def test_auto_pilot_runner_has_start_stop(self, container):
        runner = container.auto_pilot_runner
        assert hasattr(runner, "start")
        assert hasattr(runner, "stop")
        assert callable(runner.start)
        assert callable(runner.stop)

    def test_bind_app_state_populates_auto_pilot_runner(self, container):
        """bind_app_state should set auto_pilot_runner on app.state."""
        from unittest.mock import Mock

        app = Mock()
        container.bind_app_state(app)

        assert app.state.auto_pilot_runner is not None
        assert app.state.auto_pilot_runner is container.auto_pilot_runner
