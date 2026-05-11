"""FastMCP server factory."""

from __future__ import annotations

from fastmcp import FastMCP

from nlm_mcp import __version__
from nlm_mcp.config import Settings
from nlm_mcp.tools.admin import register_admin_tools


def create_server(settings: Settings | None = None) -> FastMCP:
    """Create a configured FastMCP server with core tools registered."""
    resolved = settings or Settings()
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
    return server
