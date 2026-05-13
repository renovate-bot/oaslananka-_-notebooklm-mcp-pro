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
from notebooklm.rpc.types import (
    AudioFormat,
    AudioLength,
    InfographicDetail,
    InfographicOrientation,
    QuizDifficulty,
    QuizQuantity,
    ReportFormat,
    SharePermission,
    SlideDeckFormat,
    SlideDeckLength,
    VideoFormat,
    VideoStyle,
)

from nlm_mcp.backend.exceptions import (
    BackendAuthError,
    BackendError,
    BackendValidationError,
    map_backend_exception,
)
from nlm_mcp.backend.retry import SleepCallback, is_retryable_exception, run_with_retry
from nlm_mcp.config import Settings

T = TypeVar("T")
ClientFactory = Callable[[Settings], Awaitable[Any]]
_AUTH_ENV_LOCK = asyncio.Lock()
DEFAULT_NOTEBOOKLM_AUTH_FILE = Path("~/.config/nlm-mcp/notebooklm_auth.json").expanduser()
ARTIFACT_DOWNLOAD_METHODS = {
    "audio": "download_audio",
    "video": "download_video",
    "infographic": "download_infographic",
    "slide_deck": "download_slide_deck",
    "report": "download_report",
    "mind_map": "download_mind_map",
    "data_table": "download_data_table",
    "quiz": "download_quiz",
    "flashcards": "download_flashcards",
}

ARTIFACT_OUTPUT_FORMATS = {
    "quiz": {"json", "markdown", "html"},
    "flashcards": {"json", "markdown", "html"},
    "slide_deck": {"pdf", "pptx"},
}


def _normalize_output_format(output_format: str | None) -> str | None:
    if output_format == "md":
        return "markdown"
    return output_format


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


def _enum_member(enum_type: Any, value: str | None) -> Any:
    if value is None:
        return None
    member = enum_type.__members__.get(value.upper())
    if member is None:
        raise BackendValidationError(
            "Unsupported NotebookLM option.",
            error_code=-32602,
            data={"enum": getattr(enum_type, "__name__", str(enum_type)), "value": value},
        )
    return member


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

    async def share_public(self, notebook_id: str, public: bool) -> Any:
        """Toggle public sharing for a NotebookLM notebook."""
        return await self._call(
            "notebook.share_public",
            lambda client: client.sharing.set_public(notebook_id, public),
            retry=False,
        )

    async def share_invite(
        self,
        notebook_id: str,
        email: str,
        *,
        role: Literal["viewer", "editor"] = "viewer",
        notify: bool = True,
        welcome_message: str = "",
    ) -> Any:
        """Invite a user to a NotebookLM notebook."""
        if role not in {"viewer", "editor"}:
            raise BackendValidationError(
                "Notebook sharing role must be viewer or editor.",
                error_code=-32602,
                data={"role": role},
            )
        permission_by_role = {
            "viewer": SharePermission.VIEWER,
            "editor": SharePermission.EDITOR,
        }
        return await self._call(
            "notebook.share_invite",
            lambda client: client.sharing.add_user(
                notebook_id,
                email,
                permission=permission_by_role[role],
                notify=notify,
                welcome_message=welcome_message,
            ),
            retry=False,
        )

    async def share_status(self, notebook_id: str) -> Any:
        """Get NotebookLM notebook sharing status."""
        return await self._call(
            "notebook.share_status",
            lambda client: client.sharing.get_status(notebook_id),
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

    async def add_youtube_source(self, notebook_id: str, url: str, *, wait: bool = False) -> Any:
        """Add a YouTube URL source to a NotebookLM notebook."""

        async def operation(client: Any) -> Any:
            add_youtube = getattr(client.sources, "add_youtube", None)
            if add_youtube is not None:
                return await add_youtube(notebook_id, url, wait=wait)
            return await client.sources.add_url(notebook_id, url, wait=wait)

        return await self._call("source.add_youtube", operation, retry=False)

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

    async def get_conversation_id(self, notebook_id: str) -> Any:
        """Return NotebookLM's current conversation id for a notebook."""
        return await self._call(
            "chat.conversation_start",
            lambda client: client.chat.get_conversation_id(notebook_id),
        )

    async def get_chat_history(
        self,
        notebook_id: str,
        *,
        limit: int = 100,
        conversation_id: str | None = None,
    ) -> Any:
        """Get chat history for a NotebookLM notebook."""
        return await self._call(
            "chat.history",
            lambda client: client.chat.get_history(
                notebook_id,
                limit=limit,
                conversation_id=conversation_id,
            ),
        )

    async def save_note(self, notebook_id: str, title: str, content: str) -> Any:
        """Save content as a NotebookLM note."""
        return await self._call(
            "chat.save_to_notes",
            lambda client: client.notes.create(notebook_id, title=title, content=content),
            retry=False,
        )

    async def list_notes(self, notebook_id: str, *, limit: int = 100) -> Any:
        """List saved NotebookLM notes for a notebook."""
        return await self._call(
            "chat.list_notes",
            lambda client: client.notes.list(notebook_id, limit=limit),
        )

    async def start_research(
        self,
        notebook_id: str,
        query: str,
        *,
        source: Literal["web", "drive"] = "web",
        mode: Literal["fast", "deep"] = "fast",
    ) -> Any:
        """Start a NotebookLM research task."""
        return await self._call(
            f"research.{source}_start",
            lambda client: client.research.start(notebook_id, query, source=source, mode=mode),
            retry=False,
        )

    async def research_status(self, notebook_id: str) -> Any:
        """Poll the latest NotebookLM research task for a notebook."""
        return await self._call(
            "research.status",
            lambda client: client.research.poll(notebook_id),
        )

    async def import_research_sources(
        self,
        notebook_id: str,
        task_id: str,
        sources: list[dict[str, Any]],
    ) -> Any:
        """Import selected research sources into a NotebookLM notebook."""
        return await self._call(
            "research.import_sources",
            lambda client: client.research.import_sources(notebook_id, task_id, sources),
            retry=False,
        )

    async def generate_audio_overview(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        audio_format: str = "deep_dive",
        audio_length: str = "default",
    ) -> Any:
        """Generate an audio overview artifact."""
        return await self._call(
            "generate.audio_overview",
            lambda client: client.artifacts.generate_audio(
                notebook_id,
                source_ids=source_ids,
                language=language,
                instructions=instructions,
                audio_format=_enum_member(AudioFormat, audio_format),
                audio_length=_enum_member(AudioLength, audio_length),
            ),
            retry=False,
        )

    async def generate_video_overview(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        video_format: str = "explainer",
        video_style: str = "auto_select",
    ) -> Any:
        """Generate a video overview artifact."""
        return await self._call(
            "generate.video_overview",
            lambda client: client.artifacts.generate_video(
                notebook_id,
                source_ids=source_ids,
                language=language,
                instructions=instructions,
                video_format=_enum_member(VideoFormat, video_format),
                video_style=_enum_member(VideoStyle, video_style),
            ),
            retry=False,
        )

    async def generate_cinematic_video(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
    ) -> Any:
        """Generate a cinematic video artifact via notebooklm-py's video API."""
        return await self._call(
            "generate.cinematic_video",
            lambda client: client.artifacts.generate_video(
                notebook_id,
                source_ids=source_ids,
                language=language,
                instructions=instructions,
            ),
            retry=False,
        )

    async def generate_slide_deck(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        slide_format: str = "detailed_deck",
        slide_length: str = "default",
    ) -> Any:
        """Generate a slide deck artifact."""
        return await self._call(
            "generate.slide_deck",
            lambda client: client.artifacts.generate_slide_deck(
                notebook_id,
                source_ids=source_ids,
                language=language,
                instructions=instructions,
                slide_format=_enum_member(SlideDeckFormat, slide_format),
                slide_length=_enum_member(SlideDeckLength, slide_length),
            ),
            retry=False,
        )

    async def generate_infographic(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        orientation: str = "landscape",
        detail_level: str = "standard",
    ) -> Any:
        """Generate an infographic artifact."""
        return await self._call(
            "generate.infographic",
            lambda client: client.artifacts.generate_infographic(
                notebook_id,
                source_ids=source_ids,
                language=language,
                instructions=instructions,
                orientation=_enum_member(InfographicOrientation, orientation),
                detail_level=_enum_member(InfographicDetail, detail_level),
            ),
            retry=False,
        )

    async def generate_quiz(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        instructions: str | None = None,
        quantity: str = "standard",
        difficulty: str = "medium",
    ) -> Any:
        """Generate a quiz artifact."""
        return await self._call(
            "generate.quiz",
            lambda client: client.artifacts.generate_quiz(
                notebook_id,
                source_ids=source_ids,
                instructions=instructions,
                quantity=_enum_member(QuizQuantity, quantity),
                difficulty=_enum_member(QuizDifficulty, difficulty),
            ),
            retry=False,
        )

    async def generate_flashcards(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        instructions: str | None = None,
        quantity: str = "standard",
        difficulty: str = "medium",
    ) -> Any:
        """Generate flashcard artifacts."""
        return await self._call(
            "generate.flashcards",
            lambda client: client.artifacts.generate_flashcards(
                notebook_id,
                source_ids=source_ids,
                instructions=instructions,
                quantity=_enum_member(QuizQuantity, quantity),
                difficulty=_enum_member(QuizDifficulty, difficulty),
            ),
            retry=False,
        )

    async def generate_report(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        report_format: str = "briefing_doc",
        custom_prompt: str | None = None,
        extra_instructions: str | None = None,
    ) -> Any:
        """Generate a report artifact."""
        return await self._call(
            "generate.report",
            lambda client: client.artifacts.generate_report(
                notebook_id,
                report_format=_enum_member(ReportFormat, report_format),
                source_ids=source_ids,
                language=language,
                custom_prompt=custom_prompt,
                extra_instructions=extra_instructions,
            ),
            retry=False,
        )

    async def generate_data_table(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
    ) -> Any:
        """Generate a data table artifact."""
        return await self._call(
            "generate.data_table",
            lambda client: client.artifacts.generate_data_table(
                notebook_id,
                source_ids=source_ids,
                language=language,
                instructions=instructions,
            ),
            retry=False,
        )

    async def generate_mind_map(
        self,
        notebook_id: str,
        *,
        source_ids: list[str] | None = None,
    ) -> Any:
        """Generate a mind map artifact."""
        return await self._call(
            "generate.mind_map",
            lambda client: client.artifacts.generate_mind_map(
                notebook_id,
                source_ids=source_ids,
            ),
            retry=False,
        )

    async def artifact_status(self, notebook_id: str, task_id: str) -> Any:
        """Poll a NotebookLM artifact task."""
        return await self._call(
            "artifact.status",
            lambda client: client.artifacts.poll_status(notebook_id, task_id),
        )

    async def artifact_wait(
        self,
        notebook_id: str,
        task_id: str,
        *,
        initial_interval: float,
        max_interval: float,
        timeout: float,
    ) -> Any:
        """Wait for a NotebookLM artifact task to complete."""
        return await self._call(
            "artifact.wait",
            lambda client: client.artifacts.wait_for_completion(
                notebook_id,
                task_id,
                initial_interval=initial_interval,
                max_interval=max_interval,
                timeout=timeout,
            ),
        )

    async def artifact_list(self, notebook_id: str, artifact_type: str | None = None) -> Any:
        """List NotebookLM artifacts for a notebook."""

        async def operation(client: Any) -> Any:
            if artifact_type is None:
                return await client.artifacts.list(notebook_id)
            from notebooklm.types import ArtifactType  # noqa: PLC0415

            return await client.artifacts.list(notebook_id, ArtifactType(artifact_type))

        return await self._call("artifact.list", operation)

    async def artifact_download(
        self,
        notebook_id: str,
        artifact_type: str,
        output_path: str,
        *,
        artifact_id: str | None = None,
        output_format: str | None = None,
    ) -> Any:
        """Download a NotebookLM artifact to a local path."""
        if artifact_type not in ARTIFACT_DOWNLOAD_METHODS:
            raise BackendValidationError(
                "Unsupported artifact type.",
                error_code=-32602,
                data={"artifact_type": artifact_type},
            )
        normalized_format = _normalize_output_format(output_format)
        allowed_formats = ARTIFACT_OUTPUT_FORMATS.get(artifact_type)
        if normalized_format is not None and normalized_format not in (allowed_formats or set()):
            raise BackendValidationError(
                "Unsupported artifact output format.",
                error_code=-32602,
                data={"artifact_type": artifact_type, "output_format": output_format},
            )

        async def operation(client: Any) -> Any:
            method = getattr(client.artifacts, ARTIFACT_DOWNLOAD_METHODS[artifact_type])
            if normalized_format is not None:
                return await method(
                    notebook_id,
                    output_path,
                    artifact_id=artifact_id,
                    output_format=normalized_format,
                )
            return await method(notebook_id, output_path, artifact_id=artifact_id)

        return await self._call("artifact.download", operation)

    async def artifact_delete(self, notebook_id: str, artifact_id: str) -> Any:
        """Delete a generated NotebookLM artifact when supported by notebooklm-py."""

        async def operation(client: Any) -> Any:
            method = getattr(client.artifacts, "delete", None)
            if method is None:
                raise BackendValidationError(
                    "Artifact deletion is not supported by the installed notebooklm-py backend.",
                    error_code=-32602,
                    data={"artifact_id": artifact_id},
                )
            return await method(notebook_id, artifact_id)

        return await self._call("artifact.delete", operation, retry=False)

    async def artifact_cancel(self, notebook_id: str, task_id: str) -> Any:
        """Cancel a generated NotebookLM artifact task when supported by notebooklm-py."""

        async def operation(client: Any) -> Any:
            for method_name in ("cancel", "cancel_task"):
                method = getattr(client.artifacts, method_name, None)
                if method is not None:
                    return await method(notebook_id, task_id)
            raise BackendValidationError(
                "Artifact cancellation is not supported by the installed notebooklm-py backend.",
                error_code=-32602,
                data={"task_id": task_id},
            )

        return await self._call("artifact.cancel", operation, retry=False)

    async def revise_slide(
        self,
        notebook_id: str,
        artifact_id: str,
        slide_index: int,
        prompt: str,
    ) -> Any:
        """Revise a slide in a generated slide deck."""
        return await self._call(
            "artifact.revise_slide",
            lambda client: client.artifacts.revise_slide(
                notebook_id,
                artifact_id,
                slide_index,
                prompt,
            ),
            retry=False,
        )

    async def get_language(self) -> Any:
        """Get the global NotebookLM output language."""
        return await self._call(
            "language.get",
            lambda client: client.settings.get_output_language(),
        )

    async def set_language(self, language: str) -> Any:
        """Set the global NotebookLM output language."""
        return await self._call(
            "language.set",
            lambda client: client.settings.set_output_language(language),
            retry=False,
        )
