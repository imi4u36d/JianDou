from __future__ import annotations

from pathlib import Path

from backend.services.credit_ledger import CreditLedger
from backend.services.credit_ledger import InsufficientCreditsError as ExtractedInsufficientCreditsError
from backend.services.credit_rule_catalog import CreditRuleCatalog
from backend.services.credit_rule_catalog import normalize_feature_code as extracted_normalize_feature_code
from backend.services.credit_service import CreditService, InsufficientCreditsError, normalize_feature_code
from backend.services.generation_image_run_service import GenerationImageRunService
from backend.services.generation_run_factory import (
    GenerationNotImplementedException as ExtractedGenerationNotImplementedException,
)
from backend.services.generation_run_factory import GenerationProviderException as ExtractedGenerationProviderException
from backend.services.generation_run_factory import GenerationRunFactory as ExtractedGenerationRunFactory
from backend.services.generation_run_factory import (
    GenerationRunNotFoundException as ExtractedGenerationRunNotFoundException,
)
from backend.services.generation_run_factory import (
    UnsupportedGenerationKindException as ExtractedUnsupportedGenerationKindException,
)
from backend.services.generation_run_support import GenerationRunSupport as ExtractedGenerationRunSupport
from backend.services.generation_script_run_service import GenerationScriptRunService
from backend.services.generation_service import (
    GenerationNotImplementedException,
    GenerationProviderException,
    GenerationRunFactory,
    GenerationRunNotFoundException,
    GenerationRunSupport,
    UnsupportedGenerationKindException,
)
from backend.services.generation_text_run_service import GenerationTextRunService
from backend.services.generation_video_run_service import GenerationVideoRunService
from backend.services.model_config_admin import AdminModelConfigService as ExtractedAdminModelConfigService
from backend.services.model_config_contracts import (
    AdminModelConfigKeyUpdateRequest as ExtractedAdminModelConfigKeyUpdateRequest,
)
from backend.services.model_config_contracts import (
    AdminModelConfigResponse as ExtractedAdminModelConfigResponse,
)
from backend.services.model_config_contracts import (
    AdminModelConfigValidationResponse as ExtractedAdminModelConfigValidationResponse,
)
from backend.services.model_config_contracts import ApiKeyUpdateBatch as ExtractedApiKeyUpdateBatch
from backend.services.model_config_credentials import (
    RuntimeProviderConfig as ExtractedRuntimeProviderConfig,
)
from backend.services.model_config_credentials import (
    SqlAlchemyUserModelCredentialRepository as ExtractedCredentialRepository,
)
from backend.services.model_config_path_locator import (
    GenerationConfigPathLocator as LocatedGenerationConfigPathLocator,
)
from backend.services.model_config_profiles import ModelRuntimeProfile as ExtractedModelRuntimeProfile
from backend.services.model_config_response_support import ModelConfigResponseSupport
from backend.services.model_config_runtime import (
    ModelRuntimePropertiesResolver as ExtractedModelRuntimePropertiesResolver,
)
from backend.services.model_config_service import (
    AdminModelConfigKeyUpdateRequest,
    AdminModelConfigResponse,
    AdminModelConfigService,
    AdminModelConfigValidationResponse,
    ApiKeyUpdateBatch,
    ModelRuntimeProfile,
    ModelRuntimePropertiesResolver,
    RuntimeProviderConfig,
    SqlAlchemyUserModelCredentialRepository,
    UserModelConfigService,
)
from backend.services.model_config_user import UserModelConfigService as ExtractedUserModelConfigService
from backend.services.model_invocation import (
    AgnesVideoModelProvider,
    ChatCompletionsInvocationStrategy,
    CompositeVideoModelProvider,
    GenerationConfigPathLocator,
    ImageGenerationRequest,
    ImageProviderTransport,
    OpenAiCompatibleTextModelProvider,
    OpenAiImageModelProvider,
    PromptTemplateResolver,
    SeedanceVideoModelProvider,
    TextModelInvocation,
    TextProviderTransport,
    VideoGenerationRequest,
    VideoProviderTransport,
)
from backend.services.model_invocation_config import (
    GenerationConfigPathLocator as ExtractedGenerationConfigPathLocator,
)
from backend.services.model_invocation_config import (
    PromptTemplateResolver as ExtractedPromptTemplateResolver,
)
from backend.services.model_invocation_image import ImageGenerationRequest as ExtractedImageGenerationRequest
from backend.services.model_invocation_image import ImageProviderTransport as ExtractedImageProviderTransport
from backend.services.model_invocation_image import OpenAiImageModelProvider as ExtractedImageModelProvider
from backend.services.model_invocation_image_contracts import (
    ImageGenerationRequest as ImageGenerationRequestContract,
)
from backend.services.model_invocation_image_transport import ImageProviderTransport as ImageProviderTransportClass
from backend.services.model_invocation_text import (
    OpenAiCompatibleTextModelProvider as ExtractedTextModelProvider,
)
from backend.services.model_invocation_text import TextModelInvocation as ExtractedTextModelInvocation
from backend.services.model_invocation_text import TextProviderTransport as ExtractedTextProviderTransport
from backend.services.model_invocation_text_contracts import TextModelInvocation as TextModelInvocationContract
from backend.services.model_invocation_text_strategies import (
    ChatCompletionsInvocationStrategy as ChatCompletionsStrategy,
)
from backend.services.model_invocation_text_transport import (
    TextProviderTransport as TextProviderTransportClass,
)
from backend.services.model_invocation_video import AgnesVideoModelProvider as ExtractedAgnesVideoModelProvider
from backend.services.model_invocation_video import CompositeVideoModelProvider as ExtractedCompositeVideoModelProvider
from backend.services.model_invocation_video import SeedanceVideoModelProvider as ExtractedSeedanceVideoModelProvider
from backend.services.model_invocation_video import VideoGenerationRequest as ExtractedVideoGenerationRequest
from backend.services.model_invocation_video import VideoProviderTransport as ExtractedVideoProviderTransport
from backend.services.model_invocation_video_contracts import (
    VideoGenerationRequest as VideoGenerationRequestContract,
)
from backend.services.model_invocation_video_transport import VideoProviderTransport as VideoProviderTransportClass
from backend.services.workflow_keyframe_generation_service import WorkflowKeyframeGenerationService
from backend.services.workflow_keyframe_version_store import WorkflowKeyframeVersionStore
from backend.services.workflow_lifecycle_service import WorkflowLifecycleService
from backend.services.workflow_query_service import WorkflowQueryService
from backend.services.workflow_service import WorkflowService
from backend.services.workflow_service_composition import workflow_storyboard_plan
from backend.services.workflow_stage_mutation_service import WorkflowStageMutationService
from backend.services.workflow_storyboard_generation_service import WorkflowStoryboardGenerationService
from backend.services.workflow_video_generation_service import WorkflowVideoGenerationService


def test_generation_service_reexports_run_support() -> None:
    assert GenerationRunSupport is ExtractedGenerationRunSupport


def test_credit_service_reexports_contracts_and_composes_collaborators() -> None:
    service = CreditService(None)

    assert InsufficientCreditsError is ExtractedInsufficientCreditsError
    assert normalize_feature_code is extracted_normalize_feature_code
    assert isinstance(service._ledger, CreditLedger)
    assert isinstance(service._rules, CreditRuleCatalog)


def test_credit_rule_normalization_remains_stable() -> None:
    assert normalize_feature_code(" image_generation ") == "IMAGE_GENERATION"
    assert normalize_feature_code("") == ""


def test_generation_service_reexports_run_factory_contracts() -> None:
    assert GenerationRunFactory is ExtractedGenerationRunFactory
    assert GenerationNotImplementedException is ExtractedGenerationNotImplementedException
    assert GenerationProviderException is ExtractedGenerationProviderException
    assert GenerationRunNotFoundException is ExtractedGenerationRunNotFoundException
    assert UnsupportedGenerationKindException is ExtractedUnsupportedGenerationKindException


def test_generation_run_factory_delegates_kind_orchestration() -> None:
    factory = GenerationRunFactory(
        config_resolver=object(),
        text_provider=object(),
        prompt_resolver=object(),
        image_providers=[object()],
        video_provider=object(),
    )

    text_runs = factory._text_run_service()
    assert isinstance(text_runs, GenerationTextRunService)
    assert isinstance(text_runs._script_runs, GenerationScriptRunService)
    assert isinstance(factory._image_run_service(), GenerationImageRunService)
    assert isinstance(factory._video_run_service(), GenerationVideoRunService)


def test_model_invocation_reexports_config_services() -> None:
    assert GenerationConfigPathLocator is ExtractedGenerationConfigPathLocator
    assert GenerationConfigPathLocator is LocatedGenerationConfigPathLocator
    assert PromptTemplateResolver is ExtractedPromptTemplateResolver


def test_model_invocation_reexports_text_invocation_services() -> None:
    assert OpenAiCompatibleTextModelProvider is ExtractedTextModelProvider
    assert TextModelInvocation is ExtractedTextModelInvocation
    assert TextProviderTransport is ExtractedTextProviderTransport
    assert ExtractedTextProviderTransport is TextProviderTransportClass
    assert ExtractedTextModelInvocation is TextModelInvocationContract
    assert ChatCompletionsInvocationStrategy is ChatCompletionsStrategy


def test_model_invocation_reexports_image_invocation_services() -> None:
    assert ImageGenerationRequest is ExtractedImageGenerationRequest
    assert ImageProviderTransport is ExtractedImageProviderTransport
    assert OpenAiImageModelProvider is ExtractedImageModelProvider
    assert ExtractedImageGenerationRequest is ImageGenerationRequestContract
    assert ExtractedImageProviderTransport is ImageProviderTransportClass


def test_model_invocation_reexports_video_invocation_services() -> None:
    assert AgnesVideoModelProvider is ExtractedAgnesVideoModelProvider
    assert CompositeVideoModelProvider is ExtractedCompositeVideoModelProvider
    assert SeedanceVideoModelProvider is ExtractedSeedanceVideoModelProvider
    assert VideoGenerationRequest is ExtractedVideoGenerationRequest
    assert VideoProviderTransport is ExtractedVideoProviderTransport
    assert ExtractedVideoGenerationRequest is VideoGenerationRequestContract
    assert ExtractedVideoProviderTransport is VideoProviderTransportClass


def test_model_config_service_reexports_runtime_profiles() -> None:
    assert ModelRuntimeProfile is ExtractedModelRuntimeProfile


def test_model_config_service_reexports_runtime_resolver() -> None:
    assert ModelRuntimePropertiesResolver is ExtractedModelRuntimePropertiesResolver


def test_model_config_service_reexports_admin_and_user_services() -> None:
    assert AdminModelConfigService is ExtractedAdminModelConfigService
    assert UserModelConfigService is ExtractedUserModelConfigService


def test_model_config_service_reexports_credential_contracts() -> None:
    assert RuntimeProviderConfig is ExtractedRuntimeProviderConfig
    assert SqlAlchemyUserModelCredentialRepository is ExtractedCredentialRepository


def test_model_config_service_reexports_response_contracts() -> None:
    assert AdminModelConfigKeyUpdateRequest is ExtractedAdminModelConfigKeyUpdateRequest
    assert AdminModelConfigResponse is ExtractedAdminModelConfigResponse
    assert AdminModelConfigValidationResponse is ExtractedAdminModelConfigValidationResponse
    assert ApiKeyUpdateBatch is ExtractedApiKeyUpdateBatch


def test_model_config_services_share_response_assembly() -> None:
    from backend.services.model_config_service import AdminModelConfigService, UserModelConfigService

    assert issubclass(AdminModelConfigService, ModelConfigResponseSupport)
    assert issubclass(UserModelConfigService, ModelConfigResponseSupport)


def test_workflow_service_composes_keyframe_generation_collaborator() -> None:
    service = WorkflowService(None)

    assert isinstance(service._keyframe_generation_service, WorkflowKeyframeGenerationService)
    assert isinstance(service._keyframe_generation_service._versions, WorkflowKeyframeVersionStore)


def test_workflow_service_composes_video_generation_collaborator() -> None:
    service = WorkflowService(None)

    assert isinstance(service._video_generation_service, WorkflowVideoGenerationService)


def test_workflow_service_composes_storyboard_generation_collaborator() -> None:
    service = WorkflowService(None)

    assert isinstance(service._storyboard_generation_service, WorkflowStoryboardGenerationService)


def test_workflow_service_composes_stage_mutation_collaborator() -> None:
    service = WorkflowService(None)

    assert isinstance(service._stage_mutation_service, WorkflowStageMutationService)


def test_workflow_service_composes_lifecycle_collaborator() -> None:
    service = WorkflowService(None)

    assert isinstance(service._lifecycle_service, WorkflowLifecycleService)


def test_workflow_service_composes_query_collaborator() -> None:
    service = WorkflowService(None)

    assert isinstance(service._query_service, WorkflowQueryService)


def test_workflow_service_composition_shares_persistence_dependencies() -> None:
    service = WorkflowService(None)

    assert service._video_generation_service._row_factory is service._row_factory
    assert service._keyframe_generation_service._persistence._row_factory is service._row_factory
    assert workflow_storyboard_plan(None) == ([], [])


def test_config_locator_collects_split_yaml_and_excludes_secrets(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    provider_dir = config_dir / "model" / "providers"
    provider_dir.mkdir(parents=True)
    (config_dir / "model" / "catalog.yml").write_text("model: {}", encoding="utf-8")
    (provider_dir / "openai.yaml").write_text("model: {}", encoding="utf-8")
    (provider_dir / "providers.secrets.yml").write_text("model: {}", encoding="utf-8")

    files = GenerationConfigPathLocator().collect_config_files(config_dir)

    assert [path.relative_to(config_dir).as_posix() for path in files] == [
        "model/catalog.yml",
        "model/providers/openai.yaml",
    ]


def test_prompt_resolver_uses_the_extracted_path_locator_contract(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "storyboard.yml").write_text(
        "system_prompts:\n  planning: Plan the storyboard.\n",
        encoding="utf-8",
    )
    locator = GenerationConfigPathLocator()
    locator.resolve_path = lambda _configured_path: prompt_dir  # type: ignore[method-assign]
    resolver = PromptTemplateResolver(locator, fail_fast_on_prompt_error=True)

    assert resolver.system_prompt("storyboard", "planning") == "Plan the storyboard."
