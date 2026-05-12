"""Notebook and source MCP resources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.tools.common import run_resource, to_plain

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend

READ_ONLY_ANNOTATIONS = {"readOnlyHint": True, "idempotentHint": True}


def register_core_resources(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register core NotebookLM resource URIs."""

    @server.resource(
        "notebooklm://notebooks",
        title="NotebookLM Notebooks",
        mime_type="application/json",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def notebooks_resource() -> str:
        """Return all notebooks as JSON."""
        return await run_resource(
            "notebooklm://notebooks",
            lambda: _json_resource({"notebooks": backend.list_notebooks()}),
        )

    @server.resource(
        "notebooklm://notebook/{id}",
        title="NotebookLM Notebook",
        mime_type="application/json",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def notebook_resource(id: str) -> str:
        """Return notebook metadata and source index as JSON."""
        return await run_resource(
            f"notebooklm://notebook/{id}",
            lambda: _notebook_resource(backend, id),
        )

    @server.resource(
        "notebooklm://notebook/{id}/source/{src_id}",
        title="NotebookLM Source",
        mime_type="application/json",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def source_resource(id: str, src_id: str) -> str:
        """Return source metadata as JSON."""
        return await run_resource(
            f"notebooklm://notebook/{id}/source/{src_id}",
            lambda: _json_resource({"source": backend.get_source(id, src_id)}),
        )

    @server.resource(
        "notebooklm://notebook/{id}/source/{src_id}/fulltext",
        title="NotebookLM Source Full Text",
        mime_type="application/json",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def source_fulltext_resource(id: str, src_id: str) -> str:
        """Return source full text as JSON."""
        return await run_resource(
            f"notebooklm://notebook/{id}/source/{src_id}/fulltext",
            lambda: _json_resource({"fulltext": backend.get_source_fulltext(id, src_id)}),
        )


async def _notebook_resource(backend: NotebookLMBackend, notebook_id: str) -> str:
    notebook = await backend.get_notebook(notebook_id)
    sources = await backend.list_sources(notebook_id)
    return _dumps({"notebook": to_plain(notebook), "sources": to_plain(sources)})


async def _json_resource(payload: dict[str, Any]) -> str:
    resolved: dict[str, Any] = {}
    for key, value in payload.items():
        if hasattr(value, "__await__"):
            resolved[key] = to_plain(await value)
        else:
            resolved[key] = to_plain(value)
    return _dumps(resolved)


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)
