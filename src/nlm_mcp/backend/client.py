"""Async NotebookLM backend wrapper."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeVar

from notebooklm import NotebookLMClient

from nlm_mcp.backend.exceptions import BackendAuthError, BackendError, map_backend_exception
from nlm_mcp.backend.retry import SleepCallback, is_retryable_exception, run_with_retry
from nlm_mcp.config import Settings

T = TypeVar("T")
ClientFactory = Callable[[Settings], Awaitable[Any]]
_AUTH_ENV_LOCK = asyncio.Lock()
DEFAULT_NOTEBOOKLM_AUTH_FILE = Path("~/.config/nlm-mcp/notebooklm_auth.json").expanduser()


@dataclass(frozen=True)
class AuthSource:
    """Resolved NotebookLM authentication source."""

    kind: Literal["env_json", "file", "default"]
    value: str


def resolve_auth_source(settings: Settings) -> AuthSource:
    """Resolve NotebookLM auth JSON or storage file configuration."""
    if settings.notebooklm_auth_json is not None:
        auth_json = settings.notebooklm_auth_json.get_secret_value().strip()
        if auth_json:
            return AuthSource(kind="env_json", value=auth_json)

    auth_file = settings.notebooklm_auth_file.expanduser()
    if auth_file.exists():
        return AuthSource(kind="file", value=str(auth_file))
    if auth_file == DEFAULT_NOTEBOOKLM_AUTH_FILE:
        return AuthSource(kind="default", value="")
    raise BackendAuthError(
        "NotebookLM auth file not found.",
        error_code=-32002,
        data={"auth_source": "file"},
    )


@contextmanager
def _temporary_env(name: str, value: str) -> Iterator[None]:
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


async def create_notebooklm_client(settings: Settings, *, timeout: float = 30.0) -> Any:
    """Create an unopened notebooklm-py client from configured auth."""
    auth_source = resolve_auth_source(settings)
    if auth_source.kind == "env_json":
        async with _AUTH_ENV_LOCK:
            with _temporary_env("NOTEBOOKLM_AUTH_JSON", auth_source.value):
                return await NotebookLMClient.from_storage(path=None, timeout=timeout)
    if auth_source.kind == "default":
        return await NotebookLMClient.from_storage(path=None, timeout=timeout)
    return await NotebookLMClient.from_storage(path=auth_source.value, timeout=timeout)


class NotebookLMBackend:
    """Thin async wrapper around notebooklm-py with retry and error mapping."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client_factory: ClientFactory | None = None,
        retry_wait_strategy: Any | None = None,
        retry_sleep: SleepCallback | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self._client_factory = client_factory or create_notebooklm_client
        self._retry_wait_strategy = retry_wait_strategy
        self._retry_sleep = retry_sleep
        self._client: Any | None = None
        self._client_context: Any | None = None
        self._connect_lock = asyncio.Lock()

    async def __aenter__(self) -> NotebookLMBackend:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.close()

    async def connect(self) -> Any:
        """Create and enter the underlying notebooklm-py client if needed."""
        try:
            return await self._connect_unmapped()
        except Exception as exc:
            raise map_backend_exception(exc) from exc

    async def _connect_unmapped(self) -> Any:
        """Create and enter the underlying client without mapping exceptions."""
        if self._client is not None:
            return self._client
        async with self._connect_lock:
            if self._client is not None:
                return self._client
            context: Any | None = None
            try:
                raw_client = await self._client_factory(self.settings)
                enter = getattr(raw_client, "__aenter__", None)
                if enter is not None:
                    context = raw_client
                    client = await enter()
                    self._client_context = context
                    self._client = client
                else:
                    self._client = raw_client
            except Exception as exc:
                if context is not None:
                    exit_method = getattr(context, "__aexit__", None)
                    if exit_method is not None:
                        with suppress(Exception):
                            await exit_method(type(exc), exc, exc.__traceback__)
                self._client = None
                self._client_context = None
                raise
            return self._client

    async def close(self) -> None:
        """Close the underlying notebooklm-py client if it was opened."""
        async with self._connect_lock:
            context = self._client_context
            self._client = None
            self._client_context = None
            if context is not None:
                exit_method = getattr(context, "__aexit__", None)
                if exit_method is not None:
                    with suppress(Exception):
                        await exit_method(None, None, None)

    async def _call(
        self,
        operation_name: str,
        operation: Callable[[Any], Awaitable[T]],
        *,
        retry: bool = True,
    ) -> T:
        async def invoke() -> T:
            try:
                client = await self._connect_unmapped()
                return await operation(client)
            except Exception as exc:
                if is_retryable_exception(exc):
                    with suppress(Exception):
                        await self.close()
                raise

        try:
            if not retry:
                return await invoke()
            return await run_with_retry(
                invoke,
                operation_name=operation_name,
                wait_strategy=self._retry_wait_strategy,
                sleep=self._retry_sleep,
            )
        except BackendError:
            raise
        except Exception as exc:
            raise map_backend_exception(exc) from exc

    async def list_notebooks(self) -> Any:
        """List NotebookLM notebooks."""
        return await self._call("notebook.list", lambda client: client.notebooks.list())

    async def create_notebook(self, title: str) -> Any:
        """Create a NotebookLM notebook."""
        return await self._call(
            "notebook.create",
            lambda client: client.notebooks.create(title),
            retry=False,
        )

    async def get_notebook(self, notebook_id: str) -> Any:
        """Get NotebookLM notebook metadata."""
        return await self._call(
            "notebook.get",
            lambda client: client.notebooks.get(notebook_id),
        )

    async def rename_notebook(self, notebook_id: str, title: str) -> Any:
        """Rename a NotebookLM notebook."""
        return await self._call(
            "notebook.rename",
            lambda client: client.notebooks.rename(notebook_id, title),
            retry=False,
        )

    async def delete_notebook(self, notebook_id: str) -> Any:
        """Delete a NotebookLM notebook."""
        return await self._call(
            "notebook.delete",
            lambda client: client.notebooks.delete(notebook_id),
            retry=False,
        )

    async def list_sources(self, notebook_id: str) -> Any:
        """List NotebookLM sources in a notebook."""
        return await self._call(
            "source.list",
            lambda client: client.sources.list(notebook_id),
        )

    async def get_source(self, notebook_id: str, source_id: str) -> Any:
        """Get a NotebookLM source."""
        return await self._call(
            "source.get",
            lambda client: client.sources.get(notebook_id, source_id),
        )

    async def get_source_fulltext(self, notebook_id: str, source_id: str) -> Any:
        """Get full text for a NotebookLM source."""
        return await self._call(
            "source.get_fulltext",
            lambda client: client.sources.get_fulltext(notebook_id, source_id),
        )

    async def add_url_source(self, notebook_id: str, url: str, *, wait: bool = False) -> Any:
        """Add a URL source to a NotebookLM notebook."""
        return await self._call(
            "source.add_url",
            lambda client: client.sources.add_url(notebook_id, url, wait=wait),
            retry=False,
        )

    async def add_text_source(
        self,
        notebook_id: str,
        title: str,
        content: str,
        *,
        wait: bool = False,
    ) -> Any:
        """Add a pasted-text source to a NotebookLM notebook."""
        return await self._call(
            "source.add_text",
            lambda client: client.sources.add_text(notebook_id, title, content, wait=wait),
            retry=False,
        )

    async def add_file_source(
        self,
        notebook_id: str,
        file_path: str | Path,
        *,
        mime_type: str | None = None,
        wait: bool = False,
    ) -> Any:
        """Add a file source to a NotebookLM notebook."""
        return await self._call(
            "source.add_file",
            lambda client: client.sources.add_file(
                notebook_id,
                file_path,
                mime_type=mime_type,
                wait=wait,
            ),
            retry=False,
        )

    async def add_drive_source(
        self,
        notebook_id: str,
        file_id: str,
        title: str,
        *,
        mime_type: str = "application/vnd.google-apps.document",
        wait: bool = False,
    ) -> Any:
        """Add a Google Drive source to a NotebookLM notebook."""
        return await self._call(
            "source.add_gdrive",
            lambda client: client.sources.add_drive(
                notebook_id,
                file_id,
                title,
                mime_type=mime_type,
                wait=wait,
            ),
            retry=False,
        )

    async def refresh_source(self, notebook_id: str, source_id: str) -> Any:
        """Refresh a NotebookLM source."""
        return await self._call(
            "source.refresh",
            lambda client: client.sources.refresh(notebook_id, source_id),
        )

    async def remove_source(self, notebook_id: str, source_id: str) -> Any:
        """Remove a NotebookLM source."""
        return await self._call(
            "source.remove",
            lambda client: client.sources.delete(notebook_id, source_id),
            retry=False,
        )

    async def ask(
        self,
        notebook_id: str,
        question: str,
        *,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> Any:
        """Ask a one-shot question against a NotebookLM notebook."""
        return await self._call(
            "chat.ask",
            lambda client: client.chat.ask(
                notebook_id,
                question,
                source_ids=source_ids,
                conversation_id=conversation_id,
            ),
            retry=False,
        )
