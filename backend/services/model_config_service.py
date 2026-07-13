"""Compatibility facade for model configuration services and contracts."""

from backend.services.model_config_admin import (
    AdminModelConfigSecretsService,
    AdminModelConfigService,
    LocalAdminModelConfigSecretsService,
)
from backend.services.model_config_contracts import (
    AdminModelConfigKeyUpdateRequest,
    AdminModelConfigResponse,
    AdminModelConfigValidationResponse,
    ApiKeyUpdateBatch,
)
from backend.services.model_config_credentials import (
    MybatisUserModelCredentialRepository,
    RuntimeModelCredentialProvider,
    RuntimeProviderConfig,
    SqlAlchemyUserModelCredentialRepository,
)
from backend.services.model_config_credentials import protect_user_api_key as _protect_user_api_key
from backend.services.model_config_credentials import unprotect_user_api_key as _unprotect_user_api_key
from backend.services.model_config_profiles import (
    MediaProviderCapabilities,
    MediaProviderConfig,
    MediaProviderProfile,
    ModelRuntimeProfile,
    ResolvedModel,
    TextProviderCapabilities,
    TextProviderConfig,
)
from backend.services.model_config_runtime import ModelRuntimePropertiesResolver
from backend.services.model_config_user import UserModelConfigService

__all__ = [
    "AdminModelConfigKeyUpdateRequest",
    "AdminModelConfigResponse",
    "AdminModelConfigSecretsService",
    "AdminModelConfigService",
    "AdminModelConfigValidationResponse",
    "ApiKeyUpdateBatch",
    "LocalAdminModelConfigSecretsService",
    "MediaProviderCapabilities",
    "MediaProviderConfig",
    "MediaProviderProfile",
    "ModelRuntimeProfile",
    "ModelRuntimePropertiesResolver",
    "MybatisUserModelCredentialRepository",
    "ResolvedModel",
    "RuntimeModelCredentialProvider",
    "RuntimeProviderConfig",
    "SqlAlchemyUserModelCredentialRepository",
    "TextProviderCapabilities",
    "TextProviderConfig",
    "UserModelConfigService",
]
