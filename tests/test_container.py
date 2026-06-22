"""Tests for backend/container.py — DI container."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api
import pytest

from backend.config import Settings
from backend.container import AppContainer


@pytest.fixture
def container():
    settings = Settings(_env_file=None)  # Don't read .env
    settings.app_env = "dev"
    return AppContainer(settings)


class TestAppContainer:
    def test_config_is_stored(self, container):
        assert container.config is not None
        assert container.config.app_env == "dev"

    def test_task_repository_singleton(self, container):
        r1 = container.task_repository
        r2 = container.task_repository
        assert r1 is r2

    def test_execution_coordinator_singleton(self, container):
        c1 = container.execution_coordinator
        c2 = container.execution_coordinator
        assert c1 is c2

    def test_model_resolver_singleton(self, container):
        m1 = container.model_resolver
        m2 = container.model_resolver
        assert m1 is m2

    def test_generation_application_service_singleton(self, container):
        g1 = container.generation_application_service
        g2 = container.generation_application_service
        assert g1 is g2

    def test_task_application_service_singleton(self, container):
        t1 = container.task_application_service
        t2 = container.task_application_service
        assert t1 is t2

    def test_worker_runner_singleton(self, container):
        w1 = container.worker_runner
        w2 = container.worker_runner
        assert w1 is w2

    def test_all_services_are_lazy(self, container):
        """Services should only be created on first access."""
        assert "_task_repository" not in container.__dict__
        assert "_execution_coordinator" not in container.__dict__
        assert "_model_resolver" not in container.__dict__

    def test_bind_app_state_populates_state(self, container):
        """bind_app_state should set all expected attributes on app.state."""
        from unittest.mock import Mock

        app = Mock()
        container.bind_app_state(app)

        assert app.state.task_application_service is not None
        assert app.state.generation_application_service is not None
        assert app.state.task_repository is not None
        assert app.state.model_resolver is not None
        assert app.state.worker_runner is not None
        assert app.state.container is container


class TestAppContainerProviders:
    """Tests for model provider properties added during refactoring."""

    def test_text_model_provider_singleton(self, container):
        p1 = container.text_model_provider
        p2 = container.text_model_provider
        assert p1 is p2

    def test_prompt_template_resolver_singleton(self, container):
        p1 = container.prompt_template_resolver
        p2 = container.prompt_template_resolver
        assert p1 is p2

    def test_image_model_provider_singleton(self, container):
        p1 = container.image_model_provider
        p2 = container.image_model_provider
        assert p1 is p2

    def test_video_model_provider_singleton(self, container):
        p1 = container.video_model_provider
        p2 = container.video_model_provider
        assert p1 is p2

    def test_providers_are_distinct_instances(self, container):
        """Each provider should be a different object."""
        text = container.text_model_provider
        image = container.image_model_provider
        video = container.video_model_provider
        resolver = container.prompt_template_resolver
        assert text is not image
        assert image is not video
        assert text is not resolver

    def test_all_providers_are_lazy(self, container):
        """Providers should only be created on first access."""
        assert "_text_model_provider" not in container.__dict__
        assert "_image_model_provider" not in container.__dict__
        assert "_video_model_provider" not in container.__dict__
        assert "_prompt_template_resolver" not in container.__dict__

    def test_generation_service_uses_configured_providers(self, container):
        """GenerationApplicationService should receive providers from the container."""
        gen_service = container.generation_application_service
        assert gen_service is not None
        # The factory should have been created with providers
        factory = getattr(gen_service, "_factory", None)
        assert factory is not None
        # Provider references should be set (not None)
        assert factory._text_provider is not None
        assert factory._config_resolver is not None
