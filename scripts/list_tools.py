#!/usr/bin/env python3
"""Print a Markdown catalog of registered MCP tools, resources, and prompts."""

from __future__ import annotations

import asyncio
from typing import Any

from nlm_mcp.config import Settings
from nlm_mcp.server import create_server


async def main() -> None:
    """Render the server registry as Markdown."""
    server = create_server(Settings())
    tools = await server.list_tools()
    resources = await server.list_resources()
    templates = await server.list_resource_templates()
    prompts = await server.list_prompts()

    print("# Tool Catalog\n")
    print("| Tool Name | Title | Read-only | Destructive | Description |")
    print("|---|---|---:|---:|---|")
    for tool in sorted(tools, key=lambda item: item.name):
        annotations = tool.annotations
        print(
            "| {name} | {title} | {read_only} | {destructive} | {description} |".format(
                name=tool.name,
                title=_cell(tool.title or ""),
                read_only=_bool(getattr(annotations, "readOnlyHint", False)),
                destructive=_bool(getattr(annotations, "destructiveHint", False)),
                description=_cell(tool.description or ""),
            )
        )

    print("\n## Resources\n")
    print("| URI | Name | Description |")
    print("|---|---|---|")
    for resource in resources:
        print(
            f"| {resource.uri} | {_cell(resource.name or '')} | "
            f"{_cell(resource.description or '')} |"
        )

    print("\n## Resource Templates\n")
    print("| Template | Name | Description |")
    print("|---|---|---|")
    for template in templates:
        uri_template = getattr(template, "uriTemplate", None) or getattr(
            template, "uri_template", ""
        )
        print(
            f"| {uri_template} | {_cell(template.name or '')} | "
            f"{_cell(template.description or '')} |"
        )

    print("\n## Prompts\n")
    print("| Prompt | Title | Description |")
    print("|---|---|---|")
    for prompt in sorted(prompts, key=lambda item: item.name):
        print(
            f"| {prompt.name} | {_cell(prompt.title or '')} | {_cell(prompt.description or '')} |"
        )


def _bool(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    asyncio.run(main())
