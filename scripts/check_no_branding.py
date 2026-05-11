"""Guard repository artifacts against disallowed attribution strings."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_FORBIDDEN = (
    "Generated " + "by",
    "AI-" + "assisted",
    "built with " + "AI",
    "vibe " + "coded",
    "as an " + "assistant",
)

SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "htmlcov",
    "site",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".dockerfile",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def iter_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_PARTS.intersection(path.relative_to(root).parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Makefile", "Dockerfile"}:
            paths.append(path)
    return paths


def find_forbidden(root: Path, forbidden: tuple[str, ...]) -> list[str]:
    findings: list[str] = []
    patterns = [re.compile(re.escape(term), re.IGNORECASE) for term in forbidden]
    for path in iter_files(root):
        with path.open(encoding="utf-8", errors="ignore") as handle:
            for line_number, line in enumerate(handle, start=1):
                for pattern in patterns:
                    if pattern.search(line):
                        findings.append(f"{path}:{line_number}: {pattern.pattern}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument(
        "--forbid",
        action="append",
        default=[],
        help="Additional forbidden phrase.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    forbidden = (*DEFAULT_FORBIDDEN, *tuple(args.forbid))
    findings = find_forbidden(root, forbidden)
    if findings:
        sys.stderr.write("Forbidden attribution strings found:\n")
        sys.stderr.write("\n".join(findings))
        sys.stderr.write("\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
