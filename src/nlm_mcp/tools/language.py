"""NotebookLM language tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from notebooklm.cli.language import SUPPORTED_LANGUAGES

from nlm_mcp.backend.exceptions import BackendValidationError
from nlm_mcp.tools.common import require_confirmation, run_tool, to_plain, tool_annotations
from nlm_mcp.tools.models import LanguageSetInput, NotebookListInput

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend


def register_language_tools(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register NotebookLM language tools."""

    @server.tool(
        name="language.list",
        title="List Languages",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def language_list() -> dict[str, Any]:
        """List supported NotebookLM output languages."""
        payload = NotebookListInput()
        return await run_tool(
            "language.list",
            payload,
            _language_list,
        )

    @server.tool(
        name="language.get",
        title="Get Language",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def language_get() -> dict[str, Any]:
        """Get the current global NotebookLM output language."""
        payload = NotebookListInput()
        return await run_tool(
            "language.get",
            payload,
            lambda: _language_get(backend),
        )

    @server.tool(
        name="language.set",
        title="Set Language",
        annotations=tool_annotations(destructive=True, idempotent=True),
    )
    async def language_set(language: str, confirm: bool = False) -> dict[str, Any]:
        """Set the account-global NotebookLM output language after confirmation."""
        payload = LanguageSetInput(language=language, confirm=confirm)
        return await run_tool(
            "language.set",
            payload,
            lambda: _language_set(backend, payload),
        )


async def _language_list() -> dict[str, Any]:
    return {
        "languages": [{"code": code, "name": name} for code, name in SUPPORTED_LANGUAGES.items()],
        "count": len(SUPPORTED_LANGUAGES),
    }


async def _language_get(backend: NotebookLMBackend) -> dict[str, Any]:
    language = to_plain(await backend.get_language())
    return {
        "language": language,
        "name": SUPPORTED_LANGUAGES.get(str(language)) if language else None,
    }


async def _language_set(
    backend: NotebookLMBackend,
    payload: LanguageSetInput,
) -> dict[str, Any]:
    require_confirmation(payload.confirm, "changing the account-global output language")
    if payload.language not in SUPPORTED_LANGUAGES:
        raise BackendValidationError(
            "Unsupported NotebookLM language.",
            error_code=-32602,
            data={"language": payload.language},
        )
    language = to_plain(await backend.set_language(payload.language))
    return {
        "language": language or payload.language,
        "name": SUPPORTED_LANGUAGES.get(str(language or payload.language)),
    }
