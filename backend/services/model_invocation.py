"""Model invocation layer - AI provider transport and strategy."""

from __future__ import annotations

from backend.services.model_invocation_config import (
    GenerationConfigPathLocator,
    GenerationConfigurationException,
    LocatedConfig,
    PromptTemplateResolver,
)

# =============================================================================
# DTOs for image model invocation
# =============================================================================
from backend.services.model_invocation_image import (
    DownloadedBinary,
    ImageGenerationRequest,
    ImageModelProvider,
    ImageProviderTransport,
    MultipartFilePart,
    OpenAiImageModelProvider,
    RemoteImageGenerationResult,
)
from backend.services.model_invocation_text import (
    ChatCompletionsInvocationStrategy,
    OpenAiCompatibleTextModelProvider,
    PreparedTextModelRequest,
    ResponsesApiInvocationStrategy,
    TextModelInvocation,
    TextModelInvocationStrategy,
    TextModelProvider,
    TextModelResponse,
    TextModelTransportPolicy,
    TextProviderTransport,
)

# =============================================================================
# DTOs for video model invocation
# =============================================================================
from backend.services.model_invocation_video import (
    AgnesVideoModelProvider,
    CompositeVideoModelProvider,
    RemoteTaskQueryResult,
    RemoteVideoTaskSubmission,
    SeedanceVideoModelProvider,
    VideoGenerationRequest,
    VideoModelProvider,
    VideoProviderTransport,
)
