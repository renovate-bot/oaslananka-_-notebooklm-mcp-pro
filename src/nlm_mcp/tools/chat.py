"""NotebookLM chat tools."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.tools.common import run_tool, to_plain, tool_annotations
from nlm_mcp.tools.models import (
    ChatAskInput,
    ChatHistoryInput,
    ConversationStartInput,
    SaveToNotesInput,
)

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend


def register_chat_tools(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register NotebookLM chat tools."""

    @server.tool(
        name="chat.ask",
        title="Ask Notebook",
        annotations=tool_annotations(idempotent=False),
    )
    async def chat_ask(
        notebook_id: str,
        question: str,
        source_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ask a one-shot question against a NotebookLM notebook."""
        payload = ChatAskInput(
            notebook_id=notebook_id,
            question=question,
            source_ids=source_ids,
        )
        return await run_tool(
            "chat.ask",
            payload,
            lambda: _generic_result(
                backend.ask(
                    payload.notebook_id,
                    payload.question,
                    source_ids=payload.source_ids,
                )
            ),
        )

    @server.tool(
        name="chat.conversation_start",
        title="Start Conversation",
        annotations=tool_annotations(idempotent=False),
    )
    async def chat_conversation_start(
        notebook_id: str,
        name: str = "NotebookLM conversation",
        initial_question: str | None = None,
    ) -> dict[str, Any]:
        """Start or identify the active NotebookLM conversation for a notebook."""
        payload = ConversationStartInput(
            notebook_id=notebook_id,
            name=name,
            initial_question=initial_question,
        )
        return await run_tool(
            "chat.conversation_start",
            payload,
            lambda: _start_conversation(backend, payload),
        )

    @server.tool(
        name="chat.continue",
        title="Continue Conversation",
        annotations=tool_annotations(idempotent=False),
    )
    async def chat_continue(
        notebook_id: str,
        question: str,
        conversation_id: str | None = None,
        source_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Continue a NotebookLM conversation."""
        payload = ChatAskInput(
            notebook_id=notebook_id,
            question=question,
            source_ids=source_ids,
            conversation_id=conversation_id,
        )
        return await run_tool(
            "chat.continue",
            payload,
            lambda: _generic_result(
                backend.ask(
                    payload.notebook_id,
                    payload.question,
                    source_ids=payload.source_ids,
                    conversation_id=payload.conversation_id,
                )
            ),
        )

    @server.tool(
        name="chat.history",
        title="Chat History",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def chat_history(
        notebook_id: str,
        limit: int = 100,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Get NotebookLM conversation history."""
        payload = ChatHistoryInput(
            notebook_id=notebook_id,
            limit=limit,
            conversation_id=conversation_id,
        )
        return await run_tool(
            "chat.history",
            payload,
            lambda: _history(backend, payload),
        )

    @server.tool(
        name="chat.save_to_notes",
        title="Save Chat Answer To Notes",
        annotations=tool_annotations(idempotent=False),
    )
    async def chat_save_to_notes(notebook_id: str, title: str, content: str) -> dict[str, Any]:
        """Save a chat answer or drafted content as a NotebookLM note."""
        payload = SaveToNotesInput(notebook_id=notebook_id, title=title, content=content)
        return await run_tool(
            "chat.save_to_notes",
            payload,
            lambda: _generic_result(
                backend.save_note(payload.notebook_id, payload.title, payload.content)
            ),
        )


async def _start_conversation(
    backend: NotebookLMBackend,
    payload: ConversationStartInput,
) -> dict[str, Any]:
    conversation_id: str | None = None
    if payload.initial_question:
        result = await backend.ask(payload.notebook_id, payload.initial_question)
        plain_result = to_plain(result)
        if isinstance(plain_result, dict):
            raw_conversation_id = plain_result.get("conversation_id")
            if raw_conversation_id:
                conversation_id = str(raw_conversation_id)
    else:
        plain_result = None
    if conversation_id is None:
        resolved_conversation_id = await backend.get_conversation_id(payload.notebook_id)
        if resolved_conversation_id:
            conversation_id = str(resolved_conversation_id)
    return {
        "conversation_id": conversation_id or "default",
        "name": payload.name,
        "notebook_id": payload.notebook_id,
        "initial_result": plain_result,
    }


async def _history(backend: NotebookLMBackend, payload: ChatHistoryInput) -> dict[str, Any]:
    history = await backend.get_chat_history(
        payload.notebook_id,
        limit=payload.limit,
        conversation_id=payload.conversation_id,
    )
    return {"history": to_plain(history)}


async def _generic_result(awaitable: Awaitable[Any]) -> dict[str, Any]:
    return {"result": to_plain(await awaitable)}
