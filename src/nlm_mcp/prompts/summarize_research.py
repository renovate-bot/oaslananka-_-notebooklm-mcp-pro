"""Prompt template for research summaries."""

from __future__ import annotations

from typing import Literal


def summarize_research_prompt(
    urls: list[str],
    format: Literal["podcast", "report", "slides"],
) -> str:
    """Build a prompt for URL-backed research artifact generation."""
    joined_urls = "\n".join(f"- {url}" for url in urls)
    return (
        "Create a new NotebookLM notebook from these URLs, wait for indexing, "
        f"then generate a {format} artifact with citations and a concise source map.\n\n"
        f"{joined_urls}"
    )
