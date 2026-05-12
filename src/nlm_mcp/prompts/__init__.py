"""NotebookLM MCP prompt registration."""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP

from nlm_mcp.prompts.meeting_to_podcast import meeting_to_podcast_prompt
from nlm_mcp.prompts.paper_deep_dive import paper_deep_dive_prompt
from nlm_mcp.prompts.study_pack import study_pack_prompt
from nlm_mcp.prompts.summarize_research import summarize_research_prompt


def register_prompts(server: FastMCP) -> None:
    """Register named NotebookLM workflow prompts."""

    @server.prompt(
        name="summarize-research",
        title="Summarize Research",
        description="Build a notebook from URLs and generate a requested artifact.",
    )
    def summarize_research(
        urls: list[str],
        format: Literal["podcast", "report", "slides"] = "report",
    ) -> str:
        """Build a research summary workflow prompt."""
        return summarize_research_prompt(urls, format)

    @server.prompt(
        name="study-pack",
        title="Study Pack",
        description="Generate quiz, flashcards, and mind map artifacts.",
    )
    def study_pack(
        notebook_id: str,
        difficulty: Literal["easy", "medium", "hard"] = "medium",
    ) -> str:
        """Build a study pack workflow prompt."""
        return study_pack_prompt(notebook_id, difficulty)

    @server.prompt(
        name="meeting-to-podcast",
        title="Meeting To Podcast",
        description="Ingest a transcript and generate an audio overview.",
    )
    def meeting_to_podcast(
        transcript_path: str,
        style: Literal["debate", "deep-dive"] = "deep-dive",
    ) -> str:
        """Build a meeting-to-podcast workflow prompt."""
        return meeting_to_podcast_prompt(transcript_path, style)

    @server.prompt(
        name="paper-deep-dive",
        title="Paper Deep Dive",
        description="Ingest a paper and generate video, slides, and report artifacts.",
    )
    def paper_deep_dive(pdf_path: str) -> str:
        """Build a paper deep-dive workflow prompt."""
        return paper_deep_dive_prompt(pdf_path)


__all__ = ["register_prompts"]
