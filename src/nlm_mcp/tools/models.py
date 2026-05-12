"""Pydantic models shared by NotebookLM tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    """Base model that rejects unexpected tool fields."""

    model_config = ConfigDict(extra="forbid")


class GenericRecord(StrictModel):
    """Generic NotebookLM record returned by core tools."""

    id: str
    title: str = ""
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenericResult(StrictModel):
    """Generic wrapped result for NotebookLM API responses."""

    result: Any


class NotebookListInput(StrictModel):
    """Input for `notebook.list`."""


class NotebookCreateInput(StrictModel):
    """Input for `notebook.create`."""

    title: str = Field(min_length=1, max_length=300)


class NotebookIdInput(StrictModel):
    """Input for notebook tools that target one notebook."""

    notebook_id: str = Field(min_length=1)


class NotebookRenameInput(NotebookIdInput):
    """Input for `notebook.rename`."""

    title: str = Field(min_length=1, max_length=300)


class ConfirmNotebookInput(NotebookIdInput):
    """Input for destructive notebook tools."""

    confirm: bool = False


class NotebookSharePublicInput(NotebookIdInput):
    """Input for `notebook.share_public`."""

    public: bool
    confirm: bool = False


class NotebookShareInviteInput(NotebookIdInput):
    """Input for `notebook.share_invite`."""

    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Literal["viewer", "editor"] = "viewer"
    notify: bool = True
    welcome_message: str = Field(default="", max_length=1000)
    confirm: bool = False


class SourceAddUrlInput(NotebookIdInput):
    """Input for URL-like source ingestion."""

    url: HttpUrl
    wait: bool = False


class SourceAddFileInput(NotebookIdInput):
    """Input for `source.add_file`."""

    file_path: str = Field(min_length=1)
    mime_type: str | None = None
    wait: bool = False


class SourceAddGDriveInput(NotebookIdInput):
    """Input for `source.add_gdrive`."""

    file_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=300)
    mime_type: str = "application/vnd.google-apps.document"
    wait: bool = False


class SourceAddTextInput(NotebookIdInput):
    """Input for `source.add_text`."""

    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    wait: bool = False


class SourceIdInput(NotebookIdInput):
    """Input for source tools targeting one source."""

    source_id: str = Field(min_length=1)


class ConfirmSourceInput(SourceIdInput):
    """Input for destructive source tools."""

    confirm: bool = False


class ChatAskInput(NotebookIdInput):
    """Input for `chat.ask` and `chat.continue`."""

    question: str = Field(min_length=1)
    source_ids: list[str] | None = None
    conversation_id: str | None = None


class ConversationStartInput(NotebookIdInput):
    """Input for `chat.conversation_start`."""

    name: str = Field(default="NotebookLM conversation", min_length=1, max_length=300)
    initial_question: str | None = None


class ChatHistoryInput(NotebookIdInput):
    """Input for `chat.history`."""

    limit: int = Field(default=100, ge=1, le=500)
    conversation_id: str | None = None


class SaveToNotesInput(NotebookIdInput):
    """Input for `chat.save_to_notes`."""

    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)


class SearchInput(StrictModel):
    """Input for ChatGPT-compatible `search`."""

    query: str = Field(default="", max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class SearchOutput(StrictModel):
    """Output for ChatGPT-compatible `search`."""

    ids: list[str]


class FetchInput(StrictModel):
    """Input for ChatGPT-compatible `fetch`."""

    id: str = Field(min_length=1)


class FetchOutput(StrictModel):
    """Output for ChatGPT-compatible `fetch`."""

    id: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
