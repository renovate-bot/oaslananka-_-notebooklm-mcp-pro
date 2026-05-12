"""Tool registration package for NotebookLM MCP."""

from nlm_mcp.tools.admin import HealthOutput, VersionOutput, register_admin_tools
from nlm_mcp.tools.chat import register_chat_tools
from nlm_mcp.tools.compat import register_compat_tools
from nlm_mcp.tools.notebooks import register_notebook_tools
from nlm_mcp.tools.sources import register_source_tools

__all__ = [
    "HealthOutput",
    "VersionOutput",
    "register_admin_tools",
    "register_chat_tools",
    "register_compat_tools",
    "register_notebook_tools",
    "register_source_tools",
]
