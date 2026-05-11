"""Stdio transport runner."""

from __future__ import annotations

from nlm_mcp.config import Settings, TransportMode
from nlm_mcp.server import create_server


def run_stdio(settings: Settings | None = None) -> None:
    """Run the FastMCP server over stdio."""
    resolved = settings or Settings(transport=TransportMode.STDIO)
    if resolved.transport is not TransportMode.STDIO:
        raise ValueError("run_stdio requires settings with transport=stdio")
    server = create_server(resolved)
    server.run(transport="stdio", show_banner=False)
