"""ChatGPT compatibility tools."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.backend.exceptions import BackendValidationError
from nlm_mcp.tools.common import run_tool, stable_id, stable_title, to_plain, tool_annotations
from nlm_mcp.tools.models import FetchInput, FetchOutput, SearchInput, SearchOutput

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend

SOURCE_RECORD_PARTS = 3


def register_compat_tools(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register ChatGPT-compatible `search` and `fetch` tools."""

    @server.tool(
        name="search",
        title="Search NotebookLM Records",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def search(query: str = "", limit: int = 20) -> dict[str, list[str]]:
        """Return matching NotebookLM notebook and source record ids."""
        payload = SearchInput(query=query, limit=limit)
        result = await run_tool("search", payload, lambda: _search(backend, payload))
        return SearchOutput(ids=result["ids"]).model_dump()

    @server.tool(
        name="fetch",
        title="Fetch NotebookLM Record",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def fetch(id: str) -> dict[str, Any]:
        """Return one NotebookLM record as `{id, title, content, metadata}`."""
        payload = FetchInput(id=id)
        result = await run_tool("fetch", payload, lambda: _fetch(backend, payload))
        return FetchOutput(**result).model_dump()


async def _search(backend: NotebookLMBackend, payload: SearchInput) -> dict[str, list[str]]:
    query = payload.query.casefold().strip()
    ids: list[str] = []
    notebooks = to_plain(await backend.list_notebooks())
    notebook_records: list[tuple[str, str]] = []
    for notebook in notebooks:
        notebook_id = stable_id(notebook)
        notebook_title = stable_title(notebook)
        notebook_records.append((notebook_id, notebook_title))
        if _matches(query, notebook_title):
            ids.append(f"notebook:{notebook_id}")
        if len(ids) >= payload.limit:
            return {"ids": ids}

    source_lists = await asyncio.gather(
        *(backend.list_sources(notebook_id) for notebook_id, _ in notebook_records)
    )
    for (notebook_id, _), sources_response in zip(notebook_records, source_lists, strict=True):
        sources = to_plain(sources_response)
        for source in sources:
            source_id = stable_id(source)
            source_title = stable_title(source)
            if _matches(query, source_title):
                ids.append(f"source:{notebook_id}:{source_id}")
            if len(ids) >= payload.limit:
                return {"ids": ids}
    return {"ids": ids}


async def _fetch(backend: NotebookLMBackend, payload: FetchInput) -> dict[str, Any]:
    if payload.id.startswith("notebook:"):
        notebook_id = payload.id.removeprefix("notebook:")
        if not notebook_id:
            raise BackendValidationError(
                "Notebook record id must use notebook:{notebook_id}.",
                error_code=-32602,
                data={"id": payload.id},
            )
        notebook = to_plain(await backend.get_notebook(notebook_id))
        return {
            "id": payload.id,
            "title": stable_title(notebook, default=notebook_id),
            "content": json.dumps(notebook, sort_keys=True),
            "metadata": {"kind": "notebook", "notebook_id": notebook_id, "record": notebook},
        }
    if payload.id.startswith("source:"):
        parts = payload.id.split(":", 2)
        if len(parts) != SOURCE_RECORD_PARTS or not parts[1] or not parts[2]:
            raise BackendValidationError(
                "Source record id must use source:{notebook_id}:{source_id}.",
                error_code=-32602,
                data={"id": payload.id},
            )
        _, notebook_id, source_id = parts
        source = to_plain(await backend.get_source(notebook_id, source_id))
        fulltext = to_plain(await backend.get_source_fulltext(notebook_id, source_id))
        return {
            "id": payload.id,
            "title": stable_title(source, default=source_id),
            "content": _content_from_fulltext(fulltext),
            "metadata": {
                "kind": "source",
                "notebook_id": notebook_id,
                "source_id": source_id,
                "source": source,
            },
        }
    raise BackendValidationError(
        "Unsupported record id.",
        error_code=-32602,
        data={"id": payload.id},
    )


def _matches(query: str, title: str) -> bool:
    return not query or query in title.casefold()


def _content_from_fulltext(value: Any) -> str:
    plain = to_plain(value)
    if isinstance(plain, dict):
        for key in ("text", "content", "fulltext"):
            item = plain.get(key)
            if item is not None:
                return str(item)
    if isinstance(plain, str):
        return plain
    return json.dumps(plain, sort_keys=True)
