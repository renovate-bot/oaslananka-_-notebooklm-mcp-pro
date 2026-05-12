"""FastMCP server factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fastmcp import FastMCP

from nlm_mcp import __version__
from nlm_mcp.config import Settings
from nlm_mcp.resources import register_core_resources
from nlm_mcp.tools import (
    register_admin_tools,
    register_chat_tools,
    register_compat_tools,
    register_notebook_tools,
    register_source_tools,
)

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend


class _LazyNotebookLMBackend:
    """Defer notebooklm-py import cost until a backend method is called."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._backend: Any | None = None

    def _resolve(self) -> Any:
        if self._backend is None:
            from nlm_mcp.backend.client import NotebookLMBackend  # noqa: PLC0415

            self._backend = NotebookLMBackend(self._settings)
        return self._backend

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)


def create_server(
    settings: Settings | None = None,
    *,
    backend: NotebookLMBackend | None = None,
) -> FastMCP:
    """Create a configured FastMCP server with core tools registered."""
    resolved = settings or Settings()
    resolved_backend = backend or cast("NotebookLMBackend", _LazyNotebookLMBackend(resolved))
    server = FastMCP(
        name="notebooklm_mcp",
        instructions=(
            "Programmatic MCP access to Google NotebookLM. "
            "Use admin.health first to verify server readiness."
        ),
        version=__version__,
        strict_input_validation=True,
    )
    register_admin_tools(server, resolved)
    register_notebook_tools(server, resolved_backend)
    register_source_tools(server, resolved_backend)
    register_chat_tools(server, resolved_backend)
    register_compat_tools(server, resolved_backend)
    register_core_resources(server, resolved_backend)
    return server
