"""NotebookLM source tools."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from time import monotonic
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.backend.exceptions import BackendTimeoutError, BackendValidationError
from nlm_mcp.tools.common import (
    require_confirmation,
    run_tool,
    to_plain,
    tool_annotations,
    tool_public_name,
)
from nlm_mcp.tools.models import (
    ConfirmSourceInput,
    NotebookIdInput,
    SourceAddFileInput,
    SourceAddGDriveInput,
    SourceAddTextInput,
    SourceAddUrlInput,
    SourceIdInput,
    SourceWaitInput,
)

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend


def register_source_tools(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register NotebookLM source tools."""

    @server.tool(
        name=tool_public_name("source.add_url"),
        title="Add URL Source",
        annotations=tool_annotations(idempotent=False, open_world=True),
    )
    async def source_add_url(notebook_id: str, url: str, wait: bool = False) -> dict[str, Any]:
        """Add a web URL as a source to a NotebookLM notebook."""
        payload = SourceAddUrlInput.model_validate(
            {"notebook_id": notebook_id, "url": url, "wait": wait}
        )
        return await run_tool(
            "source.add_url",
            payload,
            lambda: _generic_result(
                backend.add_url_source(payload.notebook_id, str(payload.url), wait=payload.wait)
            ),
        )

    @server.tool(
        name=tool_public_name("source.add_youtube"),
        title="Add YouTube Source",
        annotations=tool_annotations(idempotent=False, open_world=True),
    )
    async def source_add_youtube(notebook_id: str, url: str, wait: bool = False) -> dict[str, Any]:
        """Add a YouTube URL as a source to a NotebookLM notebook."""
        payload = SourceAddUrlInput.model_validate(
            {"notebook_id": notebook_id, "url": url, "wait": wait}
        )
        return await run_tool(
            "source.add_youtube",
            payload,
            lambda: _generic_result(
                backend.add_youtube_source(payload.notebook_id, str(payload.url), wait=payload.wait)
            ),
        )

    @server.tool(
        name=tool_public_name("source.add_file"),
        title="Add File Source",
        annotations=tool_annotations(idempotent=False),
    )
    async def source_add_file(
        notebook_id: str,
        file_path: str,
        mime_type: str | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        """Upload a PDF, audio, video, image, text, markdown, or docx source."""
        payload = SourceAddFileInput(
            notebook_id=notebook_id,
            file_path=file_path,
            mime_type=mime_type,
            wait=wait,
        )
        return await run_tool(
            "source.add_file",
            payload,
            lambda: _generic_result(
                backend.add_file_source(
                    payload.notebook_id,
                    payload.file_path,
                    mime_type=payload.mime_type,
                    wait=payload.wait,
                )
            ),
        )

    @server.tool(
        name=tool_public_name("source.add_gdrive"),
        title="Add Google Drive Source",
        annotations=tool_annotations(idempotent=False, open_world=True),
    )
    async def source_add_gdrive(
        notebook_id: str,
        file_id: str,
        title: str,
        mime_type: str = "application/vnd.google-apps.document",
        wait: bool = False,
    ) -> dict[str, Any]:
        """Add a Google Drive document as a source to a NotebookLM notebook."""
        payload = SourceAddGDriveInput(
            notebook_id=notebook_id,
            file_id=file_id,
            title=title,
            mime_type=mime_type,
            wait=wait,
        )
        return await run_tool(
            "source.add_gdrive",
            payload,
            lambda: _generic_result(
                backend.add_drive_source(
                    payload.notebook_id,
                    payload.file_id,
                    payload.title,
                    mime_type=payload.mime_type,
                    wait=payload.wait,
                )
            ),
        )

    @server.tool(
        name=tool_public_name("source.add_text"),
        title="Add Text Source",
        annotations=tool_annotations(idempotent=False),
    )
    async def source_add_text(
        notebook_id: str,
        title: str,
        content: str,
        wait: bool = False,
    ) -> dict[str, Any]:
        """Paste raw text as a source in a NotebookLM notebook."""
        payload = SourceAddTextInput(
            notebook_id=notebook_id,
            title=title,
            content=content,
            wait=wait,
        )
        return await run_tool(
            "source.add_text",
            payload,
            lambda: _generic_result(
                backend.add_text_source(
                    payload.notebook_id,
                    payload.title,
                    payload.content,
                    wait=payload.wait,
                )
            ),
        )

    @server.tool(
        name=tool_public_name("source.list"),
        title="List Sources",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def source_list(notebook_id: str) -> dict[str, Any]:
        """List sources in a NotebookLM notebook."""
        payload = NotebookIdInput(notebook_id=notebook_id)
        return await run_tool(
            "source.list",
            payload,
            lambda: _list_sources(backend, payload.notebook_id),
        )

    @server.tool(
        name=tool_public_name("source.get"),
        title="Get Source",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def source_get(notebook_id: str, source_id: str) -> dict[str, Any]:
        """Get metadata for one NotebookLM source."""
        payload = SourceIdInput(notebook_id=notebook_id, source_id=source_id)
        return await run_tool(
            "source.get",
            payload,
            lambda: _generic_result(backend.get_source(payload.notebook_id, payload.source_id)),
        )

    @server.tool(
        name=tool_public_name("source.get_fulltext"),
        title="Get Source Full Text",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def source_get_fulltext(notebook_id: str, source_id: str) -> dict[str, Any]:
        """Retrieve indexed full text for one NotebookLM source."""
        payload = SourceIdInput(notebook_id=notebook_id, source_id=source_id)
        return await run_tool(
            "source.get_fulltext",
            payload,
            lambda: _generic_result(
                backend.get_source_fulltext(payload.notebook_id, payload.source_id)
            ),
        )

    @server.tool(
        name=tool_public_name("source.refresh"),
        title="Refresh Source",
        annotations=tool_annotations(idempotent=True),
    )
    async def source_refresh(notebook_id: str, source_id: str) -> dict[str, Any]:
        """Re-index one NotebookLM source."""
        payload = SourceIdInput(notebook_id=notebook_id, source_id=source_id)
        return await run_tool(
            "source.refresh",
            payload,
            lambda: _generic_result(backend.refresh_source(payload.notebook_id, payload.source_id)),
        )

    @server.tool(
        name=tool_public_name("source.wait"),
        title="Wait For Source",
        annotations=tool_annotations(read_only=True, idempotent=False),
    )
    async def source_wait(
        notebook_id: str,
        source_id: str,
        poll_interval_sec: int = 5,
        timeout_sec: int = 300,
    ) -> dict[str, Any]:
        """Wait until one NotebookLM source leaves the indexing state."""
        payload = SourceWaitInput(
            notebook_id=notebook_id,
            source_id=source_id,
            poll_interval_sec=poll_interval_sec,
            timeout_sec=timeout_sec,
        )
        return await run_tool(
            "source.wait",
            payload,
            lambda: _wait_for_source(backend, payload),
        )

    @server.tool(
        name=tool_public_name("source.remove"),
        title="Remove Source",
        annotations=tool_annotations(destructive=True, idempotent=False),
    )
    async def source_remove(
        notebook_id: str,
        source_id: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Remove a source from a NotebookLM notebook after explicit confirmation."""
        payload = ConfirmSourceInput(notebook_id=notebook_id, source_id=source_id, confirm=confirm)

        async def operation() -> dict[str, Any]:
            require_confirmation(payload.confirm, "removing a source")
            removed = await backend.remove_source(payload.notebook_id, payload.source_id)
            return {
                "removed": bool(removed),
                "notebook_id": payload.notebook_id,
                "source_id": payload.source_id,
            }

        return await run_tool("source.remove", payload, operation)


async def _list_sources(backend: NotebookLMBackend, notebook_id: str) -> dict[str, Any]:
    sources = await backend.list_sources(notebook_id)
    return {"sources": to_plain(sources)}


async def _generic_result(awaitable: Awaitable[Any]) -> dict[str, Any]:
    return {"result": to_plain(await awaitable)}


async def _wait_for_source(
    backend: NotebookLMBackend,
    payload: SourceWaitInput,
) -> dict[str, Any]:
    deadline = monotonic() + payload.timeout_sec
    last_source: dict[str, Any] = {}
    while monotonic() <= deadline:
        source = to_plain(await backend.get_source(payload.notebook_id, payload.source_id))
        if isinstance(source, dict):
            last_source = source
            state = str(source.get("status", "")).casefold()
            if state in {"failed", "error"}:
                raise BackendValidationError(
                    "NotebookLM source indexing failed.",
                    error_code=-32602,
                    data={"source": source},
                )
            if state not in {"pending", "processing", "indexing", "refreshing"}:
                return {"source": source}
        await asyncio.sleep(payload.poll_interval_sec)
    raise BackendTimeoutError(
        "NotebookLM source indexing timed out.",
        error_code=-32003,
        data={"timeout_seconds": payload.timeout_sec, "last_source": last_source},
    )
