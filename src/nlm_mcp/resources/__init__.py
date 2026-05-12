"""NotebookLM MCP resource registration."""

from nlm_mcp.resources.artifact import register_artifact_resources
from nlm_mcp.resources.notebook import register_core_resources

__all__ = ["register_artifact_resources", "register_core_resources"]
