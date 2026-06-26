"""Dependency-injection container for the JianDou backend.

``AppContainer`` centralises service creation and wiring.  It replaces
the ad-hoc manual wiring that was previously done inside ``create_app``.

Usage inside ``create_app``::

    container = AppContainer(settings)
    app.state.container = container
    container.bind_app_state(app)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


@dataclass
class AppContainer:
    """Holds all singletons and service references for the application.

    Services are created lazily via properties so that ordering
    dependencies are resolved naturally.
    """

    config: object  # Settings

    # -- Infrastructure ----------------------------------------------------

    @property
    def task_repository(self) -> TaskRepository:
        if "_task_repository" not in self.__dict__:
            from backend.infrastructure.task_repository import TaskRepository
            self.__dict__["_task_repository"] = TaskRepository()
        return self.__dict__["_task_repository"]

    @property
    def redis_client(self):
        if "_redis_client" not in self.__dict__:
            from backend.services.cache_service import create_redis_client

            self.__dict__["_redis_client"] = create_redis_client()
        return self.__dict__["_redis_client"]

    @property
    def json_cache(self):
        if "_json_cache" not in self.__dict__:
            from backend.services.cache_service import create_json_cache

            self.__dict__["_json_cache"] = create_json_cache(self.redis_client)
        return self.__dict__["_json_cache"]

    @property
    def execution_coordinator(self) -> TaskExecutionCoordinator:
        if "_execution_coordinator" not in self.__dict__:
            from backend.services.task_execution_coordinator import TaskExecutionCoordinator
            self.__dict__["_execution_coordinator"] = TaskExecutionCoordinator()
        return self.__dict__["_execution_coordinator"]

    @property
    def task_queue(self) -> TaskQueueCoordinator:
        if "_task_queue" not in self.__dict__:
            from backend.services.task_diagnosis_service import TaskQueueCoordinator
            self.__dict__["_task_queue"] = TaskQueueCoordinator(self.task_repository)
        return self.__dict__["_task_queue"]

    # -- Services ---------------------------------------------------------

    @property
    def credential_repository(self) -> SqlAlchemyUserModelCredentialRepository:
        if "_credential_repository" not in self.__dict__:
            from backend.services.model_config_service import SqlAlchemyUserModelCredentialRepository
            self.__dict__["_credential_repository"] = SqlAlchemyUserModelCredentialRepository(
                self.config.database_url
            )
        return self.__dict__["_credential_repository"]

    @property
    def model_resolver(self) -> ModelRuntimePropertiesResolver:
        if "_model_resolver" not in self.__dict__:
            from backend.services.model_config_service import ModelRuntimePropertiesResolver
            self.__dict__["_model_resolver"] = ModelRuntimePropertiesResolver(
                config_dir="./config",
                credential_provider=self.credential_repository,
            )
        return self.__dict__["_model_resolver"]

    @property
    def generation_application_service(self) -> DefaultGenerationApplicationService:
        if "_generation_application_service" not in self.__dict__:
            from backend.services.generation_service import (
                DefaultGenerationApplicationService,
                GenerationRunFactory,
            )
            factory = GenerationRunFactory(
                config_resolver=self.model_resolver,
                text_provider=self.text_model_provider,
                prompt_resolver=self.prompt_template_resolver,
                image_providers=self.image_model_providers,
                video_provider=self.video_model_provider,
            )
            self.__dict__["_generation_application_service"] = DefaultGenerationApplicationService(
                config_resolver=self.model_resolver,
                generation_run_factory=factory,
            )
        return self.__dict__["_generation_application_service"]

    @property
    def generation_catalog_service(self) -> GenerationCatalogService:
        if "_generation_catalog_service" not in self.__dict__:
            from backend.services.generation_catalog_service import GenerationCatalogService
            self.__dict__["_generation_catalog_service"] = GenerationCatalogService(
                config_dir="./config"
            )
        return self.__dict__["_generation_catalog_service"]

    @property
    def task_query_service(self) -> TaskQueryService:
        if "_task_query_service" not in self.__dict__:
            from backend.services.task_query_service import TaskQueryService
            self.__dict__["_task_query_service"] = TaskQueryService(
                self.task_repository, self.execution_coordinator, self.json_cache
            )
        return self.__dict__["_task_query_service"]

    @property
    def task_command_service(self) -> TaskCommandService:
        if "_task_command_service" not in self.__dict__:
            from backend.services.task_command_service import TaskCommandService
            self.__dict__["_task_command_service"] = TaskCommandService(
                self.task_repository, self.execution_coordinator
            )
        return self.__dict__["_task_command_service"]

    @property
    def task_application_service(self) -> TaskApplicationServiceImpl:
        if "_task_application_service" not in self.__dict__:
            from backend.services.task_application_service import TaskApplicationServiceImpl
            self.__dict__["_task_application_service"] = TaskApplicationServiceImpl(
                self.task_query_service, self.task_command_service
            )
        return self.__dict__["_task_application_service"]

    @property
    def admin_model_config_service(self) -> AdminModelConfigService:
        if "_admin_model_config_service" not in self.__dict__:
            from backend.services.model_config_service import AdminModelConfigService
            self.__dict__["_admin_model_config_service"] = AdminModelConfigService(
                self.model_resolver
            )
        return self.__dict__["_admin_model_config_service"]

    @property
    def user_model_config_service(self) -> UserModelConfigService:
        if "_user_model_config_service" not in self.__dict__:
            from backend.services.model_config_service import UserModelConfigService
            self.__dict__["_user_model_config_service"] = UserModelConfigService(
                self.model_resolver, self.credential_repository
            )
        return self.__dict__["_user_model_config_service"]

    @property
    def media_artifact_service(self):
        """Local media artifact service for file operations (thumbnails, concat, etc.)."""
        if "_media_artifact_service" not in self.__dict__:
            from backend.services.media_service import JiandouStorageProperties, LocalMediaArtifactService
            from backend.services.object_storage import create_remote_object_storage
            storage_props = JiandouStorageProperties(
                root_dir=self.config.storage_root,
                public_base_url=getattr(self.config, "storage_public_base_url", "") or "/storage",
                externally_accessible_base_url=getattr(self.config, "externally_accessible_base_url", "") or "",
                storage_key_prefix=getattr(self.config, "aliyun_oss_key_prefix", "") or "",
            )
            self.__dict__["_media_artifact_service"] = LocalMediaArtifactService(
                storage_properties=storage_props,
                remote_object_store=create_remote_object_storage(self.config),
            )
        return self.__dict__["_media_artifact_service"]

    @property
    def pipeline_handler(self) -> TaskWorkerPipelineHandler:
        if "_pipeline_handler" not in self.__dict__:
            from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
            from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
            from backend.services.task_worker_service import TaskWorkerPipelineHandler
            self.__dict__["_pipeline_handler"] = TaskWorkerPipelineHandler(
                task_repository=self.task_repository,
                task_queue_port=self.task_queue,
                execution_coordinator=self.execution_coordinator,
                generation_application_service=self.generation_application_service,
                runtime_support=TaskExecutionRuntimeSupport(
                    task_repository=self.task_repository,
                    model_resolver=self.model_resolver,
                    local_media_artifact_service=self.media_artifact_service,
                ),
                artifact_assembler=TaskExecutionArtifactAssembler(
                    local_media_artifact_service=self.media_artifact_service,
                ),
                video_stage_service=self.task_video_stage_service,
            )
        return self.__dict__["_pipeline_handler"]

    @property
    def task_video_stage_service(self):
        if "_task_video_stage_service" not in self.__dict__:
            from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
            from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
            from backend.services.task_video_stage_service import TaskVideoStageService
            from backend.services.task_worker_status_stage_service import TaskWorkerStatusStageService

            self.__dict__["_task_video_stage_service"] = TaskVideoStageService(
                task_repository=self.task_repository,
                execution_coordinator=self.execution_coordinator,
                generation_application_service=self.generation_application_service,
                runtime_support=TaskExecutionRuntimeSupport(
                    task_repository=self.task_repository,
                    model_resolver=self.model_resolver,
                    local_media_artifact_service=self.media_artifact_service,
                ),
                artifact_assembler=TaskExecutionArtifactAssembler(
                    local_media_artifact_service=self.media_artifact_service,
                ),
                status_stage_service=TaskWorkerStatusStageService(
                    task_repository=self.task_repository,
                    execution_coordinator=self.execution_coordinator,
                ),
                local_media_artifact_service=self.media_artifact_service,
            )
        return self.__dict__["_task_video_stage_service"]

    @property
    def worker_runner(self) -> TaskWorkerRunner:
        if "_worker_runner" not in self.__dict__:
            from backend.services.task_worker_runner import TaskWorkerOpsConfig, TaskWorkerRunner
            self.__dict__["_worker_runner"] = TaskWorkerRunner(
                task_queue_port=self.task_queue,
                execution_coordinator=self.execution_coordinator,
                pipeline_handler=self.pipeline_handler,
                execution_mode=self.config.execution_mode,
                ops_config=TaskWorkerOpsConfig(
                    worker_concurrency=self.config.worker_concurrency,
                    worker_poll_initial_delay_ms=500,
                    worker_poll_interval_ms=self.config.worker_poll_interval_ms,
                    worker_maintenance_initial_delay_ms=1_000,
                    worker_maintenance_interval_ms=10_000,
                    worker_stale_timeout_seconds=self.config.worker_stale_timeout_seconds,
                ),
            )
        return self.__dict__["_worker_runner"]

    @property
    def auto_pilot_runner(self) -> AutoPilotWorkerRunner:
        if "_auto_pilot_runner" not in self.__dict__:
            from backend.services.auto_pilot_worker_runner import AutoPilotOpsConfig, AutoPilotWorkerRunner
            self.__dict__["_auto_pilot_runner"] = AutoPilotWorkerRunner(
                workflow_service=self._lazy_workflow_service(),
                ops_config=AutoPilotOpsConfig(
                    poll_interval_ms=1_000,
                    maintenance_interval_ms=30_000,
                ),
            )
        return self.__dict__["_auto_pilot_runner"]

    def _lazy_workflow_service(self):
        """Create a WorkflowService for the auto-pilot runner.

        The auto-pilot runner needs the generation service to drive workflow
        stages (storyboard, keyframe, video generation) and the media service
        for final video concatenation.
        """
        from backend.services.workflow_service import WorkflowService
        task_repo = self.task_repository
        return WorkflowService(
            task_repo.session,
            generation_service=self.generation_application_service,
            media_service=self.media_artifact_service,
        )

    # -- App binding -------------------------------------------------------

    def bind_app_state(self, app: FastAPI) -> None:
        """Wire container services onto ``app.state`` for router access."""
        from backend.services.structured_application_logger import StructuredApplicationLogger

        app.state.container = self
        app.state.task_application_service = self.task_application_service
        app.state.admin_model_config_service = self.admin_model_config_service
        app.state.user_model_config_service = self.user_model_config_service
        app.state.model_resolver = self.model_resolver
        app.state.structured_logger = StructuredApplicationLogger
        app.state.generation_application_service = self.generation_application_service
        app.state.generation_catalog_service = self.generation_catalog_service
        app.state.media_artifact_service = self.media_artifact_service
        app.state.task_video_stage_service = self.task_video_stage_service
        app.state.task_worker_runner = self.worker_runner
        app.state.auto_pilot_runner = self.auto_pilot_runner
        app.state.task_repository = self.task_repository
        app.state.credential_repository = self.credential_repository
        app.state.execution_coordinator = self.execution_coordinator
        app.state.task_queue = self.task_queue
        app.state.redis_client = self.redis_client
        app.state.json_cache = self.json_cache

    # -- Model providers (lazy singletons) ----------------------------------

    @property
    def text_model_provider(self) -> OpenAiCompatibleTextModelProvider:
        if "_text_model_provider" not in self.__dict__:
            from backend.services.model_invocation import OpenAiCompatibleTextModelProvider
            self.__dict__["_text_model_provider"] = OpenAiCompatibleTextModelProvider()
        return self.__dict__["_text_model_provider"]

    @property
    def prompt_template_resolver(self) -> PromptTemplateResolver:
        if "_prompt_template_resolver" not in self.__dict__:
            from backend.services.model_invocation import PromptTemplateResolver
            self.__dict__["_prompt_template_resolver"] = PromptTemplateResolver()
        return self.__dict__["_prompt_template_resolver"]

    @property
    def image_model_providers(self) -> list:
        if "_image_model_providers" not in self.__dict__:
            from backend.services.model_invocation import (
                ImageProviderTransport,
                OpenAiImageModelProvider,
            )
            transport = ImageProviderTransport()
            self.__dict__["_image_model_providers"] = [
                OpenAiImageModelProvider(transport=transport),
            ]
        return self.__dict__["_image_model_providers"]

    @property
    def image_model_provider(self):
        providers = self.image_model_providers
        return providers[0] if providers else None

    @property
    def video_model_provider(self):
        if "_video_model_provider" not in self.__dict__:
            from backend.services.model_invocation import (
                AgnesVideoModelProvider,
                CompositeVideoModelProvider,
                SeedanceVideoModelProvider,
                VideoProviderTransport,
            )
            transport = VideoProviderTransport()
            self.__dict__["_video_model_provider"] = CompositeVideoModelProvider(
                providers=[
                    SeedanceVideoModelProvider(transport=transport),
                    AgnesVideoModelProvider(transport=transport),
                ]
            )
        return self.__dict__["_video_model_provider"]
