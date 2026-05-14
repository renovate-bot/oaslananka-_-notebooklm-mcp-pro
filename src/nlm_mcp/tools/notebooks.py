"""Notebook management tools."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.tools.common import (
    require_confirmation,
    run_tool,
    to_plain,
    tool_annotations,
    tool_public_name,
)
from nlm_mcp.tools.models import (
    ConfirmNotebookInput,
    NotebookCreateInput,
    NotebookIdInput,
    NotebookListInput,
    NotebookRenameInput,
    NotebookShareInviteInput,
    NotebookSharePublicInput,
)

if TYPE_CHECKING:
    from nlm_mcp.backend.client import NotebookLMBackend


def register_notebook_tools(server: FastMCP, backend: NotebookLMBackend) -> None:
    """Register NotebookLM notebook tools."""

    @server.tool(
        name=tool_public_name("notebook.list"),
        title="List Notebooks",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def notebook_list() -> dict[str, Any]:
        """List all notebooks visible to the configured NotebookLM session."""
        payload = NotebookListInput()
        return await run_tool(
            "notebook.list",
            payload,
            lambda: _list_notebooks(backend),
        )

    @server.tool(
        name=tool_public_name("notebook.create"),
        title="Create Notebook",
        annotations=tool_annotations(idempotent=False),
    )
    async def notebook_create(title: str) -> dict[str, Any]:
        """Create a NotebookLM notebook with the supplied title."""
        payload = NotebookCreateInput(title=title)
        return await run_tool(
            "notebook.create",
            payload,
            lambda: _generic_result(backend.create_notebook(payload.title)),
        )

    @server.tool(
        name=tool_public_name("notebook.get"),
        title="Get Notebook",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def notebook_get(notebook_id: str) -> dict[str, Any]:
        """Get metadata for one NotebookLM notebook."""
        payload = NotebookIdInput(notebook_id=notebook_id)
        return await run_tool(
            "notebook.get",
            payload,
            lambda: _generic_result(backend.get_notebook(payload.notebook_id)),
        )

    @server.tool(
        name=tool_public_name("notebook.rename"),
        title="Rename Notebook",
        annotations=tool_annotations(idempotent=True),
    )
    async def notebook_rename(notebook_id: str, title: str) -> dict[str, Any]:
        """Rename one NotebookLM notebook."""
        payload = NotebookRenameInput(notebook_id=notebook_id, title=title)
        return await run_tool(
            "notebook.rename",
            payload,
            lambda: _generic_result(backend.rename_notebook(payload.notebook_id, payload.title)),
        )

    @server.tool(
        name=tool_public_name("notebook.delete"),
        title="Delete Notebook",
        annotations=tool_annotations(destructive=True, idempotent=False),
    )
    async def notebook_delete(notebook_id: str, confirm: bool = False) -> dict[str, Any]:
        """Delete a NotebookLM notebook after explicit confirmation."""
        payload = ConfirmNotebookInput(notebook_id=notebook_id, confirm=confirm)

        async def operation() -> dict[str, Any]:
            require_confirmation(payload.confirm, "deleting a notebook")
            deleted = await backend.delete_notebook(payload.notebook_id)
            return {"deleted": bool(deleted), "notebook_id": payload.notebook_id}

        return await run_tool("notebook.delete", payload, operation)

    @server.tool(
        name=tool_public_name("notebook.share_public"),
        title="Toggle Public Notebook Sharing",
        annotations=tool_annotations(destructive=True, idempotent=True, open_world=True),
    )
    async def notebook_share_public(
        notebook_id: str,
        public: bool,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Toggle public sharing for one NotebookLM notebook."""
        payload = NotebookSharePublicInput(
            notebook_id=notebook_id,
            public=public,
            confirm=confirm,
        )

        async def operation() -> dict[str, Any]:
            if payload.public:
                require_confirmation(payload.confirm, "enabling public notebook sharing")
            return await _generic_result(backend.share_public(payload.notebook_id, payload.public))

        return await run_tool(
            "notebook.share_public",
            payload,
            operation,
        )

    @server.tool(
        name=tool_public_name("notebook.share_invite"),
        title="Invite Notebook Collaborator",
        annotations=tool_annotations(destructive=True, idempotent=False, open_world=True),
    )
    async def notebook_share_invite(
        notebook_id: str,
        email: str,
        role: str = "viewer",
        notify: bool = True,
        welcome_message: str = "",
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Invite an email address to view or edit a NotebookLM notebook."""
        raw_payload = {
            "notebook_id": notebook_id,
            "email": email,
            "role": role,
            "notify": notify,
            "welcome_message": welcome_message,
            "confirm": confirm,
        }

        async def operation() -> dict[str, Any]:
            payload = NotebookShareInviteInput.model_validate(raw_payload)
            require_confirmation(payload.confirm, "sharing a notebook with a collaborator")
            return await _generic_result(
                backend.share_invite(
                    payload.notebook_id,
                    payload.email,
                    role=payload.role,
                    notify=payload.notify,
                    welcome_message=payload.welcome_message,
                )
            )

        return await run_tool(
            "notebook.share_invite",
            raw_payload,
            operation,
        )

    @server.tool(
        name=tool_public_name("notebook.share_status"),
        title="Notebook Sharing Status",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def notebook_share_status(notebook_id: str) -> dict[str, Any]:
        """Return sharing settings for one NotebookLM notebook."""
        payload = NotebookIdInput(notebook_id=notebook_id)
        return await run_tool(
            "notebook.share_status",
            payload,
            lambda: _generic_result(backend.share_status(payload.notebook_id)),
        )


async def _list_notebooks(backend: NotebookLMBackend) -> dict[str, Any]:
    notebooks = await backend.list_notebooks()
    return {"notebooks": to_plain(notebooks)}


async def _generic_result(awaitable: Awaitable[Any]) -> dict[str, Any]:
    return {"result": to_plain(await awaitable)}
