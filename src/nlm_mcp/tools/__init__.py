"""Tool registration package for NotebookLM MCP."""

from nlm_mcp.tools.admin import HealthOutput, VersionOutput, register_admin_tools

__all__ = ["HealthOutput", "VersionOutput", "register_admin_tools"]
