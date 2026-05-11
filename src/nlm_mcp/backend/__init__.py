"""NotebookLM backend adapter package."""

from nlm_mcp.backend.client import NotebookLMBackend
from nlm_mcp.backend.exceptions import BackendError

__all__ = ["BackendError", "NotebookLMBackend"]
