#!/usr/bin/env python3
"""Run deterministic seed inputs through local fuzz targets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fuzz.config_fuzzer import test_one_input

SEEDS: tuple[bytes, ...] = (
    b"",
    b"http",
    b"/mcp",
    b"token",
    b"github-oauth",
    b"\xff\xfe\x00\x01",
    b"../../../../../tmp/notebooklm",
    b"https://example.com/%2f%2e%2e/%00",
)


def main() -> None:
    """Exercise fuzz targets with stable corpus seeds."""
    for seed in SEEDS:
        test_one_input(seed)


if __name__ == "__main__":
    main()
