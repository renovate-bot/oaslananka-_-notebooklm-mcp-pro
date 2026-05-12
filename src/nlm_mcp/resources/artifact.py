"""Artifact MCP resources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.backend.exceptions import BackendNotFoundError
from nlm_mcp.backend.tasks import TaskStore
from nlm_mcp.tools.common import run_resource, to_plain

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend

READ_ONLY_ANNOTATIONS = {"readOnlyHint": True, "idempotentHint": True}


def register_artifact_resources(
    server: FastMCP,
    backend: NotebookLMBackend,
    task_store: TaskStore,
) -> None:
    """Register artifact and mind-map resource URIs."""

    @server.resource(
        "notebooklm://notebook/{id}/mindmap",
        title="NotebookLM Mind Map",
        mime_type="application/json",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def mindmap_resource(id: str) -> str:
        """Return mind-map artifacts for a notebook as JSON."""
        return await run_resource(
            f"notebooklm://notebook/{id}/mindmap",
            lambda: _mindmap_resource(backend, id),
        )

    @server.resource(
        "notebooklm://artifact/{task_id}",
        title="NotebookLM Artifact",
        mime_type="application/json",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def artifact_resource(task_id: str) -> str:
        """Return tracked artifact metadata as JSON."""
        return await run_resource(
            f"notebooklm://artifact/{task_id}",
            lambda: _artifact_resource(task_store, task_id),
        )


async def _mindmap_resource(backend: NotebookLMBackend, notebook_id: str) -> str:
    mind_maps = await backend.artifact_list(notebook_id, "mind_map")
    return _dumps({"notebook_id": notebook_id, "mind_maps": to_plain(mind_maps)})


async def _artifact_resource(task_store: TaskStore, task_id: str) -> str:
    record = await task_store.get(task_id)
    if record is None:
        raise BackendNotFoundError(
            "Artifact task was not found.",
            error_code=-32004,
            data={"task_id": task_id},
        )
    return _dumps({"artifact": record.__dict__})


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(to_plain(payload), sort_keys=True)
