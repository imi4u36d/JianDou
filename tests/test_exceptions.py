"""Tests for backend/exceptions.py — centralized exception hierarchy."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from backend.exceptions import (
    AuthError,
    ConfigurationError,
    ConflictError,
    GenerationConfigurationError,
    GenerationError,
    GenerationNotImplementedError,
    GenerationProviderError,
    GenerationRunNotFoundError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    JianDouError,
    NotFoundError,
    TaskError,
    TaskExecutionAbortedError,
    TokenExpiredError,
    UnsupportedGenerationKindError,
    ValidationError,
)


class TestJianDouError:
    def test_is_base_of_all_errors(self):
        assert issubclass(AuthError, JianDouError)
        assert issubclass(GenerationError, JianDouError)
        assert issubclass(TaskError, JianDouError)
        assert issubclass(ConfigurationError, JianDouError)
        assert issubclass(NotFoundError, JianDouError)
        assert issubclass(ConflictError, JianDouError)
        assert issubclass(ValidationError, JianDouError)

    def test_code_is_optional(self):
        err = JianDouError("something")
        assert err.code is None

    def test_code_can_be_set(self):
        err = JianDouError("oops", code="ERR_001")
        assert err.code == "ERR_001"


class TestAuthErrors:
    def test_invalid_credentials(self):
        err = InvalidCredentialsError("bad password")
        assert isinstance(err, AuthError)
        assert str(err) == "bad password"

    def test_token_expired(self):
        err = TokenExpiredError("token expired")
        assert isinstance(err, AuthError)

    def test_insufficient_permissions(self):
        err = InsufficientPermissionsError("not admin")
        assert isinstance(err, AuthError)


class TestGenerationErrors:
    def test_provider_error_carries_http_status(self):
        err = GenerationProviderError("timeout", http_status=504)
        assert isinstance(err, GenerationError)
        assert err.http_status == 504
        assert err.provider_request == {}
        assert err.provider_response is None
        assert err.code == "GENERATION_PROVIDER_ERROR"

    def test_not_implemented(self):
        err = GenerationNotImplementedError("not ready")
        assert isinstance(err, GenerationError)

    def test_run_not_found(self):
        err = GenerationRunNotFoundError("run_123")
        assert isinstance(err, GenerationError)

    def test_unsupported_kind_formats_message(self):
        err = UnsupportedGenerationKindError("audio")
        assert "不支持的生成类型: audio" in str(err)
        assert err.code == "UNSUPPORTED_GENERATION_KIND"

    def test_configuration_error(self):
        err = GenerationConfigurationError("missing config")
        assert isinstance(err, GenerationError)


class TestTaskErrors:
    def test_execution_aborted_carries_status(self):
        err = TaskExecutionAbortedError("aborted", task_status="CANCELLED")
        assert isinstance(err, TaskError)
        assert err.task_status == "CANCELLED"
        assert err.code == "TASK_EXECUTION_ABORTED"


class TestNotFoundError:
    def test_catches_all_not_founds(self):
        err = NotFoundError("task abc")
        assert isinstance(err, JianDouError)
        assert "task abc" in str(err)


class TestValidationError:
    def test_catches_input_errors(self):
        err = ValidationError("field x required")
        assert isinstance(err, JianDouError)
        assert "field x required" in str(err)


class TestCompatAliases:
    """Verify backward-compatibility aliases work."""

    def test_generation_provider_exception_alias(self):
        import warnings

        from backend.exceptions import GenerationProviderException
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            err = GenerationProviderException("test")
            assert isinstance(err, GenerationProviderError)
            # Should emit deprecation warning
            assert len(w) >= 1

    def test_generation_not_implemented_alias(self):
        from backend.exceptions import GenerationNotImplementedError
        err = GenerationNotImplementedError("nope")
        assert isinstance(err, GenerationNotImplementedError)

    def test_task_execution_aborted_alias(self):
        from backend.exceptions import TaskExecutionAbortedError
        err = TaskExecutionAbortedError("stop", task_status="ABORTED")
        assert isinstance(err, TaskExecutionAbortedError)
        assert err.task_status == "ABORTED"
