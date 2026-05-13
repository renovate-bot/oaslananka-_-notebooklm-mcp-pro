"""Tests for NotebookLM language tools."""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from nlm_mcp.backend.client import NotebookLMBackend
from nlm_mcp.config import Settings
from nlm_mcp.server import create_server

MIN_SUPPORTED_LANGUAGES = 80


class LanguageBackend:
    """In-memory backend for language tool tests."""

    def __init__(self) -> None:
        self.language = "en"

    async def get_language(self) -> str:
        return self.language

    async def set_language(self, language: str) -> str:
        self.language = language
        return language


def _server(backend: LanguageBackend | None = None) -> Any:
    return create_server(Settings(), backend=cast(NotebookLMBackend, backend or LanguageBackend()))


async def test_language_list_returns_supported_languages() -> None:
    async with Client(_server()) as client:
        result = await client.call_tool("language.list", {})

    assert result.data["count"] >= MIN_SUPPORTED_LANGUAGES
    assert {"code": "en", "name": "English"} in result.data["languages"]


async def test_language_get_returns_current_language() -> None:
    async with Client(_server()) as client:
        result = await client.call_tool("language.get", {})

    assert result.data == {"language": "en", "name": "English"}


async def test_language_set_requires_confirmation() -> None:
    async with Client(_server()) as client:
        with pytest.raises(ToolError, match="Confirmation required"):
            await client.call_tool("language.set", {"language": "tr"})


async def test_language_set_valid_language() -> None:
    backend = LanguageBackend()
    async with Client(_server(backend)) as client:
        result = await client.call_tool("language.set", {"language": "tr", "confirm": True})

    assert result.data["language"] == "tr"
    assert backend.language == "tr"


async def test_language_set_invalid_language_errors() -> None:
    async with Client(_server()) as client:
        with pytest.raises(ToolError, match="Unsupported NotebookLM language"):
            await client.call_tool("language.set", {"language": "xx-invalid", "confirm": True})
