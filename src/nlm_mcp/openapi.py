"""OpenAPI 3.1 schema generation for ChatGPT Custom Actions integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from nlm_mcp import __version__
from nlm_mcp.tools.common import tool_public_name
from nlm_mcp.tools.models import (
    ArtifactCancelInput,
    ArtifactDeleteInput,
    ArtifactDownloadInput,
    ArtifactListInput,
    ArtifactStatusInput,
    ArtifactWaitInput,
    AudioOverviewInput,
    ChatAskInput,
    ChatHistoryInput,
    CinematicVideoInput,
    ConfirmNotebookInput,
    ConfirmSourceInput,
    ConversationStartInput,
    DataTableInput,
    FetchInput,
    InfographicInput,
    LanguageSetInput,
    ListNotesInput,
    MindMapInput,
    NotebookCreateInput,
    NotebookIdInput,
    NotebookListInput,
    NotebookRenameInput,
    NotebookShareInviteInput,
    NotebookSharePublicInput,
    QuizLikeInput,
    ReportInput,
    ResearchStartInput,
    ResearchWaitInput,
    ReviseSlideInput,
    SaveToNotesInput,
    SearchInput,
    SlideDeckInput,
    SourceAddFileInput,
    SourceAddGDriveInput,
    SourceAddTextInput,
    SourceAddUrlInput,
    SourceIdInput,
    SourceWaitInput,
    VideoOverviewInput,
)


@dataclass(frozen=True)
class ToolSpec:
    """OpenAPI metadata for one MCP tool."""

    name: str
    summary: str
    description: str
    tag: str
    input_model: type[BaseModel]


TOOL_ALIASES: dict[str, str] = {
    "source.delete": "source.remove",
    "chat.query": "chat.ask",
    "chat.save_note": "chat.save_to_notes",
    "chat.list_notes": "chat.list_notes",
}

TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "notebook.list",
        "List all notebooks",
        "List all notebooks visible to the configured NotebookLM session.",
        "notebooks",
        NotebookListInput,
    ),
    ToolSpec(
        "notebook.create",
        "Create notebook",
        "Create a NotebookLM notebook with a title.",
        "notebooks",
        NotebookCreateInput,
    ),
    ToolSpec(
        "notebook.get",
        "Get notebook",
        "Get metadata for one NotebookLM notebook.",
        "notebooks",
        NotebookIdInput,
    ),
    ToolSpec(
        "notebook.rename",
        "Rename notebook",
        "Rename one NotebookLM notebook.",
        "notebooks",
        NotebookRenameInput,
    ),
    ToolSpec(
        "notebook.delete",
        "Delete notebook",
        "Delete a NotebookLM notebook after explicit confirmation.",
        "notebooks",
        ConfirmNotebookInput,
    ),
    ToolSpec(
        "notebook.share_public",
        "Toggle public sharing",
        "Enable or disable public sharing for a NotebookLM notebook.",
        "notebooks",
        NotebookSharePublicInput,
    ),
    ToolSpec(
        "notebook.share_invite",
        "Invite collaborator",
        "Invite a user to view or edit a NotebookLM notebook.",
        "notebooks",
        NotebookShareInviteInput,
    ),
    ToolSpec(
        "notebook.share_status",
        "Get sharing status",
        "Return sharing settings for one NotebookLM notebook.",
        "notebooks",
        NotebookIdInput,
    ),
    ToolSpec(
        "source.add_url",
        "Add URL source",
        "Add a web URL as a source to a NotebookLM notebook.",
        "sources",
        SourceAddUrlInput,
    ),
    ToolSpec(
        "source.add_youtube",
        "Add YouTube source",
        "Add a YouTube URL as a source to a NotebookLM notebook.",
        "sources",
        SourceAddUrlInput,
    ),
    ToolSpec(
        "source.add_file",
        "Add file source",
        "Upload a PDF, audio, video, image, text, markdown, or docx source.",
        "sources",
        SourceAddFileInput,
    ),
    ToolSpec(
        "source.add_gdrive",
        "Add Google Drive source",
        "Add a Google Drive document as a source.",
        "sources",
        SourceAddGDriveInput,
    ),
    ToolSpec(
        "source.add_text",
        "Add text source",
        "Paste raw text as a source in a NotebookLM notebook.",
        "sources",
        SourceAddTextInput,
    ),
    ToolSpec(
        "source.list",
        "List sources",
        "List sources in a NotebookLM notebook.",
        "sources",
        NotebookIdInput,
    ),
    ToolSpec(
        "source.get",
        "Get source",
        "Get metadata for one NotebookLM source.",
        "sources",
        SourceIdInput,
    ),
    ToolSpec(
        "source.get_fulltext",
        "Get source full text",
        "Retrieve indexed full text for one NotebookLM source.",
        "sources",
        SourceIdInput,
    ),
    ToolSpec(
        "source.refresh",
        "Refresh source",
        "Re-index one NotebookLM source.",
        "sources",
        SourceIdInput,
    ),
    ToolSpec(
        "source.wait",
        "Wait for source indexing",
        "Wait until one NotebookLM source leaves the indexing state.",
        "sources",
        SourceWaitInput,
    ),
    ToolSpec(
        "source.remove",
        "Remove source",
        "Remove a source from a NotebookLM notebook after confirmation.",
        "sources",
        ConfirmSourceInput,
    ),
    ToolSpec(
        "source.delete",
        "Delete source",
        "Alias for removing a source from a NotebookLM notebook.",
        "sources",
        ConfirmSourceInput,
    ),
    ToolSpec(
        "chat.ask",
        "Ask notebook",
        "Ask a one-shot question against a NotebookLM notebook.",
        "chat",
        ChatAskInput,
    ),
    ToolSpec(
        "chat.query",
        "Query notebook",
        "Alias for asking a one-shot question against a NotebookLM notebook.",
        "chat",
        ChatAskInput,
    ),
    ToolSpec(
        "chat.stream_query",
        "Stream query notebook",
        "Run a query through the NotebookLM chat backend and return one result.",
        "chat",
        ChatAskInput,
    ),
    ToolSpec(
        "chat.conversation_start",
        "Start conversation",
        "Start or identify a NotebookLM conversation.",
        "chat",
        ConversationStartInput,
    ),
    ToolSpec(
        "chat.continue",
        "Continue conversation",
        "Continue a NotebookLM conversation.",
        "chat",
        ChatAskInput,
    ),
    ToolSpec(
        "chat.history",
        "Get chat history",
        "Get NotebookLM conversation history.",
        "chat",
        ChatHistoryInput,
    ),
    ToolSpec(
        "chat.save_to_notes",
        "Save answer to notes",
        "Save a chat answer or drafted content as a NotebookLM note.",
        "chat",
        SaveToNotesInput,
    ),
    ToolSpec(
        "chat.save_note",
        "Save notebook note",
        "Alias for saving content as a NotebookLM note.",
        "chat",
        SaveToNotesInput,
    ),
    ToolSpec(
        "chat.list_notes",
        "List notebook notes",
        "List saved NotebookLM notes.",
        "chat",
        ListNotesInput,
    ),
    ToolSpec(
        "research.web_start",
        "Start web research",
        "Start a web research task with optional auto-import.",
        "research",
        ResearchStartInput,
    ),
    ToolSpec(
        "research.drive_start",
        "Start Drive research",
        "Start a Google Drive research task.",
        "research",
        ResearchStartInput,
    ),
    ToolSpec(
        "research.status",
        "Get research status",
        "Poll the latest research task status.",
        "research",
        NotebookIdInput,
    ),
    ToolSpec(
        "research.wait",
        "Wait for research",
        "Block until a research task finishes or times out.",
        "research",
        ResearchWaitInput,
    ),
    ToolSpec(
        "generate.audio_overview",
        "Generate audio overview",
        "Generate a NotebookLM audio overview and return a task id.",
        "artifact-generation",
        AudioOverviewInput,
    ),
    ToolSpec(
        "generate.video_overview",
        "Generate video overview",
        "Generate a NotebookLM video overview and return a task id.",
        "artifact-generation",
        VideoOverviewInput,
    ),
    ToolSpec(
        "generate.cinematic_video",
        "Generate cinematic video",
        "Generate a cinematic video and return a task id.",
        "artifact-generation",
        CinematicVideoInput,
    ),
    ToolSpec(
        "generate.infographic",
        "Generate infographic",
        "Generate an infographic and return a task id.",
        "artifact-generation",
        InfographicInput,
    ),
    ToolSpec(
        "generate.slide_deck",
        "Generate slide deck",
        "Generate a PDF or PPTX slide deck and return a task id.",
        "artifact-generation",
        SlideDeckInput,
    ),
    ToolSpec(
        "generate.report",
        "Generate report",
        "Generate a briefing, study guide, blog post, or custom report.",
        "artifact-generation",
        ReportInput,
    ),
    ToolSpec(
        "generate.mind_map",
        "Generate mind map",
        "Generate a NotebookLM mind map and return a task id.",
        "artifact-generation",
        MindMapInput,
    ),
    ToolSpec(
        "generate.data_table",
        "Generate data table",
        "Generate a data table and return a task id.",
        "artifact-generation",
        DataTableInput,
    ),
    ToolSpec(
        "generate.quiz",
        "Generate quiz",
        "Generate a quiz and return a task id.",
        "artifact-generation",
        QuizLikeInput,
    ),
    ToolSpec(
        "generate.flashcards",
        "Generate flashcards",
        "Generate flashcards and return a task id.",
        "artifact-generation",
        QuizLikeInput,
    ),
    ToolSpec(
        "artifact.list",
        "List artifacts",
        "List NotebookLM artifacts and locally tracked tasks.",
        "artifacts",
        ArtifactListInput,
    ),
    ToolSpec(
        "artifact.status",
        "Get artifact status",
        "Poll a NotebookLM artifact task.",
        "artifacts",
        ArtifactStatusInput,
    ),
    ToolSpec(
        "artifact.wait",
        "Wait for artifact",
        "Wait for an artifact task to complete.",
        "artifacts",
        ArtifactWaitInput,
    ),
    ToolSpec(
        "artifact.download",
        "Download artifact",
        "Download an artifact into the configured artifacts directory.",
        "artifacts",
        ArtifactDownloadInput,
    ),
    ToolSpec(
        "artifact.delete",
        "Delete artifact",
        "Delete a generated artifact after confirmation.",
        "artifacts",
        ArtifactDeleteInput,
    ),
    ToolSpec(
        "artifact.revise_slide",
        "Revise slide",
        "Modify one slide in a generated slide deck.",
        "artifacts",
        ReviseSlideInput,
    ),
    ToolSpec(
        "artifact.cancel",
        "Cancel artifact task",
        "Cancel a running artifact generation task.",
        "artifacts",
        ArtifactCancelInput,
    ),
    ToolSpec(
        "language.list",
        "List languages",
        "List supported NotebookLM output languages.",
        "language",
        NotebookListInput,
    ),
    ToolSpec(
        "language.get",
        "Get language",
        "Get the current account-global NotebookLM output language.",
        "language",
        NotebookListInput,
    ),
    ToolSpec(
        "language.set",
        "Set language",
        "Set the account-global NotebookLM output language after confirmation.",
        "language",
        LanguageSetInput,
    ),
    ToolSpec(
        "search",
        "Search NotebookLM records",
        "Return IDs of matching notebook and source records.",
        "compatibility",
        SearchInput,
    ),
    ToolSpec(
        "fetch",
        "Fetch NotebookLM record",
        "Return a full record by ID with id, title, content, and metadata.",
        "compatibility",
        FetchInput,
    ),
    ToolSpec(
        "admin.health",
        "Health check",
        "Return server and backend health information.",
        "admin",
        NotebookListInput,
    ),
    ToolSpec(
        "admin.version",
        "Version info",
        "Return server version and runtime information.",
        "admin",
        NotebookListInput,
    ),
)


def _operation_id(tool_name: str) -> str:
    return tool_name.replace(".", "_")


def _request_body(model: type[BaseModel]) -> dict[str, Any]:
    return {
        "required": bool(model.model_fields),
        "content": {
            "application/json": {
                "schema": model.model_json_schema(ref_template="#/components/schemas/{model}")
            }
        },
    }


def _success_schema(tool_name: str) -> dict[str, Any]:
    if tool_name == "search":
        return {
            "type": "object",
            "properties": {"ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["ids"],
        }
    if tool_name == "fetch":
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["id", "title", "content", "metadata"],
        }
    return {"type": "object", "additionalProperties": True}


def _tool_path(spec: ToolSpec) -> dict[str, Any]:
    return {
        "post": {
            "operationId": _operation_id(spec.name),
            "summary": spec.summary,
            "description": spec.description,
            "tags": [spec.tag],
            "requestBody": _request_body(spec.input_model),
            "responses": {
                "200": {
                    "description": spec.summary,
                    "content": {
                        "application/json": {
                            "schema": _success_schema(spec.name),
                        }
                    },
                },
                "400": {"description": "Invalid request"},
                "401": {"description": "Unauthorized"},
                "429": {"description": "Rate limit exceeded"},
                "500": {"description": "Backend error"},
            },
        }
    }


def _schemas() -> dict[str, Any]:
    schemas: dict[str, Any] = {}
    for spec in TOOL_SPECS:
        schemas[spec.input_model.__name__] = spec.input_model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
    return schemas


OPENAPI_SCHEMA: dict[str, Any] = {
    "openapi": "3.1.0",
    "info": {
        "title": "NotebookLM MCP Server",
        "description": (
            "Programmatic access to Google NotebookLM via MCP. Manage notebooks, "
            "sources, generated audio/video/infographic artifacts, research tasks, "
            "and chat with notebook content."
        ),
        "version": __version__,
        "contact": {
            "name": "oaslananka",
            "url": "https://github.com/oaslananka/notebooklm-mcp-pro",
        },
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    },
    "servers": [{"url": "{base_url}", "description": "NotebookLM MCP Server"}],
    "paths": {f"/tools/{spec.name}": _tool_path(spec) for spec in TOOL_SPECS},
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": (
                    "Bearer token authentication. Set NLM_MCP_BEARER_TOKEN on the server."
                ),
            }
        },
        "schemas": _schemas(),
    },
}


def resolve_tool_name(tool_name: str) -> str:
    """Return the MCP tool name backing an OpenAPI action name."""
    return tool_public_name(TOOL_ALIASES.get(tool_name, tool_name))
