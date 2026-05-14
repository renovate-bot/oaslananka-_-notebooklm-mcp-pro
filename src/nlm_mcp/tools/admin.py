"""Administrative MCP tools."""

from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict

from nlm_mcp import __version__
from nlm_mcp.config import Settings
from nlm_mcp.tools.common import tool_public_name


class HealthOutput(BaseModel):
    """Health status returned by `admin.health`."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    version: str
    transport: str
    auth_mode: str


class VersionOutput(BaseModel):
    """Version metadata returned by `admin.version`."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    python: str
    fastmcp: str


def build_health(settings: Settings) -> HealthOutput:
    """Build current health metadata without touching external services."""
    return HealthOutput(
        status="ok",
        version=__version__,
        transport=settings.transport.value,
        auth_mode=settings.auth_mode.value,
    )


def build_version_info() -> VersionOutput:
    """Build package and runtime version metadata."""
    try:
        fastmcp_version = version("fastmcp")
    except PackageNotFoundError:
        fastmcp_version = "unknown"
    return VersionOutput(
        name="notebooklm-mcp-pro",
        version=__version__,
        python=platform.python_version(),
        fastmcp=fastmcp_version,
    )


def register_admin_tools(server: FastMCP, settings: Settings) -> None:
    """Register administrative tools on the provided FastMCP server."""
    read_only = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    @server.tool(
        name=tool_public_name("admin.health"),
        title="Server Health",
        annotations=read_only,
    )
    async def admin_health() -> dict[str, str]:
        """Return local server health and selected safe configuration fields."""
        return build_health(settings).model_dump()

    @server.tool(
        name=tool_public_name("admin.version"),
        title="Server Version",
        annotations=read_only,
    )
    async def admin_version() -> dict[str, str]:
        """Return package, Python, and FastMCP version metadata."""
        return build_version_info().model_dump()
