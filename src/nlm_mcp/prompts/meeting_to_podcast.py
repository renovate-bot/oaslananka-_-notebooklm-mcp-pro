"""Prompt template for meeting-to-podcast workflows."""

from __future__ import annotations

from typing import Literal


def meeting_to_podcast_prompt(
    transcript_path: str,
    style: Literal["debate", "deep-dive"],
) -> str:
    """Build a prompt for turning a transcript into an audio overview."""
    return (
        f"Ingest the meeting transcript at {transcript_path}, create a notebook, "
        f"and generate an audio overview in {style} style. Emphasize decisions, "
        "open questions, owners, and follow-up timing."
    )
