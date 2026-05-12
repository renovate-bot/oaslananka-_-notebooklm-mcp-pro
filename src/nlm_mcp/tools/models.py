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


ResearchMode = Literal["fast", "deep"]
ArtifactTypeName = Literal[
    "audio",
    "video",
    "report",
    "quiz",
    "flashcards",
    "mind_map",
    "infographic",
    "slide_deck",
    "data_table",
]


class ResearchStartInput(NotebookIdInput):
    """Input for research start tools."""

    query: str = Field(min_length=1, max_length=1000)
    mode: ResearchMode = "fast"


class ResearchWaitInput(NotebookIdInput):
    """Input for `research.wait`."""

    task_id: str | None = Field(default=None, min_length=1)
    poll_interval_sec: int = Field(default=15, ge=1)
    timeout_sec: int = Field(default=600, ge=1)
    auto_import: bool = False
    max_sources: int = Field(default=10, ge=1, le=100)


class GenerationBaseInput(NotebookIdInput):
    """Common generation input."""

    source_ids: list[str] | None = None
    language: str = Field(default="en", min_length=1)
    instructions: str | None = Field(default=None, max_length=4000)


class AudioOverviewInput(GenerationBaseInput):
    """Input for `generate.audio_overview`."""

    audio_format: Literal["deep_dive", "brief", "critique", "debate"] = "deep_dive"
    audio_length: Literal["short", "default", "long"] = "default"


class VideoOverviewInput(GenerationBaseInput):
    """Input for `generate.video_overview`."""

    video_format: Literal["explainer", "brief"] = "explainer"
    video_style: Literal[
        "auto_select",
        "custom",
        "classic",
        "whiteboard",
        "kawaii",
        "anime",
        "watercolor",
        "retro_print",
        "heritage",
        "paper_craft",
    ] = "auto_select"


class CinematicVideoInput(GenerationBaseInput):
    """Input for `generate.cinematic_video`."""


class SlideDeckInput(GenerationBaseInput):
    """Input for `generate.slide_deck`."""

    slide_format: Literal["detailed_deck", "presenter_slides"] = "detailed_deck"
    slide_length: Literal["default", "short"] = "default"


class InfographicInput(GenerationBaseInput):
    """Input for `generate.infographic`."""

    orientation: Literal["landscape", "portrait", "square"] = "landscape"
    detail_level: Literal["concise", "standard", "detailed"] = "standard"


class QuizLikeInput(NotebookIdInput):
    """Input shared by quiz and flashcards tools."""

    source_ids: list[str] | None = None
    instructions: str | None = Field(default=None, max_length=4000)
    quantity: Literal["fewer", "standard", "more"] = "standard"
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class ReportInput(GenerationBaseInput):
    """Input for `generate.report`."""

    report_format: Literal["briefing_doc", "study_guide", "blog_post", "custom"] = "briefing_doc"
    custom_prompt: str | None = Field(default=None, max_length=8000)
    extra_instructions: str | None = Field(default=None, max_length=4000)


class DataTableInput(GenerationBaseInput):
    """Input for `generate.data_table`."""


class MindMapInput(NotebookIdInput):
    """Input for `generate.mind_map`."""

    source_ids: list[str] | None = None


class GenerationTaskOutput(StrictModel):
    """Output returned when an artifact task is submitted."""

    task_id: str
    status: str
    notebook_id: str
    artifact_type: str
    result: Any


class ArtifactStatusInput(NotebookIdInput):
    """Input for artifact task status tools."""

    task_id: str = Field(min_length=1)


class ArtifactWaitInput(ArtifactStatusInput):
    """Input for `artifact.wait`."""

    poll_interval_sec: int = Field(default=15, ge=1)
    timeout_sec: int = Field(default=600, ge=1)


class ArtifactListInput(NotebookIdInput):
    """Input for `artifact.list`."""

    artifact_type: ArtifactTypeName | None = None


class ArtifactDownloadInput(NotebookIdInput):
    """Input for `artifact.download`."""

    artifact_type: ArtifactTypeName
    output_path: str = Field(min_length=1)
    artifact_id: str | None = Field(default=None, min_length=1)
    output_format: Literal["json", "md", "markdown", "html", "pdf", "pptx"] | None = None


class ReviseSlideInput(NotebookIdInput):
    """Input for `artifact.revise_slide`."""

    artifact_id: str = Field(min_length=1)
    slide_index: int = Field(ge=0)
    prompt: str = Field(min_length=1, max_length=4000)


class LanguageSetInput(StrictModel):
    """Input for `language.set`."""

    language: str = Field(min_length=1)
    confirm: bool = False
