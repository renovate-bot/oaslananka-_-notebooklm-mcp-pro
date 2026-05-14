import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.exceptions import ResourceError, ToolError

from nlm_mcp.backend.client import NotebookLMBackend
from nlm_mcp.backend.exceptions import BackendValidationError
from nlm_mcp.config import Settings
from nlm_mcp.server import create_server
from nlm_mcp.tools.common import (
    args_hash,
    require_confirmation,
    run_resource,
    run_tool,
    stable_id,
    stable_title,
    to_plain,
)

EXPECTED_CORE_TOOLS = {
    "admin_health",
    "admin_version",
    "notebook_list",
    "notebook_create",
    "notebook_get",
    "notebook_rename",
    "notebook_delete",
    "notebook_share_public",
    "notebook_share_invite",
    "notebook_share_status",
    "source_add_url",
    "source_add_youtube",
    "source_add_file",
    "source_add_gdrive",
    "source_add_text",
    "source_list",
    "source_get",
    "source_get_fulltext",
    "source_refresh",
    "source_wait",
    "source_remove",
    "chat_ask",
    "chat_query",
    "chat_stream_query",
    "chat_conversation_start",
    "chat_continue",
    "chat_history",
    "chat_save_note",
    "chat_list_notes",
    "chat_save_to_notes",
    "search",
    "fetch",
}
CHAT_HISTORY_LIMIT = 5


class FakeBackend:
    """Offline NotebookLM backend used by core tool tests."""

    def __init__(self) -> None:
        self.notebooks = [
            {"id": "nb-1", "title": "Alpha Notebook", "owner": "user@example.test"},
            {"id": "nb-2", "title": "Beta Notebook", "owner": "user@example.test"},
        ]
        self.sources = {
            "nb-1": [
                {"id": "src-1", "title": "Alpha Source", "fresh": True},
                {"id": "src-2", "title": "Beta Source", "fresh": True},
            ],
            "nb-2": [
                {"id": "src-3", "title": "Beta Source", "fresh": True},
            ],
        }

    async def list_notebooks(self) -> list[dict[str, Any]]:
        return self.notebooks

    async def create_notebook(self, title: str) -> dict[str, str]:
        return {"id": "nb-new", "title": title}

    async def get_notebook(self, notebook_id: str) -> dict[str, str]:
        return {"id": notebook_id, "title": "Alpha Notebook"}

    async def rename_notebook(self, notebook_id: str, title: str) -> dict[str, str]:
        return {"id": notebook_id, "title": title}

    async def delete_notebook(self, notebook_id: str) -> bool:
        return notebook_id == "nb-1"

    async def share_public(self, notebook_id: str, public: bool) -> dict[str, Any]:
        return {"notebook_id": notebook_id, "public": public}

    async def share_invite(
        self,
        notebook_id: str,
        email: str,
        *,
        role: str = "viewer",
        notify: bool = True,
        welcome_message: str = "",
    ) -> dict[str, Any]:
        return {
            "notebook_id": notebook_id,
            "email": email,
            "role": role,
            "notify": notify,
            "welcome_message": welcome_message,
        }

    async def share_status(self, notebook_id: str) -> dict[str, Any]:
        return {"notebook_id": notebook_id, "public": False, "collaborators": []}

    async def list_sources(self, notebook_id: str) -> list[dict[str, Any]]:
        assert notebook_id
        return self.sources.get(notebook_id, [])

    async def get_source(self, notebook_id: str, source_id: str) -> dict[str, Any]:
        return {"id": source_id, "notebook_id": notebook_id, "title": "Alpha Source"}

    async def get_source_fulltext(self, notebook_id: str, source_id: str) -> dict[str, str]:
        if source_id == "empty":
            return {"notebook_id": notebook_id, "source_id": source_id, "text": ""}
        return {"notebook_id": notebook_id, "source_id": source_id, "text": "indexed text"}

    async def add_url_source(
        self,
        notebook_id: str,
        url: str,
        *,
        wait: bool = False,
    ) -> dict[str, Any]:
        return {"id": "src-url", "notebook_id": notebook_id, "url": url, "wait": wait}

    async def add_youtube_source(
        self,
        notebook_id: str,
        url: str,
        *,
        wait: bool = False,
    ) -> dict[str, Any]:
        return {"id": "src-yt", "notebook_id": notebook_id, "url": url, "wait": wait}

    async def add_file_source(
        self,
        notebook_id: str,
        file_path: str,
        *,
        mime_type: str | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        return {
            "id": "src-file",
            "notebook_id": notebook_id,
            "file_path": file_path,
            "mime_type": mime_type,
            "wait": wait,
        }

    async def add_drive_source(
        self,
        notebook_id: str,
        file_id: str,
        title: str,
        *,
        mime_type: str = "application/vnd.google-apps.document",
        wait: bool = False,
    ) -> dict[str, Any]:
        return {
            "id": "src-drive",
            "notebook_id": notebook_id,
            "file_id": file_id,
            "title": title,
            "mime_type": mime_type,
            "wait": wait,
        }

    async def add_text_source(
        self,
        notebook_id: str,
        title: str,
        content: str,
        *,
        wait: bool = False,
    ) -> dict[str, Any]:
        return {
            "id": "src-text",
            "notebook_id": notebook_id,
            "title": title,
            "content": content,
            "wait": wait,
        }

    async def refresh_source(self, notebook_id: str, source_id: str) -> dict[str, str]:
        return {"notebook_id": notebook_id, "source_id": source_id, "status": "refreshing"}

    async def remove_source(self, notebook_id: str, source_id: str) -> bool:
        return notebook_id == "nb-1" and source_id == "src-1"

    async def ask(
        self,
        notebook_id: str,
        question: str,
        *,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "notebook_id": notebook_id,
            "answer": f"answer: {question}",
            "source_ids": source_ids or [],
            "conversation_id": "conv-from-answer" if question == "Start?" else conversation_id,
            "citations": [],
        }

    async def get_conversation_id(self, notebook_id: str) -> str:
        assert notebook_id
        return "conv-1"

    async def get_chat_history(
        self,
        notebook_id: str,
        *,
        limit: int = 100,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "notebook_id": notebook_id,
                "conversation_id": conversation_id,
                "limit": limit,
                "question": "Question",
                "answer": "Answer",
            }
        ]

    async def save_note(self, notebook_id: str, title: str, content: str) -> dict[str, str]:
        return {"id": "note-1", "notebook_id": notebook_id, "title": title, "content": content}

    async def list_notes(self, notebook_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [{"id": "note-1", "notebook_id": notebook_id, "limit": limit}]


def _fake_server() -> Any:
    return create_server(Settings(), backend=cast(NotebookLMBackend, FakeBackend()))


async def test_core_tools_are_registered_with_annotations() -> None:
    async with Client(_fake_server()) as client:
        tools = await client.list_tools()

    by_name = {tool.name: tool for tool in tools}
    assert EXPECTED_CORE_TOOLS.issubset(by_name)
    assert by_name["search"].annotations is not None
    assert by_name["search"].annotations.readOnlyHint is True
    assert by_name["fetch"].annotations is not None
    assert by_name["fetch"].annotations.readOnlyHint is True
    assert by_name["notebook_delete"].annotations is not None
    assert by_name["notebook_delete"].annotations.destructiveHint is True
    assert by_name["source_remove"].annotations is not None
    assert by_name["source_remove"].annotations.destructiveHint is True
    assert by_name["notebook_share_invite"].annotations is not None
    assert by_name["notebook_share_invite"].annotations.destructiveHint is True


async def test_notebook_source_and_chat_tools_use_backend() -> None:
    async with Client(_fake_server()) as client:
        notebooks = await client.call_tool("notebook_list", {})
        renamed = await client.call_tool(
            "notebook_rename",
            {"notebook_id": "nb-1", "title": "Renamed"},
        )
        source = await client.call_tool(
            "source_add_text",
            {"notebook_id": "nb-1", "title": "Notes", "content": "Body"},
        )
        answer = await client.call_tool(
            "chat_ask",
            {"notebook_id": "nb-1", "question": "What changed?"},
        )

    assert notebooks.data["notebooks"][0]["id"] == "nb-1"
    assert renamed.data["result"]["title"] == "Renamed"
    assert source.data["result"]["id"] == "src-text"
    assert answer.data["result"]["answer"] == "answer: What changed?"


async def test_remaining_notebook_tools_use_backend() -> None:
    async with Client(_fake_server()) as client:
        created = await client.call_tool("notebook_create", {"title": "New"})
        fetched = await client.call_tool("notebook_get", {"notebook_id": "nb-1"})
        public = await client.call_tool(
            "notebook_share_public",
            {"notebook_id": "nb-1", "public": True, "confirm": True},
        )
        invited = await client.call_tool(
            "notebook_share_invite",
            {
                "notebook_id": "nb-1",
                "email": "reader@example.test",
                "role": "editor",
                "notify": False,
                "welcome_message": "Review notes",
                "confirm": True,
            },
        )
        status = await client.call_tool("notebook_share_status", {"notebook_id": "nb-1"})

    assert created.data["result"] == {"id": "nb-new", "title": "New"}
    assert fetched.data["result"]["id"] == "nb-1"
    assert public.data["result"]["public"] is True
    assert invited.data["result"]["role"] == "editor"
    assert status.data["result"]["collaborators"] == []


async def test_remaining_source_tools_use_backend() -> None:
    async with Client(_fake_server()) as client:
        url = await client.call_tool(
            "source_add_url",
            {"notebook_id": "nb-1", "url": "https://example.com/article", "wait": True},
        )
        youtube = await client.call_tool(
            "source_add_youtube",
            {"notebook_id": "nb-1", "url": "https://youtube.com/watch?v=abc123"},
        )
        file_source = await client.call_tool(
            "source_add_file",
            {"notebook_id": "nb-1", "file_path": "source_pdf", "mime_type": "application/pdf"},
        )
        drive = await client.call_tool(
            "source_add_gdrive",
            {"notebook_id": "nb-1", "file_id": "drive-1", "title": "Drive Doc"},
        )
        listed = await client.call_tool("source_list", {"notebook_id": "nb-1"})
        source = await client.call_tool(
            "source_get",
            {"notebook_id": "nb-1", "source_id": "src-1"},
        )
        fulltext = await client.call_tool(
            "source_get_fulltext",
            {"notebook_id": "nb-1", "source_id": "src-1"},
        )
        refreshed = await client.call_tool(
            "source_refresh",
            {"notebook_id": "nb-1", "source_id": "src-1"},
        )
        waited = await client.call_tool(
            "source_wait",
            {"notebook_id": "nb-1", "source_id": "src-1", "poll_interval_sec": 1},
        )

    assert url.data["result"]["id"] == "src-url"
    assert url.data["result"]["url"] == "https://example.com/article"
    assert youtube.data["result"]["id"] == "src-yt"
    assert file_source.data["result"]["mime_type"] == "application/pdf"
    assert drive.data["result"]["file_id"] == "drive-1"
    assert listed.data["sources"][0]["id"] == "src-1"
    assert source.data["result"]["title"] == "Alpha Source"
    assert fulltext.data["result"]["text"] == "indexed text"
    assert refreshed.data["result"]["status"] == "refreshing"
    assert waited.data["source"]["id"] == "src-1"


async def test_remaining_chat_tools_use_backend() -> None:
    async with Client(_fake_server()) as client:
        started = await client.call_tool(
            "chat_conversation_start",
            {"notebook_id": "nb-1", "name": "Study", "initial_question": "Start?"},
        )
        continued = await client.call_tool(
            "chat_continue",
            {"notebook_id": "nb-1", "question": "Next?", "conversation_id": "conv-1"},
        )
        history = await client.call_tool(
            "chat_history",
            {"notebook_id": "nb-1", "limit": CHAT_HISTORY_LIMIT, "conversation_id": "conv-1"},
        )
        note = await client.call_tool(
            "chat_save_to_notes",
            {"notebook_id": "nb-1", "title": "Saved", "content": "Answer"},
        )
        alias_answer = await client.call_tool(
            "chat_query",
            {"notebook_id": "nb-1", "question": "Alias?"},
        )
        stream_answer = await client.call_tool(
            "chat_stream_query",
            {"notebook_id": "nb-1", "question": "Stream?"},
        )
        alias_note = await client.call_tool(
            "chat_save_note",
            {"notebook_id": "nb-1", "title": "Saved", "content": "Answer"},
        )
        notes = await client.call_tool(
            "chat_list_notes",
            {"notebook_id": "nb-1", "limit": CHAT_HISTORY_LIMIT},
        )

    assert started.data["conversation_id"] == "conv-from-answer"
    assert started.data["initial_result"]["answer"] == "answer: Start?"
    assert continued.data["result"]["conversation_id"] == "conv-1"
    assert history.data["history"][0]["limit"] == CHAT_HISTORY_LIMIT
    assert note.data["result"]["id"] == "note-1"
    assert alias_answer.data["result"]["answer"] == "answer: Alias?"
    assert stream_answer.data["result"]["answer"] == "answer: Stream?"
    assert alias_note.data["result"]["id"] == "note-1"
    assert notes.data["notes"][0]["limit"] == CHAT_HISTORY_LIMIT


async def test_destructive_tools_require_confirmation() -> None:
    async with Client(_fake_server()) as client:
        with pytest.raises(ToolError, match="Confirmation required"):
            await client.call_tool("notebook_delete", {"notebook_id": "nb-1"})
        with pytest.raises(ToolError, match="Confirmation required"):
            await client.call_tool(
                "notebook_share_public",
                {"notebook_id": "nb-1", "public": True},
            )
        with pytest.raises(ToolError, match="Confirmation required"):
            await client.call_tool(
                "notebook_share_invite",
                {"notebook_id": "nb-1", "email": "reader@example.test"},
            )
        with pytest.raises(ToolError, match="email"):
            await client.call_tool(
                "notebook_share_invite",
                {"notebook_id": "nb-1", "email": "not-an-email", "confirm": True},
            )
        deleted = await client.call_tool(
            "notebook_delete",
            {"notebook_id": "nb-1", "confirm": True},
        )
        with pytest.raises(ToolError, match="Confirmation required"):
            await client.call_tool(
                "source_remove",
                {"notebook_id": "nb-1", "source_id": "src-1"},
            )
        removed = await client.call_tool(
            "source_remove",
            {"notebook_id": "nb-1", "source_id": "src-1", "confirm": True},
        )

    assert deleted.data == {"deleted": True, "notebook_id": "nb-1"}
    assert removed.data == {"removed": True, "notebook_id": "nb-1", "source_id": "src-1"}


async def test_search_and_fetch_return_openai_compatible_shapes() -> None:
    async with Client(_fake_server()) as client:
        search = await client.call_tool("search", {"query": "alpha", "limit": 10})
        limited = await client.call_tool("search", {"query": "", "limit": 1})
        notebook = await client.call_tool("fetch", {"id": "notebook:nb-1"})
        fetched = await client.call_tool("fetch", {"id": "source:nb-1:src-1"})
        empty = await client.call_tool("fetch", {"id": "source:nb-1:empty"})
        with pytest.raises(ToolError, match="Notebook record id"):
            await client.call_tool("fetch", {"id": "notebook:"})
        with pytest.raises(ToolError, match="Unsupported record id"):
            await client.call_tool("fetch", {"id": "unknown:record"})
        with pytest.raises(ToolError, match="Source record id"):
            await client.call_tool("fetch", {"id": "source:nb-1"})

    assert search.data == {"ids": ["notebook:nb-1", "source:nb-1:src-1"]}
    assert limited.data == {"ids": ["notebook:nb-1"]}
    assert notebook.data["metadata"]["kind"] == "notebook"
    assert notebook.data["content"] == '{"id": "nb-1", "title": "Alpha Notebook"}'
    assert fetched.data["id"] == "source:nb-1:src-1"
    assert fetched.data["title"] == "Alpha Source"
    assert fetched.data["content"] == "indexed text"
    assert fetched.data["metadata"]["kind"] == "source"
    assert empty.data["content"] == ""


async def test_core_resources_are_registered_and_resolve() -> None:
    async with Client(_fake_server()) as client:
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        notebooks = await client.read_resource("notebooklm://notebooks")
        notebook = await client.read_resource("notebooklm://notebook/nb-1")
        fulltext = await client.read_resource("notebooklm://notebook/nb-1/source/src-1/fulltext")

    assert {str(resource.uri) for resource in resources} == {"notebooklm://notebooks"}
    assert {
        "notebooklm://notebook/{id}",
        "notebooklm://notebook/{id}/source/{src_id}",
        "notebooklm://notebook/{id}/source/{src_id}/fulltext",
    }.issubset({template.uriTemplate for template in templates})
    assert json.loads(notebooks[0].text)["notebooks"][0]["id"] == "nb-1"
    assert json.loads(notebook[0].text)["notebook"]["id"] == "nb-1"
    assert json.loads(fulltext[0].text)["fulltext"]["text"] == "indexed text"


async def test_common_helpers_cover_conversion_and_error_paths() -> None:
    class SampleEnum(Enum):
        VALUE = "value"

    @dataclass
    class SampleRecord:
        id: str
        title: str

    class SampleObject:
        def __init__(self) -> None:
            self.id = "object-1"
            self.title = "Object"
            self._private = "hidden"

    async def ok_tool() -> dict[str, bool]:
        return {"ok": True}

    async def backend_error() -> dict[str, bool]:
        raise BackendValidationError("Invalid input.", error_code=-32602)

    async def unexpected_error() -> dict[str, bool]:
        raise RuntimeError("internal")

    assert to_plain(SampleRecord(id="record-1", title="Record")) == {
        "id": "record-1",
        "title": "Record",
    }
    assert to_plain(SampleEnum.VALUE) == "value"
    assert to_plain(SampleObject()) == {"id": "object-1", "title": "Object"}
    assert stable_id({"source_id": "src-1"}) == "src-1"
    assert stable_id({"slug": "fallback"}, "slug") == "fallback"
    assert stable_id({"no_id": "value"})
    assert stable_title({"display_name": "Display"}) == "Display"
    assert stable_title({"other": "value"}, default="Default") == "Default"
    assert args_hash({"a": 1})
    assert await run_tool("tool_ok", {}, ok_tool) == {"ok": True}
    with pytest.raises(ToolError, match="Invalid input"):
        await run_tool("tool_backend_error", {}, backend_error)
    with pytest.raises(ToolError, match="NotebookLM tool execution failed"):
        await run_tool("tool_unexpected_error", {}, unexpected_error)
    with pytest.raises(BackendValidationError):
        require_confirmation(False, "testing")
    require_confirmation(True, "testing")


async def test_resource_helper_maps_errors() -> None:
    async def ok_resource() -> str:
        return "ok"

    async def backend_error() -> str:
        raise BackendValidationError("Resource invalid.", error_code=-32602)

    async def unexpected_error() -> str:
        raise RuntimeError("internal")

    assert await run_resource("notebooklm://ok", ok_resource) == "ok"
    with pytest.raises(ResourceError, match="Resource invalid"):
        await run_resource("notebooklm://backend-error", backend_error)
    with pytest.raises(ResourceError, match="NotebookLM resource read failed"):
        await run_resource("notebooklm://unexpected-error", unexpected_error)
