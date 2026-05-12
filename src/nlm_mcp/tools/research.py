"""NotebookLM research tools."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.backend.exceptions import BackendTimeoutError
from nlm_mcp.tools.common import run_tool, to_plain, tool_annotations
from nlm_mcp.tools.models import NotebookIdInput, ResearchStartInput, ResearchWaitInput

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend


def register_research_tools(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register NotebookLM research tools."""

    @server.tool(
        name="research.web_start",
        title="Start Web Research",
        annotations=tool_annotations(idempotent=False, open_world=True),
    )
    async def research_web_start(
        notebook_id: str,
        query: str,
        mode: str = "fast",
    ) -> dict[str, Any]:
        """Start a web research task for a notebook."""
        payload = ResearchStartInput.model_validate(
            {"notebook_id": notebook_id, "query": query, "mode": mode}
        )
        return await run_tool(
            "research.web_start",
            payload,
            lambda: _generic_result(
                backend.start_research(
                    payload.notebook_id,
                    payload.query,
                    source="web",
                    mode=payload.mode,
                )
            ),
        )

    @server.tool(
        name="research.drive_start",
        title="Start Drive Research",
        annotations=tool_annotations(idempotent=False),
    )
    async def research_drive_start(notebook_id: str, query: str) -> dict[str, Any]:
        """Start a Google Drive research task for a notebook."""
        payload = ResearchStartInput(notebook_id=notebook_id, query=query, mode="fast")
        return await run_tool(
            "research.drive_start",
            payload,
            lambda: _generic_result(
                backend.start_research(
                    payload.notebook_id,
                    payload.query,
                    source="drive",
                    mode="fast",
                )
            ),
        )

    @server.tool(
        name="research.status",
        title="Research Status",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def research_status(notebook_id: str) -> dict[str, Any]:
        """Poll the latest research task status for a notebook."""
        payload = NotebookIdInput(notebook_id=notebook_id)
        return await run_tool(
            "research.status",
            payload,
            lambda: _generic_result(backend.research_status(payload.notebook_id)),
        )

    @server.tool(
        name="research.wait",
        title="Wait For Research",
        annotations=tool_annotations(read_only=True, idempotent=False),
    )
    async def research_wait(
        notebook_id: str,
        task_id: str | None = None,
        poll_interval_sec: int = 15,
        timeout_sec: int = 600,
        auto_import: bool = False,
        max_sources: int = 10,
    ) -> dict[str, Any]:
        """Wait until the latest research task completes, optionally importing sources."""
        payload = ResearchWaitInput(
            notebook_id=notebook_id,
            task_id=task_id,
            poll_interval_sec=poll_interval_sec,
            timeout_sec=timeout_sec,
            auto_import=auto_import,
            max_sources=max_sources,
        )
        return await run_tool(
            "research.wait",
            payload,
            lambda: _wait_for_research(backend, payload),
        )


async def _wait_for_research(
    backend: NotebookLMBackend,
    payload: ResearchWaitInput,
) -> dict[str, Any]:
    deadline = monotonic() + payload.timeout_sec
    last_status: dict[str, Any] = {}
    while monotonic() <= deadline:
        status = to_plain(await backend.research_status(payload.notebook_id))
        if isinstance(status, dict):
            last_status = status
            status_task_id = status.get("task_id")
            if payload.task_id and str(status_task_id) != payload.task_id:
                await asyncio.sleep(payload.poll_interval_sec)
                continue
            state = status.get("status")
            if state in {"completed", "no_research", "failed", "error"}:
                imported: Any = []
                sources = status.get("sources", [])
                task_id = payload.task_id or status.get("task_id")
                if (
                    state == "completed"
                    and payload.auto_import
                    and task_id
                    and isinstance(sources, list)
                ):
                    imported = await backend.import_research_sources(
                        payload.notebook_id,
                        str(task_id),
                        sources[: payload.max_sources],
                    )
                return {"research": status, "imported": to_plain(imported)}
        await asyncio.sleep(payload.poll_interval_sec)
    raise BackendTimeoutError(
        "NotebookLM research task timed out.",
        error_code=-32003,
        data={"timeout_seconds": payload.timeout_sec, "last_status": last_status},
    )


async def _generic_result(awaitable: Any) -> dict[str, Any]:
    return {"result": to_plain(await awaitable)}
