"""Prompt template for study packs."""

from __future__ import annotations

from typing import Literal


def study_pack_prompt(
    notebook_id: str,
    difficulty: Literal["easy", "medium", "hard"],
) -> str:
    """Build a prompt for a NotebookLM study pack."""
    return (
        f"For notebook {notebook_id}, create a {difficulty} study pack by generating "
        "a quiz, flashcards, and a mind map. Return the task ids and summarize the "
        "learning objectives covered by each artifact."
    )
