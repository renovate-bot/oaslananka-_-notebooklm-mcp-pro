from notebooklm import (
    AuthError,
    NotebookLMError,
    NotebookNotFoundError,
    RateLimitError,
    RPCTimeoutError,
    ValidationError,
)

from nlm_mcp.backend.exceptions import (
    BackendAuthError,
    BackendError,
    BackendNotFoundError,
    BackendRateLimitError,
    BackendTimeoutError,
    BackendUnexpectedError,
    BackendValidationError,
    map_backend_exception,
)

RATE_LIMIT_ERROR_CODE = -32001
AUTH_ERROR_CODE = -32002
TIMEOUT_ERROR_CODE = -32003
NOT_FOUND_ERROR_CODE = -32004
UNEXPECTED_ERROR_CODE = -32000
VALIDATION_ERROR_CODE = -32602
RETRY_AFTER_SECONDS = 7
TIMEOUT_SECONDS = 12.5


def test_rate_limit_error_mapping_includes_retry_after() -> None:
    mapped = map_backend_exception(RateLimitError("limited", retry_after=RETRY_AFTER_SECONDS))

    assert isinstance(mapped, BackendRateLimitError)
    assert mapped.error_code == RATE_LIMIT_ERROR_CODE
    assert mapped.data["retry_after_seconds"] == RETRY_AFTER_SECONDS


def test_auth_error_mapping_uses_auth_code() -> None:
    mapped = map_backend_exception(AuthError("expired"))

    assert isinstance(mapped, BackendAuthError)
    assert mapped.error_code == AUTH_ERROR_CODE
    assert mapped.safe_message == "Authentication failed."


def test_file_not_found_mapping_does_not_leak_path() -> None:
    mapped = map_backend_exception(FileNotFoundError("C:/Users/Admin/private/storage.json"))

    assert isinstance(mapped, BackendAuthError)
    assert mapped.error_code == AUTH_ERROR_CODE
    assert mapped.safe_message == "Authentication failed."
    assert "private" not in str(mapped.to_mcp_error())


def test_notebooklm_value_error_auth_redirect_maps_to_auth_error() -> None:
    mapped = map_backend_exception(
        ValueError(
            "Authentication expired or invalid. Redirected to: "
            "https://accounts.google.com/signin. Run 'notebooklm login' to re-authenticate."
        )
    )

    assert isinstance(mapped, BackendAuthError)
    assert mapped.error_code == AUTH_ERROR_CODE
    assert (
        mapped.safe_message
        == "Authentication failed. Re-authenticate the configured NotebookLM storage."
    )
    assert "accounts.google.com" not in str(mapped.to_mcp_error())


def test_timeout_error_mapping_uses_timeout_code() -> None:
    mapped = map_backend_exception(RPCTimeoutError("slow", timeout_seconds=TIMEOUT_SECONDS))

    assert isinstance(mapped, BackendTimeoutError)
    assert mapped.error_code == TIMEOUT_ERROR_CODE
    assert mapped.data["timeout_seconds"] == TIMEOUT_SECONDS


def test_validation_error_mapping_uses_json_rpc_invalid_params_code() -> None:
    mapped = map_backend_exception(ValidationError("bad input"))

    assert isinstance(mapped, BackendValidationError)
    assert mapped.error_code == VALIDATION_ERROR_CODE


def test_not_found_error_mapping_uses_safe_not_found_code() -> None:
    mapped = map_backend_exception(NotebookNotFoundError("nb-1"))

    assert isinstance(mapped, BackendNotFoundError)
    assert mapped.error_code == NOT_FOUND_ERROR_CODE
    assert mapped.data["backend_error_class"] == "NotebookNotFoundError"


def test_existing_backend_error_is_preserved() -> None:
    error = BackendError("already mapped", error_code=-32099)

    assert map_backend_exception(error) is error


def test_unclassified_notebooklm_error_is_sanitized() -> None:
    mapped = map_backend_exception(NotebookLMError("raw upstream details"))

    assert type(mapped) is BackendUnexpectedError
    assert mapped.error_code == UNEXPECTED_ERROR_CODE
    assert mapped.safe_message == "NotebookLM backend request failed."
    assert mapped.data["backend_error_class"] == "NotebookLMError"


def test_builtin_timeout_error_is_mapped() -> None:
    mapped = map_backend_exception(TimeoutError("elapsed"))

    assert isinstance(mapped, BackendTimeoutError)
    assert mapped.error_code == TIMEOUT_ERROR_CODE
