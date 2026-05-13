"""Tests for ChatGPT-compatible search and fetch tools."""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from nlm_mcp.backend.client import NotebookLMBackend
from nlm_mcp.config import Settings
from nlm_mcp.server import create_server


class CompatBackend:
    """In-memory backend for search and fetch tests."""

    async def list_notebooks(self) -> list[dict[str, Any]]:
        return [
            {"id": "nb-1", "title": "Climate Research"},
            {"id": "nb-2", "title": "Finance Notes"},
        ]

    async def list_sources(self, notebook_id: str) -> list[dict[str, Any]]:
        sources = {
            "nb-1": [
                {"id": "src-1", "title": "Climate Paper"},
                {"id": "src-2", "title": "Emissions Data"},
            ],
            "nb-2": [{"id": "src-3", "title": "Budget Sheet"}],
        }
        return sources.get(notebook_id, [])

    async def get_notebook(self, notebook_id: str) -> dict[str, Any]:
        return {"id": notebook_id, "title": "Climate Research", "source_count": 2}

    async def get_source(self, notebook_id: str, source_id: str) -> dict[str, Any]:
        return {"id": source_id, "notebook_id": notebook_id, "title": "Climate Paper"}

    async def get_source_fulltext(self, notebook_id: str, source_id: str) -> dict[str, str]:
        return {"notebook_id": notebook_id, "source_id": source_id, "text": "full text"}


def _server() -> Any:
    return create_server(Settings(), backend=cast(NotebookLMBackend, CompatBackend()))


async def test_search_empty_query_returns_notebooks_and_sources() -> None:
    async with Client(_server()) as client:
        result = await client.call_tool("search", {"query": "", "limit": 10})

    assert result.data["ids"] == [
        "notebook:nb-1",
        "notebook:nb-2",
        "source:nb-1:src-1",
        "source:nb-1:src-2",
        "source:nb-2:src-3",
    ]


async def test_search_query_filters_and_limit_applies() -> None:
    async with Client(_server()) as client:
        result = await client.call_tool("search", {"query": "climate", "limit": 1})

    assert result.data["ids"] == ["notebook:nb-1"]


async def test_fetch_notebook_record() -> None:
    async with Client(_server()) as client:
        result = await client.call_tool("fetch", {"id": "notebook:nb-1"})

    assert result.data["id"] == "notebook:nb-1"
    assert result.data["title"] == "Climate Research"
    assert result.data["metadata"]["kind"] == "notebook"


async def test_fetch_source_record() -> None:
    async with Client(_server()) as client:
        result = await client.call_tool("fetch", {"id": "source:nb-1:src-1"})

    assert result.data == {
        "id": "source:nb-1:src-1",
        "title": "Climate Paper",
        "content": "full text",
        "metadata": {
            "kind": "source",
            "notebook_id": "nb-1",
            "source_id": "src-1",
            "source": {"id": "src-1", "notebook_id": "nb-1", "title": "Climate Paper"},
        },
    }


async def test_fetch_unknown_id_errors() -> None:
    async with Client(_server()) as client:
        with pytest.raises(ToolError, match="Unsupported record id"):
            await client.call_tool("fetch", {"id": "unknown:1"})
