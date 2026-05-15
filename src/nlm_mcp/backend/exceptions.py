"""Backend exception mapping for safe MCP error responses."""

from __future__ import annotations

from typing import Any


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


def _looks_like_notebooklm_auth_failure(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "authentication expired or invalid" in message
        or "run 'notebooklm login'" in message
        or "run `notebooklm login`" in message
    )


def _looks_like_account_routing_failure(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "account-routing mismatch" in message
        or "multiple google accounts signed in" in message
        or "request defaults to account index 0" in message
    )


def _map_client_error(exc: Exception, *, account_routing_failure: bool) -> BackendError:
    if account_routing_failure:
        return BackendAuthError(
            (
                "Authentication failed. Recreate the NotebookLM auth storage with the intended "
                "Google account; mixed-account cookies can route NotebookLM writes to the wrong "
                "account."
            ),
            error_code=-32002,
            data=_base_data(exc),
        )
    return BackendValidationError(
        "NotebookLM client error.",
        error_code=-32602,
        data=_base_data(exc),
    )


def map_backend_exception(exc: Exception) -> BackendError:
    """Map notebooklm-py and transport exceptions to sanitized backend errors."""
    if isinstance(exc, BackendError):
        return exc

    from notebooklm import (  # noqa: PLC0415
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

    is_auth_failure_by_message = _looks_like_notebooklm_auth_failure(exc)
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
    elif isinstance(exc, (AuthError, ConfigurationError, FileNotFoundError)) or (
        is_auth_failure_by_message
    ):
        auth_message = (
            "Authentication failed. Re-authenticate the configured NotebookLM storage."
            if is_auth_failure_by_message
            else "Authentication failed."
        )
        mapped = BackendAuthError(auth_message, error_code=-32002, data=_base_data(exc))
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
        is_account_routing_failure = _looks_like_account_routing_failure(exc)
        mapped = _map_client_error(exc, account_routing_failure=is_account_routing_failure)
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
