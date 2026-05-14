"""Tests for shared tool execution helpers."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ResourceError, ToolError
from pydantic import BaseModel

from nlm_mcp.backend.exceptions import BackendAuthError, BackendUnexpectedError
from nlm_mcp.tools.common import run_resource, run_tool


class _ValidationPayload(BaseModel):
    count: int


async def _raise_backend_auth_error() -> None:
    raise BackendAuthError(
        "Authentication failed.",
        error_code=-32002,
        data={"redirect": "https://accounts.google.com/private"},
    )


async def _raise_unexpected_error() -> None:
    raise RuntimeError("private upstream payload")


async def _raise_pydantic_validation_error() -> None:
    _ValidationPayload.model_validate({"count": "not-an-int"})


@pytest.mark.asyncio
async def test_run_tool_suppresses_backend_exception_context() -> None:
    """Backend details must not be chained into client-visible tool errors."""
    with pytest.raises(ToolError) as exc_info:
        await run_tool("notebook.list", {}, _raise_backend_auth_error)

    assert str(exc_info.value) == "Authentication failed."
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_run_tool_suppresses_pydantic_validation_exception_context() -> None:
    """Validation errors should keep their user-facing message without chaining."""
    with pytest.raises(ToolError) as exc_info:
        await run_tool("notebook.list", {}, _raise_pydantic_validation_error)

    message = str(exc_info.value)
    assert "count" in message
    assert "Input should be a valid integer" in message
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_run_tool_suppresses_unexpected_exception_context() -> None:
    """Unexpected exceptions should return a generic message without chaining."""
    with pytest.raises(ToolError) as exc_info:
        await run_tool("notebook.list", {}, _raise_unexpected_error)

    assert str(exc_info.value) == "NotebookLM tool execution failed."
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_run_resource_suppresses_generic_exception_context() -> None:
    """Unexpected resource exceptions should return a generic message without chaining."""
    with pytest.raises(ResourceError) as exc_info:
        await run_resource("notebooklm://notebooks", _raise_unexpected_error)

    assert str(exc_info.value) == "NotebookLM resource read failed."
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_run_resource_suppresses_backend_exception_context() -> None:
    """Resource errors should keep backend internals out of formatted tracebacks."""
    with pytest.raises(ResourceError) as exc_info:
        await run_resource("notebooklm://notebooks", _raise_backend_auth_error)

    assert str(exc_info.value) == "Authentication failed."
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_run_resource_suppresses_unexpected_exception_context() -> None:
    """Unexpected resource errors should not expose their source exception."""

    async def fail() -> None:
        raise BackendUnexpectedError("safe message")

    with pytest.raises(ResourceError) as exc_info:
        await run_resource("notebooklm://notebooks", fail)

    assert str(exc_info.value) == "safe message"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
