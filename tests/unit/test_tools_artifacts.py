from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError

from nlm_mcp.backend.client import NotebookLMBackend
from nlm_mcp.backend.tasks import TaskStore
from nlm_mcp.config import Settings
from nlm_mcp.server import create_server

MIN_SUPPORTED_LANGUAGES = 80


class FakeArtifactBackend:
    """Offline backend for research, generation, lifecycle, and language tools."""

    def __init__(self) -> None:
        self.downloads: list[tuple[str, str, str, str | None, str | None]] = []
        self.imported: list[dict[str, Any]] = []
        self.language = "en"

    async def start_research(
        self,
        notebook_id: str,
        query: str,
        *,
        source: str = "web",
        mode: str = "fast",
    ) -> dict[str, Any]:
        return {
            "task_id": f"{source}-research-1",
            "notebook_id": notebook_id,
            "query": query,
            "source": source,
            "mode": mode,
        }

    async def research_status(self, notebook_id: str) -> dict[str, Any]:
        return {
            "task_id": "web-research-1",
            "status": "completed",
            "notebook_id": notebook_id,
            "sources": [{"url": "https://example.com", "title": "Example"}],
        }

    async def import_research_sources(
        self,
        notebook_id: str,
        task_id: str,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        self.imported.append({"notebook_id": notebook_id, "task_id": task_id, "sources": sources})
        return [{"id": "src-imported", "title": sources[0]["title"]}]

    async def generate_audio_overview(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "audio-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_video_overview(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "video-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_cinematic_video(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "cinematic-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_slide_deck(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "slides-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_infographic(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "info-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_quiz(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "quiz-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_flashcards(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "cards-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_report(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "report-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_data_table(self, notebook_id: str, **_: Any) -> dict[str, str]:
        return {"task_id": "table-1", "status": "pending", "notebook_id": notebook_id}

    async def generate_mind_map(self, notebook_id: str, **_: Any) -> dict[str, Any]:
        return {
            "note_id": "mind-1",
            "mind_map": {"name": "Root", "children": [{"name": "Leaf"}]},
            "notebook_id": notebook_id,
        }

    async def artifact_status(self, notebook_id: str, task_id: str) -> dict[str, str]:
        return {
            "task_id": task_id,
            "status": "completed",
            "notebook_id": notebook_id,
        }

    async def artifact_wait(
        self,
        notebook_id: str,
        task_id: str,
        *,
        initial_interval: float,
        max_interval: float,
        timeout: float,
    ) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "status": "completed",
            "notebook_id": notebook_id,
            "interval": initial_interval,
            "max_interval": max_interval,
            "timeout": timeout,
        }

    async def artifact_list(
        self,
        notebook_id: str,
        artifact_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "audio-1",
                "title": "Audio",
                "kind": artifact_type or "audio",
                "notebook_id": notebook_id,
            }
        ]

    async def artifact_download(
        self,
        notebook_id: str,
        artifact_type: str,
        output_path: str,
        *,
        artifact_id: str | None = None,
        output_format: str | None = None,
    ) -> str:
        self.downloads.append((notebook_id, artifact_type, output_path, artifact_id, output_format))
        return output_path

    async def revise_slide(
        self,
        notebook_id: str,
        artifact_id: str,
        slide_index: int,
        prompt: str,
    ) -> dict[str, str]:
        return {
            "task_id": "revision-1",
            "status": "pending",
            "notebook_id": notebook_id,
            "artifact_id": artifact_id,
            "slide_index": str(slide_index),
            "prompt": prompt,
        }

    async def artifact_delete(self, notebook_id: str, artifact_id: str) -> bool:
        return notebook_id == "nb-1" and artifact_id == "quiz-1"

    async def artifact_cancel(self, notebook_id: str, task_id: str) -> bool:
        return notebook_id == "nb-1" and task_id == "audio-1"

    async def get_language(self) -> str:
        return self.language

    async def set_language(self, language: str) -> str:
        self.language = language
        return language


def _server(tmp_path: Path, backend: FakeArtifactBackend | None = None) -> Any:
    settings = Settings(data_dir=tmp_path)
    return create_server(
        settings,
        backend=cast(NotebookLMBackend, backend or FakeArtifactBackend()),
    )


async def test_generation_tools_submit_and_track_tasks(tmp_path: Path) -> None:
    async with Client(_server(tmp_path)) as client:
        audio = await client.call_tool(
            "generate_audio_overview",
            {
                "notebook_id": "nb-1",
                "audio_format": "debate",
                "audio_length": "short",
            },
        )
        video = await client.call_tool("generate_video_overview", {"notebook_id": "nb-1"})
        cinematic = await client.call_tool("generate_cinematic_video", {"notebook_id": "nb-1"})
        slides = await client.call_tool(
            "generate_slide_deck",
            {"notebook_id": "nb-1", "slide_format": "presenter_slides"},
        )
        infographic = await client.call_tool(
            "generate_infographic",
            {"notebook_id": "nb-1", "orientation": "square", "detail_level": "detailed"},
        )
        quiz = await client.call_tool(
            "generate_quiz",
            {"notebook_id": "nb-1", "quantity": "fewer", "difficulty": "hard"},
        )
        cards = await client.call_tool("generate_flashcards", {"notebook_id": "nb-1"})
        report = await client.call_tool(
            "generate_report",
            {"notebook_id": "nb-1", "report_format": "study_guide"},
        )
        table = await client.call_tool("generate_data_table", {"notebook_id": "nb-1"})
        mind_map = await client.call_tool("generate_mind_map", {"notebook_id": "nb-1"})

    assert audio.data["task_id"] == "audio-1"
    assert video.data["artifact_type"] == "video"
    assert cinematic.data["task_id"] == "cinematic-1"
    assert slides.data["artifact_type"] == "slide_deck"
    assert infographic.data["task_id"] == "info-1"
    assert quiz.data["task_id"] == "quiz-1"
    assert cards.data["task_id"] == "cards-1"
    assert report.data["task_id"] == "report-1"
    assert table.data["artifact_type"] == "data_table"
    assert mind_map.data["task_id"] == "mind-1"


async def test_quiz_like_validation_errors_are_sanitized(tmp_path: Path) -> None:
    backend = FakeArtifactBackend()
    async with Client(_server(tmp_path, backend)) as client:
        with pytest.raises(ToolError, match="quantity"):
            await client.call_tool(
                "generate_quiz",
                {"notebook_id": "nb-1", "quantity": "short"},
            )
        with pytest.raises(ToolError, match="quantity"):
            await client.call_tool(
                "generate_flashcards",
                {"notebook_id": "nb-1", "quantity": "short"},
            )


async def test_artifact_lifecycle_tools_and_resources(tmp_path: Path) -> None:
    backend = FakeArtifactBackend()
    async with Client(_server(tmp_path, backend)) as client:
        await client.call_tool("generate_audio_overview", {"notebook_id": "nb-1"})
        status = await client.call_tool(
            "artifact_status",
            {"notebook_id": "nb-1", "task_id": "audio-1"},
        )
        waited = await client.call_tool(
            "artifact_wait",
            {"notebook_id": "nb-1", "task_id": "audio-1", "poll_interval_sec": 1},
        )
        listed = await client.call_tool(
            "artifact_list",
            {"notebook_id": "nb-1", "artifact_type": "audio"},
        )
        downloaded = await client.call_tool(
            "artifact_download",
            {
                "notebook_id": "nb-1",
                "artifact_type": "quiz",
                "artifact_id": "quiz-1",
                "output_path": "quiz_json",
                "output_format": "md",
            },
        )
        revised = await client.call_tool(
            "artifact_revise_slide",
            {
                "notebook_id": "nb-1",
                "artifact_id": "slides-1",
                "slide_index": 0,
                "prompt": "Tighten the title",
            },
        )
        deleted = await client.call_tool(
            "artifact_delete",
            {"notebook_id": "nb-1", "artifact_id": "quiz-1", "confirm": True},
        )
        canceled = await client.call_tool(
            "artifact_cancel",
            {"notebook_id": "nb-1", "task_id": "audio-1", "confirm": True},
        )
        artifact_resource = await client.read_resource("notebooklm://artifact/audio-1")
        mindmap_resource = await client.read_resource("notebooklm://notebook/nb-1/mindmap")
        with pytest.raises(McpError, match="Artifact task was not found"):
            await client.read_resource("notebooklm://artifact/missing")

    assert status.data["status"]["status"] == "completed"
    assert waited.data["status"]["interval"] == 1.0
    assert listed.data["tracked_tasks"][0]["task_id"] == "audio-1"
    assert downloaded.data["path"] == str(tmp_path / "artifacts" / "quiz_json")
    assert backend.downloads[0][2] == str(tmp_path / "artifacts" / "quiz_json")
    assert backend.downloads[0][4] == "markdown"
    assert revised.data["task_id"] == "revision-1"
    assert deleted.data["deleted"] is True
    assert canceled.data["canceled"] is True
    assert json.loads(artifact_resource[0].text)["artifact"]["task_id"] == "audio-1"
    assert json.loads(mindmap_resource[0].text)["mind_maps"][0]["kind"] == "mind_map"


async def test_artifact_download_rejects_unsafe_paths(tmp_path: Path) -> None:
    absolute_backend = FakeArtifactBackend()
    async with Client(_server(tmp_path, absolute_backend)) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "artifact_download",
                {
                    "notebook_id": "nb-1",
                    "artifact_type": "quiz",
                    "output_path": str(tmp_path / "outside_json"),
                },
            )
    assert absolute_backend.downloads == []

    traversal_backend = FakeArtifactBackend()
    async with Client(_server(tmp_path, traversal_backend)) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "artifact_download",
                {
                    "notebook_id": "nb-1",
                    "artifact_type": "quiz",
                    "output_path": "../outside.json",
                },
            )
    assert traversal_backend.downloads == []


async def test_research_language_and_prompts(tmp_path: Path) -> None:
    backend = FakeArtifactBackend()
    async with Client(_server(tmp_path, backend)) as client:
        web = await client.call_tool(
            "research_web_start",
            {"notebook_id": "nb-1", "query": "climate", "mode": "deep"},
        )
        drive = await client.call_tool(
            "research_drive_start",
            {"notebook_id": "nb-1", "query": "budget"},
        )
        status = await client.call_tool("research_status", {"notebook_id": "nb-1"})
        waited = await client.call_tool(
            "research_wait",
            {
                "notebook_id": "nb-1",
                "poll_interval_sec": 1,
                "timeout_sec": 1,
                "auto_import": True,
            },
        )
        languages = await client.call_tool("language_list", {})
        language = await client.call_tool("language_get", {})
        with pytest.raises(ToolError, match="Confirmation required"):
            await client.call_tool("language_set", {"language": "tr"})
        changed = await client.call_tool("language_set", {"language": "tr", "confirm": True})
        prompts = await client.list_prompts()
        study_prompt = await client.get_prompt(
            "study-pack",
            {"notebook_id": "nb-1", "difficulty": "hard"},
        )
        research_prompt = await client.get_prompt(
            "summarize-research",
            {"urls": ["https://example.com"], "format": "slides"},
        )
        meeting_prompt = await client.get_prompt(
            "meeting-to-podcast",
            {"transcript_path": "meeting_txt", "style": "debate"},
        )
        paper_prompt = await client.get_prompt(
            "paper-deep-dive",
            {"pdf_path": "paper_pdf"},
        )

    assert web.data["result"]["mode"] == "deep"
    assert drive.data["result"]["source"] == "drive"
    assert status.data["result"]["status"] == "completed"
    assert waited.data["imported"][0]["id"] == "src-imported"
    assert backend.imported[0]["task_id"] == "web-research-1"
    assert languages.data["count"] >= MIN_SUPPORTED_LANGUAGES
    assert language.data == {"language": "en", "name": "English"}
    assert changed.data["language"] == "tr"
    assert changed.data["name"]
    assert {"study-pack", "summarize-research", "meeting-to-podcast", "paper-deep-dive"} == {
        item.name for item in prompts
    }
    assert "quiz, flashcards, and a mind map" in study_prompt.messages[0].content.text
    research_prompt_urls = [
        urlsplit(token.strip(".,")).geturl()
        for token in research_prompt.messages[0].content.text.split()
        if token.startswith(("http://", "https://"))
    ]
    assert research_prompt_urls == ["https://example.com"]
    assert "meeting_txt" in meeting_prompt.messages[0].content.text
    assert "paper_pdf" in paper_prompt.messages[0].content.text


async def test_research_wait_does_not_import_failed_tasks(tmp_path: Path) -> None:
    class FailedResearchBackend(FakeArtifactBackend):
        async def research_status(self, notebook_id: str) -> dict[str, Any]:
            return {
                "task_id": "web-research-1",
                "status": "failed",
                "notebook_id": notebook_id,
                "sources": [{"url": "https://example.com", "title": "Example"}],
            }

    backend = FailedResearchBackend()
    async with Client(_server(tmp_path, backend)) as client:
        waited = await client.call_tool(
            "research_wait",
            {
                "notebook_id": "nb-1",
                "task_id": "web-research-1",
                "poll_interval_sec": 1,
                "timeout_sec": 1,
                "auto_import": True,
            },
        )

    assert waited.data["research"]["status"] == "failed"
    assert waited.data["imported"] == []
    assert backend.imported == []


async def test_task_store_persists_records(tmp_path: Path) -> None:
    first_store = TaskStore(tmp_path / "tasks_db")
    await first_store.upsert(
        task_id="task-1",
        notebook_id="nb-1",
        kind="audio",
        status="pending",
        metadata={"a": 1},
    )
    second_store = TaskStore(tmp_path / "tasks_db")

    record = await second_store.get("task-1")
    records = await second_store.list_for_notebook("nb-1")

    assert record is not None
    assert record.metadata == {"a": 1}
    assert records[0].task_id == "task-1"
