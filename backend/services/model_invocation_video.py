"""Compatibility exports for video provider contracts and implementations."""

from backend.services.model_invocation_video_agnes import AgnesVideoModelProvider
from backend.services.model_invocation_video_composite import CompositeVideoModelProvider
from backend.services.model_invocation_video_contracts import (
    RemoteTaskQueryResult,
    RemoteVideoTaskSubmission,
    VideoGenerationRequest,
    VideoModelProvider,
)
from backend.services.model_invocation_video_seedance import SeedanceVideoModelProvider
from backend.services.model_invocation_video_transport import VideoProviderTransport

__all__ = [
    "AgnesVideoModelProvider",
    "CompositeVideoModelProvider",
    "RemoteTaskQueryResult",
    "RemoteVideoTaskSubmission",
    "SeedanceVideoModelProvider",
    "VideoGenerationRequest",
    "VideoModelProvider",
    "VideoProviderTransport",
]
