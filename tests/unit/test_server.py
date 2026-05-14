from fastmcp import Client, FastMCP

from nlm_mcp import __version__
from nlm_mcp.config import AuthMode, Settings, TransportMode
from nlm_mcp.server import create_server


def test_create_server_returns_fastmcp_instance() -> None:
    server = create_server(Settings())

    assert isinstance(server, FastMCP)


async def test_admin_tools_are_registered_with_annotations() -> None:
    async with Client(create_server(Settings())) as client:
        tools = await client.list_tools()

    by_name = {tool.name: tool for tool in tools}
    assert {"admin_health", "admin_version"}.issubset(by_name)
    assert by_name["admin_health"].annotations is not None
    assert by_name["admin_health"].annotations.readOnlyHint is True
    assert by_name["admin_version"].annotations is not None
    assert by_name["admin_version"].annotations.readOnlyHint is True
    assert all("." not in name for name in by_name)


async def test_admin_health_tool_reports_server_state() -> None:
    settings = Settings(transport=TransportMode.STDIO, auth_mode=AuthMode.NONE)

    async with Client(create_server(settings)) as client:
        result = await client.call_tool("admin_health", {})

    assert result.data == {
        "status": "ok",
        "version": __version__,
        "transport": "stdio",
        "auth_mode": "none",
    }


async def test_admin_version_tool_reports_package_version() -> None:
    async with Client(create_server(Settings())) as client:
        result = await client.call_tool("admin_version", {})

    assert result.data["name"] == "notebooklm-mcp-pro"
    assert result.data["version"] == __version__
    assert result.data["python"].startswith("3.")
    assert result.data["fastmcp"]
