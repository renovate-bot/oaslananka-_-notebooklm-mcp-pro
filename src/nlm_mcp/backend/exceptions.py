"""Backend exception mapping for safe MCP error responses."""

from __future__ import annotations

from typing import Any

from notebooklm import (
    ArtifactNotFoundError,
    AuthError,
    ClientError,
    ConfigurationError,
    NetworkError,
    NotebookLMError,
    NotebookNotFoundError,
    RateLimitError,
    RPCTimeoutError,
    ServerError,
    SourceNotFoundError,
    ValidationError,
)


class BackendError(Exception):
    """Base error returned by the NotebookLM backend layer."""

    def __init__(
        self,
        safe_message: str,
        *,
        error_code: int = -32000,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message
        self.error_code = error_code
        self.data = data or {}

    def to_mcp_error(self) -> dict[str, Any]:
        """Return a JSON-RPC compatible MCP error object."""
        return {
            "code": self.error_code,
            "message": self.safe_message,
            "data": self.data,
        }


class BackendRateLimitError(BackendError):
    """NotebookLM rejected the request due to rate limiting."""


class BackendAuthError(BackendError):
    """NotebookLM authentication is missing, expired, or invalid."""


class BackendTimeoutError(BackendError):
    """NotebookLM did not complete the request before the timeout."""


class BackendValidationError(BackendError):
    """The caller supplied invalid backend input."""


class BackendNotFoundError(BackendError):
    """The requested NotebookLM entity was not found."""


class BackendUnavailableError(BackendError):
    """NotebookLM or the network was unavailable."""


class BackendUnexpectedError(BackendError):
    """An unclassified backend error occurred."""


def _base_data(exc: Exception) -> dict[str, Any]:
    return {"backend_error_class": exc.__class__.__name__}


def map_backend_exception(exc: Exception) -> BackendError:
    """Map notebooklm-py and transport exceptions to sanitized backend errors."""
    if isinstance(exc, BackendError):
        return exc

    mapped: BackendError
    if isinstance(exc, RateLimitError):
        data = _base_data(exc)
        if exc.retry_after is not None:
            data["retry_after_seconds"] = exc.retry_after
        mapped = BackendRateLimitError(
            "NotebookLM rate limit exceeded.",
            error_code=-32001,
            data=data,
        )
    elif isinstance(exc, (AuthError, ConfigurationError, FileNotFoundError)):
        mapped = BackendAuthError("Authentication failed.", error_code=-32002, data=_base_data(exc))
    elif isinstance(exc, (RPCTimeoutError, TimeoutError)):
        data = _base_data(exc)
        timeout_seconds = getattr(exc, "timeout_seconds", None)
        if timeout_seconds is not None:
            data["timeout_seconds"] = timeout_seconds
        mapped = BackendTimeoutError(
            "NotebookLM backend request timed out.",
            error_code=-32003,
            data=data,
        )
    elif isinstance(exc, ValidationError):
        mapped = BackendValidationError(
            "Invalid backend request.",
            error_code=-32602,
            data=_base_data(exc),
        )
    elif isinstance(exc, (NotebookNotFoundError, SourceNotFoundError, ArtifactNotFoundError)):
        mapped = BackendNotFoundError(
            "Requested NotebookLM resource was not found.",
            error_code=-32004,
            data=_base_data(exc),
        )
    elif isinstance(exc, (NetworkError, ServerError)):
        mapped = BackendUnavailableError(
            "NotebookLM backend is temporarily unavailable.",
            error_code=-32005,
            data=_base_data(exc),
        )
    elif isinstance(exc, ClientError):
        mapped = BackendValidationError(
            "NotebookLM client error.",
            error_code=-32602,
            data=_base_data(exc),
        )
    elif isinstance(exc, NotebookLMError):
        mapped = BackendUnexpectedError(
            "NotebookLM backend request failed.",
            error_code=-32000,
            data=_base_data(exc),
        )
    else:
        mapped = BackendUnexpectedError(
            "NotebookLM backend request failed.",
            error_code=-32000,
            data=_base_data(exc),
        )

    return mapped
