"""Prompt template for paper deep dives."""

from __future__ import annotations


def paper_deep_dive_prompt(pdf_path: str) -> str:
    """Build a prompt for a paper deep-dive workflow."""
    return (
        f"Ingest the PDF at {pdf_path}, create a paper deep-dive notebook, and "
        "generate a cinematic video, slide deck, and report. Include assumptions, "
        "methodology, limitations, and practical implications."
    )
