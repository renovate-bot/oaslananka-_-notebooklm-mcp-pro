# notebooklm-mcp-pro

**Production-grade [Model Context Protocol](https://modelcontextprotocol.io) server for [Google NotebookLM](https://notebooklm.google.com).**

[![CI](https://github.com/oaslananka/notebooklm-mcp-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/oaslananka/notebooklm-mcp-pro/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/notebooklm-mcp-pro.svg)](https://pypi.org/project/notebooklm-mcp-pro/)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue.svg)](https://pypi.org/project/notebooklm-mcp-pro/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/oaslananka/notebooklm-mcp-pro/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-92%25+-brightgreen.svg)](https://github.com/oaslananka/notebooklm-mcp-pro/actions)

`notebooklm-mcp-pro` connects MCP-compatible clients to Google NotebookLM through one Python package. It supports local stdio transport for desktop clients and Streamable HTTP for remote integrations, including bearer token and GitHub OAuth authentication.

## What you can do

| Category | Tools |
|---|---|
| Notebooks | List, create, rename, delete, share publicly, invite collaborators |
| Sources | Add URLs, YouTube videos, files, Google Drive docs, and pasted text |
| Chat | Ask questions, continue conversations, save notes, list notes |
| Research | Start web or Drive research, poll status, wait for completion |
| Artifacts | Generate audio, video, cinematic video, slides, infographics, reports, tables, quizzes, flashcards, and mind maps |
| Language | List supported languages and set the account-global output language |
| Admin | Health, version, OpenAPI, plugin manifest, OAuth metadata |

## 60-second start

=== "pip"
    ```bash
    pip install notebooklm-mcp-pro
    notebooklm-py login
    nlm-mcp stdio
    ```

=== "uv"
    ```bash
    uv tool install notebooklm-mcp-pro
    notebooklm-py login
    nlm-mcp stdio
    ```

=== "Docker"
    ```bash
    docker run --rm -p 8080:8080 \
      -e NLM_MCP_TRANSPORT=http \
      -e NLM_MCP_AUTH_MODE=token \
      -e NLM_MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
      ghcr.io/oaslananka/notebooklm-mcp-pro:latest
    ```

## Choose your integration

- [Claude Desktop](integrations/claude-desktop.md)
- [Claude.ai Web](integrations/claude-web.md)
- [ChatGPT Custom Actions](integrations/chatgpt.md)
- [Cursor](integrations/cursor.md)
- [VS Code Continue](integrations/vscode.md)

## Architecture

```mermaid
flowchart LR
  Client["MCP or OpenAPI client"] --> Transport["stdio or Streamable HTTP"]
  Transport --> Auth["none, bearer token, or GitHub OAuth"]
  Auth --> Server["FastMCP server"]
  Server --> Tools["NotebookLM tools, resources, prompts"]
  Tools --> Backend["notebooklm-py async client"]
  Backend --> NotebookLM["Google NotebookLM"]
  Server --> Store["SQLite task/session store"]
```

## Next steps

Read [Installation](getting-started/installation.md), configure [Authentication](getting-started/authentication.md), and use the [Tools Reference](tools/notebooks.md) to map client prompts to tool calls.
