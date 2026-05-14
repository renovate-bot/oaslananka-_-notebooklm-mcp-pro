"""Shared helpers for NotebookLM tool registration."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, TypeVar

import structlog
from fastmcp.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from nlm_mcp.backend.exceptions import BackendError, BackendValidationError

T = TypeVar("T")
logger = structlog.get_logger(__name__)


def tool_annotations(
    *,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> ToolAnnotations:
    """Build MCP tool annotations with explicit safety hints."""
    return ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=open_world,
    )


def tool_public_name(canonical_name: str) -> str:
    """Return the MCP-visible tool name accepted by stricter clients such as VS Code."""
    return canonical_name.replace(".", "_")


def to_plain(value: Any) -> Any:
    """Convert notebooklm-py return values into JSON-compatible structures."""
    plain: Any
    if isinstance(value, BaseModel):
        plain = value.model_dump(mode="json")
    elif is_dataclass(value) and not isinstance(value, type):
        plain = to_plain(asdict(value))
    elif isinstance(value, Enum):
        plain = value.name.lower()
    elif isinstance(value, dict):
        plain = {str(key): to_plain(item) for key, item in value.items()}
    elif isinstance(value, (list, tuple, set)):
        plain = [to_plain(item) for item in value]
    elif isinstance(value, (str, int, float, bool)) or value is None:
        plain = value
    elif hasattr(value, "model_dump"):
        plain = to_plain(value.model_dump(mode="json"))
    elif hasattr(value, "__dict__"):
        plain = {
            key: to_plain(item) for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        plain = str(value)
    return plain


def stable_id(value: Any, *fallback_keys: str) -> str:
    """Extract a stable id-like value from a dict/object response."""
    plain = to_plain(value)
    if isinstance(plain, dict):
        for key in ("id", "notebook_id", "source_id", *fallback_keys):
            item = plain.get(key)
            if item is not None and str(item):
                return str(item)
    for key in ("id", "notebook_id", "source_id", *fallback_keys):
        item = getattr(value, key, None)
        if item is not None and str(item):
            return str(item)
    digest = hashlib.sha256(json.dumps(plain, sort_keys=True, default=str).encode()).hexdigest()
    return digest[:16]


def stable_title(value: Any, default: str = "") -> str:
    """Extract a display title from a dict/object response."""
    plain = to_plain(value)
    if isinstance(plain, dict):
        for key in ("title", "name", "display_name"):
            item = plain.get(key)
            if item is not None and str(item):
                return str(item)
    for key in ("title", "name", "display_name"):
        item = getattr(value, key, None)
        if item is not None and str(item):
            return str(item)
    return default


def args_hash(args: BaseModel | dict[str, Any]) -> str:
    """Hash tool arguments for audit logging without storing raw values."""
    payload = args.model_dump(mode="json") if isinstance(args, BaseModel) else args
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


async def run_tool(
    tool_name: str,
    args: BaseModel | dict[str, Any],
    operation: Callable[[], Awaitable[T]],
) -> T:
    """Run a tool body with sanitized errors and structured audit events."""
    arg_hash = args_hash(args)
    try:
        result = await operation()
    except BackendError as exc:
        logger.warning(
            "tool_failed",
            tool=tool_name,
            args_hash=arg_hash,
            error_code=exc.error_code,
            error_class=exc.__class__.__name__,
        )
        raise ToolError(exc.safe_message) from None
    except PydanticValidationError as exc:
        logger.warning(
            "tool_failed",
            tool=tool_name,
            args_hash=arg_hash,
            error_code=-32602,
            error_class=exc.__class__.__name__,
        )
        raise ToolError(str(exc)) from None
    except Exception as exc:
        logger.warning(
            "tool_failed",
            tool=tool_name,
            args_hash=arg_hash,
            error_code=-32000,
            error_class=exc.__class__.__name__,
        )
        raise ToolError("NotebookLM tool execution failed.") from None
    logger.info("tool_completed", tool=tool_name, args_hash=arg_hash)
    return result


async def run_resource(resource_uri: str, operation: Callable[[], Awaitable[T]]) -> T:
    """Run a resource body with sanitized errors."""
    try:
        return await operation()
    except BackendError as exc:
        logger.warning(
            "resource_failed",
            resource=resource_uri,
            error_code=exc.error_code,
            error_class=exc.__class__.__name__,
        )
        raise ResourceError(exc.safe_message) from None
    except Exception as exc:
        logger.warning(
            "resource_failed",
            resource=resource_uri,
            error_code=-32000,
            error_class=exc.__class__.__name__,
        )
        raise ResourceError("NotebookLM resource read failed.") from None


def require_confirmation(confirm: bool, action: str) -> None:
    """Require explicit confirmation for destructive tool calls."""
    if not confirm:
        raise BackendValidationError(
            f"Confirmation required before {action}.",
            error_code=-32602,
            data={"confirmation_required": True},
        )
