#!/usr/bin/env python3
"""Validate imports across nlm_mcp architecture layers."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "nlm_mcp"
PACKAGE = "nlm_mcp"
BACKEND = f"{PACKAGE}.backend"
CONFIG = f"{PACKAGE}.config"
AUTH = f"{PACKAGE}.auth"
TOOLS = f"{PACKAGE}.tools"
RESOURCES = f"{PACKAGE}.resources"
PROMPTS = f"{PACKAGE}.prompts"
SERVER = f"{PACKAGE}.server"
TRANSPORT = f"{PACKAGE}.transport"
UI = f"{PACKAGE}.ui"
PUBLIC_ROOT_SYMBOLS = {f"{PACKAGE}.__version__"}

ALLOWED_PREFIXES: dict[str, set[str]] = {
    "backend": {BACKEND, CONFIG},
    "auth": {AUTH, CONFIG},
    "tools": {BACKEND, CONFIG, TOOLS},
    "resources": {BACKEND, RESOURCES, TOOLS},
    "prompts": {PROMPTS},
    "transport": {CONFIG, SERVER, TRANSPORT},
    "ui": {UI},
}


def _layer(path: Path) -> str | None:
    try:
        relative = path.relative_to(SRC)
    except ValueError:
        return None
    first = relative.parts[0]
    if first.endswith(".py"):
        return first.removesuffix(".py")
    return first


def _module_name(path: Path) -> str:
    relative = path.relative_to(SRC).with_suffix("")
    parts = (PACKAGE, *relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_relative_import(path: Path, node: ast.ImportFrom) -> str:
    current_package = _module_name(path).split(".")
    if path.name != "__init__.py":
        current_package = current_package[:-1]
    base_length = max(1, len(current_package) - node.level + 1)
    base = ".".join(current_package[:base_length])
    if node.module:
        return f"{base}.{node.module}"
    return base


def _imports(path: Path, tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_relative_import(path, node) if node.level else node.module
            if module is None:
                continue
            if module == PACKAGE:
                imports.extend(f"{PACKAGE}.{alias.name}" for alias in node.names)
            else:
                imports.append(module)
    return [name for name in imports if name == PACKAGE or name.startswith(f"{PACKAGE}.")]


def _allowed(layer: str, imported: str) -> bool:
    if imported in PUBLIC_ROOT_SYMBOLS:
        return True
    allowed = ALLOWED_PREFIXES.get(layer)
    if allowed is None:
        return True
    return any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in allowed)


def main() -> int:
    """Return non-zero when an import crosses a forbidden architecture boundary."""
    violations: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        layer = _layer(path)
        if layer is None:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imports(path, tree):
            if not _allowed(layer, imported):
                relative = path.relative_to(ROOT).as_posix()
                violations.append(f"{relative}: {layer} must not import {imported}")
    if violations:
        print("Architecture boundary violations:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
