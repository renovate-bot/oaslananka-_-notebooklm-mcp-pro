import asyncio
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_stdio_server_initializes_and_lists_core_tools() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "nlm_mcp", "stdio"],
        cwd=repo_root,
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await asyncio.wait_for(session.initialize(), timeout=10)
        tools = await asyncio.wait_for(session.list_tools(), timeout=10)
        resources = await asyncio.wait_for(session.list_resources(), timeout=10)
        prompts = await asyncio.wait_for(session.list_prompts(), timeout=10)

    tool_names = {tool.name for tool in tools.tools}
    assert {"admin.health", "admin.version"}.issubset(tool_names)
    assert resources.resources == []
    assert prompts.prompts == []
