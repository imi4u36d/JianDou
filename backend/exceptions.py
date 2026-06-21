"""Centralized exception hierarchy for the JianDou backend.

All application-specific exceptions inherit from ``JianDouError``,
making it easy to catch and handle JianDou-specific errors uniformly.
"""
from __future__ import annotations


class JianDouError(Exception):
    """Base exception for all JianDou application errors."""

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


# -- Configuration errors ---------------------------------------------------

class ConfigurationError(JianDouError):
    """Raised when application configuration is invalid or missing."""

    pass


# -- Authentication / Authorization errors ----------------------------------

class AuthError(JianDouError):
    """Base for authentication and authorization errors."""

    pass


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""

    pass


class TokenExpiredError(AuthError):
    """Raised when a JWT token has expired."""

    pass


class InsufficientPermissionsError(AuthError):
    """Raised when the authenticated user lacks required permissions."""

    pass


# -- Resource errors --------------------------------------------------------

class NotFoundError(JianDouError):
    """Raised when a requested resource does not exist."""

    pass


class ConflictError(JianDouError):
    """Raised when a resource state conflicts with the requested operation."""

    pass


# -- Generation / Model errors ----------------------------------------------

class GenerationError(JianDouError):
    """Base for generation-related errors."""

    pass


class GenerationProviderError(GenerationError):
    """Raised when a provider (text/image/video API) returns an error.

    Corresponds to ``GenerationProviderException`` in the legacy module.
    """

    def __init__(
        self,
        message: str,
        *,
        provider_request: dict | None = None,
        provider_response: object = None,
        http_status: int = 0,
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code or "GENERATION_PROVIDER_ERROR")
        self.provider_request = provider_request or {}
        self.provider_response = provider_response
        self.http_status = http_status


class GenerationNotImplementedError(GenerationError):
    """Raised when a generation feature is not yet implemented."""

    pass


class GenerationRunNotFoundError(GenerationError):
    """Raised when a generation run ID is not found."""

    pass


class UnsupportedGenerationKindError(GenerationError):
    """Raised when an unsupported generation kind is requested."""

    def __init__(self, kind: str) -> None:
        super().__init__(f"不支持的生成类型: {kind}", code="UNSUPPORTED_GENERATION_KIND")


class GenerationConfigurationError(GenerationError):
    """Raised when generation config is missing or invalid.

    Corresponds to ``GenerationConfigurationException`` in the legacy module.
    """

    pass


# -- Task errors ------------------------------------------------------------

class TaskError(JianDouError):
    """Base for task-related errors."""

    pass


class TaskExecutionAbortedError(TaskError):
    """Raised when a task execution is aborted mid-flight.

    Corresponds to ``TaskExecutionAbortedException`` in the legacy module.
    """

    def __init__(self, message: str = "", *, task_status: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or "TASK_EXECUTION_ABORTED")
        self.task_status = task_status


# -- Validation errors ------------------------------------------------------

class ValidationError(JianDouError):
    """Raised when input validation fails."""

    pass


# -- Backward compatibility aliases -----------------------------------------

_COMPAT_MESSAGE = (
    "Use the new canonical name. "
    "Import from `backend.exceptions` directly."
)


def _compat(name: str, replacement: type[JianDouError]) -> type[JianDouError]:
    """Create a compatibility alias that warns on use."""
    import warnings

    class CompatAlias(replacement):
        def __init__(self, *args, **kwargs):
            warnings.warn(
                f"{name} is deprecated; {_COMPAT_MESSAGE}",
                DeprecationWarning,
                stacklevel=2,
            )
            super().__init__(*args, **kwargs)

    CompatAlias.__name__ = name
    CompatAlias.__qualname__ = name
    return CompatAlias


# These aliases exist so code importing the old names continues to work.
GenerationProviderException = _compat("GenerationProviderException", GenerationProviderError)
GenerationNotImplementedException = _compat("GenerationNotImplementedException", GenerationNotImplementedError)
GenerationRunNotFoundException = _compat("GenerationRunNotFoundException", GenerationRunNotFoundError)
UnsupportedGenerationKindException = _compat("UnsupportedGenerationKindException", UnsupportedGenerationKindError)
GenerationConfigurationException = _compat("GenerationConfigurationException", GenerationConfigurationError)
TaskExecutionAbortedException = _compat("TaskExecutionAbortedException", TaskExecutionAbortedError)
