from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from notebooklm import RateLimitError
from pydantic import SecretStr
from pytest import MonkeyPatch, raises
from tenacity import wait_none

import nlm_mcp.backend.client as client_module
from nlm_mcp.backend.client import AuthSource, NotebookLMBackend, resolve_auth_source
from nlm_mcp.backend.exceptions import (
    BackendAuthError,
    BackendRateLimitError,
    BackendTimeoutError,
    BackendValidationError,
)
from nlm_mcp.config import Settings

AUTH_ERROR_CODE = -32002
VALIDATION_ERROR_CODE = -32602
MAX_RETRY_ATTEMPTS = 5
EXPECTED_RECONNECT_CLIENTS = 2
EXPECTED_VIDEO_GENERATE_CALLS = 2
RETRY_AFTER_SECONDS = 3


async def _no_sleep(_delay: float) -> None:
    return None


class FakeNotebooksAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.error: Exception | None = None
        self.create_error: Exception | None = None

    async def list(self) -> list[dict[str, str]]:
        self.calls.append(("list", ()))
        if self.error is not None:
            raise self.error
        return [{"id": "nb-1", "title": "Notebook"}]

    async def create(self, title: str) -> dict[str, str]:
        self.calls.append(("create", (title,)))
        if self.create_error is not None:
            raise self.create_error
        return {"id": "nb-2", "title": title}

    async def get(self, notebook_id: str) -> dict[str, str]:
        self.calls.append(("get", (notebook_id,)))
        return {"id": notebook_id, "title": "Notebook"}

    async def rename(self, notebook_id: str, new_title: str) -> dict[str, str]:
        self.calls.append(("rename", (notebook_id, new_title)))
        return {"id": notebook_id, "title": new_title}

    async def delete(self, notebook_id: str) -> bool:
        self.calls.append(("delete", (notebook_id,)))
        return True


class FakeSourcesAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def list(self, notebook_id: str) -> list[dict[str, str]]:
        self.calls.append(("list", (notebook_id,)))
        return [{"id": "src-1", "title": "Source"}]

    async def add_url(self, notebook_id: str, url: str, wait: bool = False) -> dict[str, str]:
        self.calls.append(("add_url", (notebook_id, url, wait)))
        return {"id": "src-2", "title": url}

    async def add_youtube(self, notebook_id: str, url: str, wait: bool = False) -> dict[str, str]:
        self.calls.append(("add_youtube", (notebook_id, url, wait)))
        return {"id": "src-youtube", "title": url}

    async def get_fulltext(self, notebook_id: str, source_id: str) -> dict[str, str]:
        self.calls.append(("get_fulltext", (notebook_id, source_id)))
        return {"source_id": source_id, "text": "full text"}


class FakeChatAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.error: Exception | None = None

    async def ask(
        self,
        notebook_id: str,
        question: str,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(("ask", (notebook_id, question, source_ids, conversation_id)))
        if self.error is not None:
            raise self.error
        return {"answer": "response", "citations": []}


class FakeResearchAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def start(
        self,
        notebook_id: str,
        query: str,
        *,
        source: str = "web",
        mode: str = "fast",
    ) -> dict[str, Any]:
        self.calls.append(("start", (notebook_id, query), {"source": source, "mode": mode}))
        return {"task_id": "research-1", "source": source, "mode": mode}

    async def poll(self, notebook_id: str) -> dict[str, str]:
        self.calls.append(("poll", (notebook_id,), {}))
        return {"task_id": "research-1", "status": "completed"}

    async def import_sources(
        self,
        notebook_id: str,
        task_id: str,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        self.calls.append(("import_sources", (notebook_id, task_id, sources), {}))
        return [{"id": "src-1", "title": "Imported"}]


class FakeArtifactsAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def generate_audio(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_audio", (notebook_id,), kwargs))
        return {"task_id": "audio-1", "status": "pending"}

    async def generate_video(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_video", (notebook_id,), kwargs))
        return {"task_id": "video-1", "status": "pending"}

    async def generate_slide_deck(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_slide_deck", (notebook_id,), kwargs))
        return {"task_id": "slides-1", "status": "pending"}

    async def generate_infographic(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_infographic", (notebook_id,), kwargs))
        return {"task_id": "info-1", "status": "pending"}

    async def generate_quiz(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_quiz", (notebook_id,), kwargs))
        return {"task_id": "quiz-1", "status": "pending"}

    async def generate_flashcards(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_flashcards", (notebook_id,), kwargs))
        return {"task_id": "cards-1", "status": "pending"}

    async def generate_report(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_report", (notebook_id,), kwargs))
        return {"task_id": "report-1", "status": "pending"}

    async def generate_data_table(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_data_table", (notebook_id,), kwargs))
        return {"task_id": "table-1", "status": "pending"}

    async def generate_mind_map(self, notebook_id: str, **kwargs: Any) -> dict[str, str]:
        self.calls.append(("generate_mind_map", (notebook_id,), kwargs))
        return {"note_id": "mind-1"}

    async def poll_status(self, notebook_id: str, task_id: str) -> dict[str, str]:
        self.calls.append(("poll_status", (notebook_id, task_id), {}))
        return {"task_id": task_id, "status": "completed"}

    async def wait_for_completion(
        self, notebook_id: str, task_id: str, **kwargs: Any
    ) -> dict[str, str]:
        self.calls.append(("wait_for_completion", (notebook_id, task_id), kwargs))
        return {"task_id": task_id, "status": "completed"}

    async def list(
        self, notebook_id: str, artifact_type: Any | None = None
    ) -> list[dict[str, str]]:
        self.calls.append(("list", (notebook_id, artifact_type), {}))
        return [{"id": "artifact-1", "kind": str(artifact_type or "all")}]

    async def download_quiz(
        self,
        notebook_id: str,
        output_path: str,
        *,
        artifact_id: str | None = None,
        output_format: str = "json",
    ) -> str:
        self.calls.append(
            (
                "download_quiz",
                (notebook_id, output_path),
                {"artifact_id": artifact_id, "output_format": output_format},
            )
        )
        return output_path

    async def revise_slide(
        self,
        notebook_id: str,
        artifact_id: str,
        slide_index: int,
        prompt: str,
    ) -> dict[str, str]:
        self.calls.append(("revise_slide", (notebook_id, artifact_id, slide_index, prompt), {}))
        return {"task_id": "revision-1", "status": "pending"}

    async def delete(self, notebook_id: str, artifact_id: str) -> bool:
        self.calls.append(("delete", (notebook_id, artifact_id), {}))
        return True

    async def cancel(self, notebook_id: str, task_id: str) -> bool:
        self.calls.append(("cancel", (notebook_id, task_id), {}))
        return True


class FakeSettingsAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.language = "en"

    async def get_output_language(self) -> str:
        self.calls.append(("get_output_language", ()))
        return self.language

    async def set_output_language(self, language: str) -> str:
        self.calls.append(("set_output_language", (language,)))
        self.language = language
        return language


class FakeNotebookLMClient:
    def __init__(self) -> None:
        self.notebooks = FakeNotebooksAPI()
        self.sources = FakeSourcesAPI()
        self.chat = FakeChatAPI()
        self.research = FakeResearchAPI()
        self.artifacts = FakeArtifactsAPI()
        self.settings = FakeSettingsAPI()
        self.notes = self
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> FakeNotebookLMClient:
        self.entered = True
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.exited = True

    async def list(self, notebook_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [{"id": "note-1", "notebook_id": notebook_id, "limit": limit}]

    async def create(self, notebook_id: str, *, title: str, content: str) -> dict[str, str]:
        return {"id": "note-1", "notebook_id": notebook_id, "title": title, "content": content}


async def test_backend_delegates_notebook_operations() -> None:
    fake = FakeNotebookLMClient()

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    assert await backend.list_notebooks() == [{"id": "nb-1", "title": "Notebook"}]
    assert await backend.create_notebook("New") == {"id": "nb-2", "title": "New"}
    assert await backend.get_notebook("nb-1") == {"id": "nb-1", "title": "Notebook"}
    assert await backend.rename_notebook("nb-1", "Renamed") == {
        "id": "nb-1",
        "title": "Renamed",
    }
    assert await backend.delete_notebook("nb-1") is True

    await backend.close()

    assert fake.entered is True
    assert fake.exited is True
    assert fake.notebooks.calls == [
        ("list", ()),
        ("create", ("New",)),
        ("get", ("nb-1",)),
        ("rename", ("nb-1", "Renamed")),
        ("delete", ("nb-1",)),
    ]


async def test_backend_delegates_source_and_chat_operations() -> None:
    fake = FakeNotebookLMClient()

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        assert await backend.list_sources("nb-1") == [{"id": "src-1", "title": "Source"}]
        assert await backend.add_url_source("nb-1", "https://example.com") == {
            "id": "src-2",
            "title": "https://example.com",
        }
        assert await backend.add_youtube_source("nb-1", "https://youtube.com/watch?v=abc") == {
            "id": "src-youtube",
            "title": "https://youtube.com/watch?v=abc",
        }
        assert await backend.get_source_fulltext("nb-1", "src-1") == {
            "source_id": "src-1",
            "text": "full text",
        }
        assert await backend.ask("nb-1", "Question?", source_ids=["src-1"]) == {
            "answer": "response",
            "citations": [],
        }

        assert fake.sources.calls == [
            ("list", ("nb-1",)),
            ("add_url", ("nb-1", "https://example.com", False)),
            ("add_youtube", ("nb-1", "https://youtube.com/watch?v=abc", False)),
            ("get_fulltext", ("nb-1", "src-1")),
        ]
        assert fake.chat.calls == [("ask", ("nb-1", "Question?", ["src-1"], None))]
    finally:
        await backend.close()


async def test_backend_delegates_research_artifact_and_language_operations() -> None:
    fake = FakeNotebookLMClient()

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        assert await backend.start_research("nb-1", "topic", source="web", mode="deep") == {
            "task_id": "research-1",
            "source": "web",
            "mode": "deep",
        }
        assert await backend.research_status("nb-1") == {
            "task_id": "research-1",
            "status": "completed",
        }
        assert await backend.import_research_sources(
            "nb-1", "research-1", [{"url": "https://example.com", "title": "Example"}]
        ) == [{"id": "src-1", "title": "Imported"}]
        assert (await backend.generate_audio_overview("nb-1"))["task_id"] == "audio-1"
        assert (await backend.generate_video_overview("nb-1"))["task_id"] == "video-1"
        assert (await backend.generate_cinematic_video("nb-1"))["task_id"] == "video-1"
        assert (await backend.generate_slide_deck("nb-1"))["task_id"] == "slides-1"
        assert (await backend.generate_infographic("nb-1"))["task_id"] == "info-1"
        assert (await backend.generate_quiz("nb-1"))["task_id"] == "quiz-1"
        assert (await backend.generate_flashcards("nb-1"))["task_id"] == "cards-1"
        assert (await backend.generate_report("nb-1"))["task_id"] == "report-1"
        assert (await backend.generate_data_table("nb-1"))["task_id"] == "table-1"
        assert await backend.generate_mind_map("nb-1") == {"note_id": "mind-1"}
        assert await backend.artifact_status("nb-1", "audio-1") == {
            "task_id": "audio-1",
            "status": "completed",
        }
        assert (
            await backend.artifact_wait(
                "nb-1",
                "audio-1",
                initial_interval=1.0,
                max_interval=1.0,
                timeout=2.0,
            )
        )["status"] == "completed"
        assert await backend.artifact_list("nb-1", "audio") == [
            {"id": "artifact-1", "kind": "ArtifactType.AUDIO"}
        ]
        assert (
            await backend.artifact_download(
                "nb-1",
                "quiz",
                "quiz.json",
                artifact_id="quiz-1",
                output_format="json",
            )
            == "quiz.json"
        )
        assert await backend.artifact_delete("nb-1", "quiz-1") is True
        assert await backend.artifact_cancel("nb-1", "audio-1") is True
        assert (await backend.revise_slide("nb-1", "slides-1", 0, "Revise"))["task_id"] == (
            "revision-1"
        )
        assert await backend.list_notes("nb-1", limit=5) == [
            {"id": "note-1", "notebook_id": "nb-1", "limit": 5}
        ]
        assert await backend.get_language() == "en"
        assert await backend.set_language("tr") == "tr"
    finally:
        await backend.close()

    assert fake.research.calls[0] == (
        "start",
        ("nb-1", "topic"),
        {"source": "web", "mode": "deep"},
    )
    assert fake.artifacts.calls[0][0] == "generate_audio"
    assert [call[0] for call in fake.artifacts.calls].count(
        "generate_video"
    ) == EXPECTED_VIDEO_GENERATE_CALLS
    assert "generate_cinematic_video" not in [call[0] for call in fake.artifacts.calls]
    mind_map_call = next(call for call in fake.artifacts.calls if call[0] == "generate_mind_map")
    assert mind_map_call[2] == {"source_ids": None}
    infographic_call = next(
        call for call in fake.artifacts.calls if call[0] == "generate_infographic"
    )
    assert "style" not in infographic_call[2]
    assert fake.settings.calls == [("get_output_language", ()), ("set_output_language", ("tr",))]


async def test_backend_normalizes_and_validates_artifact_download_formats() -> None:
    fake = FakeNotebookLMClient()

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        assert (
            await backend.artifact_download(
                "nb-1",
                "quiz",
                "quiz.md",
                artifact_id="quiz-1",
                output_format="md",
            )
            == "quiz.md"
        )
        assert fake.artifacts.calls[-1] == (
            "download_quiz",
            ("nb-1", "quiz.md"),
            {"artifact_id": "quiz-1", "output_format": "markdown"},
        )

        with raises(BackendValidationError) as exc_info:
            await backend.artifact_download("nb-1", "audio", "audio.md", output_format="md")
        assert exc_info.value.error_code == VALIDATION_ERROR_CODE
        assert exc_info.value.data == {"artifact_type": "audio", "output_format": "md"}

        with raises(BackendValidationError) as slide_exc:
            await backend.artifact_download(
                "nb-1", "slide_deck", "slides.html", output_format="html"
            )
        assert slide_exc.value.data == {"artifact_type": "slide_deck", "output_format": "html"}
    finally:
        await backend.close()


async def test_backend_maps_errors_after_retry() -> None:
    fake = FakeNotebookLMClient()
    fake.notebooks.error = RateLimitError("limited", retry_after=RETRY_AFTER_SECONDS)

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        with raises(BackendRateLimitError) as exc_info:
            await backend.list_notebooks()

        assert exc_info.value.data["retry_after_seconds"] == RETRY_AFTER_SECONDS
        assert len(fake.notebooks.calls) == MAX_RETRY_ATTEMPTS
    finally:
        await backend.close()


async def test_backend_connect_serializes_concurrent_initialization() -> None:
    fake = FakeNotebookLMClient()
    factory_calls = 0

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        nonlocal factory_calls
        factory_calls += 1
        await asyncio.sleep(0)
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        clients = await asyncio.gather(backend.connect(), backend.connect(), backend.connect())
    finally:
        await backend.close()

    assert all(client is fake for client in clients)
    assert factory_calls == 1
    assert fake.exited is True


async def test_backend_cleans_up_context_when_enter_fails() -> None:
    class FailingEnterClient(FakeNotebookLMClient):
        async def __aenter__(self) -> FakeNotebookLMClient:
            self.entered = True
            raise TimeoutError("temporary")

    fake = FailingEnterClient()

    async def factory(_settings: Settings) -> FailingEnterClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    with raises(BackendTimeoutError):
        await backend.connect()

    assert fake.entered is True
    assert fake.exited is True


async def test_backend_reconnects_after_retryable_operation_error() -> None:
    clients: list[FakeNotebookLMClient] = []

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        client = FakeNotebookLMClient()
        if not clients:
            client.notebooks.error = TimeoutError("temporary")
        clients.append(client)
        return client

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        assert await backend.list_notebooks() == [{"id": "nb-1", "title": "Notebook"}]
    finally:
        await backend.close()

    assert len(clients) == EXPECTED_RECONNECT_CLIENTS
    assert clients[0].exited is True
    assert clients[1].exited is True


async def test_backend_retries_retryable_connection_error() -> None:
    attempts = 0
    fake = FakeNotebookLMClient()

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("temporary")
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        assert await backend.list_notebooks() == [{"id": "nb-1", "title": "Notebook"}]
    finally:
        await backend.close()

    assert attempts == EXPECTED_RECONNECT_CLIENTS
    assert fake.exited is True


async def test_backend_does_not_retry_mutating_operations() -> None:
    fake = FakeNotebookLMClient()
    fake.notebooks.create_error = TimeoutError("temporary")

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        with raises(BackendTimeoutError):
            await backend.create_notebook("New")
    finally:
        await backend.close()

    assert fake.notebooks.calls == [("create", ("New",))]


async def test_backend_does_not_retry_chat_questions() -> None:
    fake = FakeNotebookLMClient()
    fake.chat.error = TimeoutError("temporary")

    async def factory(_settings: Settings) -> FakeNotebookLMClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    try:
        with raises(BackendTimeoutError):
            await backend.ask("nb-1", "Question?", conversation_id="conv-1")
    finally:
        await backend.close()

    assert fake.chat.calls == [("ask", ("nb-1", "Question?", None, "conv-1"))]


async def test_backend_close_suppresses_client_exit_errors() -> None:
    class FailingExitClient(FakeNotebookLMClient):
        async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
            self.exited = True
            raise RuntimeError("cleanup failed")

    fake = FailingExitClient()

    async def factory(_settings: Settings) -> FailingExitClient:
        return fake

    backend = NotebookLMBackend(
        Settings(),
        client_factory=factory,
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    await backend.connect()
    await backend.close()

    assert fake.exited is True


def test_resolve_auth_source_prefers_inline_json(tmp_path: Path) -> None:
    auth_file = tmp_path / "missing.json"
    settings = Settings(
        notebooklm_auth_json=SecretStr('{"cookies": []}'),
        notebooklm_auth_file=auth_file,
    )

    assert resolve_auth_source(settings) == AuthSource(kind="env_json", value='{"cookies": []}')


def test_resolve_auth_source_uses_existing_file(tmp_path: Path) -> None:
    auth_file = tmp_path / "storage.json"
    auth_file.write_text('{"cookies": []}', encoding="utf-8")

    source = resolve_auth_source(Settings(notebooklm_auth_file=auth_file))

    assert source == AuthSource(kind="file", value=str(auth_file))


def test_resolve_auth_source_uses_notebooklm_default_when_project_default_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    default_path = tmp_path / "missing-default.json"
    cli_default_path = tmp_path / "missing-cli-default.json"
    monkeypatch.setattr(client_module, "DEFAULT_NOTEBOOKLM_AUTH_FILE", default_path)
    monkeypatch.setattr(client_module, "_notebooklm_default_auth_file", lambda: cli_default_path)

    source = resolve_auth_source(Settings(notebooklm_auth_file=default_path))

    assert source == AuthSource(kind="default", value=str(cli_default_path))


def test_resolve_auth_source_uses_notebooklm_cli_default_when_present(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    default_path = tmp_path / "missing-project-default.json"
    cli_default_path = tmp_path / "profiles" / "default" / "storage_state.json"
    cli_default_path.parent.mkdir(parents=True)
    cli_default_path.write_text('{"cookies": []}', encoding="utf-8")
    monkeypatch.setattr(client_module, "DEFAULT_NOTEBOOKLM_AUTH_FILE", default_path)
    monkeypatch.setattr(client_module, "_notebooklm_default_auth_file", lambda: cli_default_path)

    source = resolve_auth_source(Settings(notebooklm_auth_file=default_path))

    assert source == AuthSource(kind="file", value=str(cli_default_path))


def test_resolve_auth_source_prefers_newer_notebooklm_cli_default_over_project_default(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    project_default_path = tmp_path / "project" / "notebooklm_auth.json"
    cli_default_path = tmp_path / "profiles" / "default" / "storage_state.json"
    project_default_path.parent.mkdir(parents=True)
    cli_default_path.parent.mkdir(parents=True)
    project_default_path.write_text('{"cookies": [{"name": "expired"}]}', encoding="utf-8")
    cli_default_path.write_text('{"cookies": [{"name": "active"}]}', encoding="utf-8")
    os.utime(project_default_path, (100, 100))
    os.utime(cli_default_path, (200, 200))
    monkeypatch.setattr(client_module, "DEFAULT_NOTEBOOKLM_AUTH_FILE", project_default_path)
    monkeypatch.setattr(client_module, "_notebooklm_default_auth_file", lambda: cli_default_path)

    source = resolve_auth_source(Settings(notebooklm_auth_file=project_default_path))

    assert source == AuthSource(kind="file", value=str(cli_default_path))


def test_resolve_auth_source_prefers_newer_project_default_over_notebooklm_cli_default(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    project_default_path = tmp_path / "project" / "notebooklm_auth.json"
    cli_default_path = tmp_path / "profiles" / "default" / "storage_state.json"
    project_default_path.parent.mkdir(parents=True)
    cli_default_path.parent.mkdir(parents=True)
    project_default_path.write_text('{"cookies": [{"name": "active"}]}', encoding="utf-8")
    cli_default_path.write_text('{"cookies": [{"name": "expired"}]}', encoding="utf-8")
    os.utime(project_default_path, (200, 200))
    os.utime(cli_default_path, (100, 100))
    monkeypatch.setattr(client_module, "DEFAULT_NOTEBOOKLM_AUTH_FILE", project_default_path)
    monkeypatch.setattr(client_module, "_notebooklm_default_auth_file", lambda: cli_default_path)

    source = resolve_auth_source(Settings(notebooklm_auth_file=project_default_path))

    assert source == AuthSource(kind="file", value=str(project_default_path))


def test_resolve_auth_source_honors_notebooklm_profile_env(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    default_path = tmp_path / "missing-project-default.json"
    profile_storage = tmp_path / "notebooklm-home" / "profiles" / "work" / "storage_state.json"
    profile_storage.parent.mkdir(parents=True)
    profile_storage.write_text('{"cookies": []}', encoding="utf-8")
    monkeypatch.setattr(client_module, "DEFAULT_NOTEBOOKLM_AUTH_FILE", default_path)
    monkeypatch.setenv("NOTEBOOKLM_HOME", str(tmp_path / "notebooklm-home"))
    monkeypatch.setenv("NOTEBOOKLM_PROFILE", "work")

    source = resolve_auth_source(Settings(notebooklm_auth_file=default_path))

    assert source == AuthSource(kind="file", value=str(profile_storage))


def test_resolve_auth_source_uses_default_resolution_for_missing_profile_env_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    default_path = tmp_path / "missing-project-default.json"
    profile_storage = tmp_path / "notebooklm-home" / "profiles" / "work" / "storage_state.json"
    monkeypatch.setattr(client_module, "DEFAULT_NOTEBOOKLM_AUTH_FILE", default_path)
    monkeypatch.setenv("NOTEBOOKLM_HOME", str(tmp_path / "notebooklm-home"))
    monkeypatch.setenv("NOTEBOOKLM_PROFILE", "work")

    source = resolve_auth_source(Settings(notebooklm_auth_file=default_path))

    assert source == AuthSource(kind="default", value=str(profile_storage))


def test_resolve_auth_source_rejects_missing_file(tmp_path: Path) -> None:
    with raises(BackendAuthError) as exc_info:
        resolve_auth_source(Settings(notebooklm_auth_file=tmp_path / "missing.json"))

    assert exc_info.value.error_code == AUTH_ERROR_CODE


async def test_default_client_factory_sets_notebooklm_auth_json_env(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}

    class FakeNotebookLMClientClass:
        @classmethod
        async def from_storage(
            cls,
            path: str | None = None,
            timeout: float = 30.0,
        ) -> FakeNotebookLMClient:
            captured["path"] = path
            captured["auth_json"] = __import__("os").environ.get("NOTEBOOKLM_AUTH_JSON")
            captured["timeout"] = str(timeout)
            return FakeNotebookLMClient()

    monkeypatch.setattr("nlm_mcp.backend.client.NotebookLMClient", FakeNotebookLMClientClass)

    backend = NotebookLMBackend(
        Settings(notebooklm_auth_json=SecretStr('{"cookies": []}')),
        retry_wait_strategy=wait_none(),
        retry_sleep=_no_sleep,
    )

    await backend.connect()
    await backend.close()

    assert captured == {
        "path": None,
        "auth_json": '{"cookies": []}',
        "timeout": "30.0",
    }
