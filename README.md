# notebooklm-mcp-pro

Production-grade Model Context Protocol server for Google NotebookLM with local stdio and remote Streamable HTTP transports.

[![CI](https://github.com/oaslananka-lab/notebooklm-mcp-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/oaslananka-lab/notebooklm-mcp-pro/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

This repository is being built as a Python-only MCP server backed by `notebooklm-py` and FastMCP. The first public release will include typed NotebookLM tools, resources, prompts, Streamable HTTP authentication, deployment templates, and a complete documentation site.

FastMCP 3.x is used because the current 2.x dependency graph pulls a critical vulnerable cache package with no fixed release available.

## Quickstart

```bash
make bootstrap
make test
make run-stdio
```

## Status

The server now provides the FastMCP factory, validated settings, structured logging, stdio transport wiring, admin tools, a `notebooklm-py` backend wrapper, and the core notebook, source, chat, `search`, and `fetch` tool families. Artifact generation, remote authentication, UI resources, deployment templates, and full documentation are added in the subsequent implementation milestones.

## License

MIT. See [LICENSE](LICENSE).
