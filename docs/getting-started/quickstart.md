# Quickstart

## Local stdio

```bash
pip install notebooklm-mcp-pro
nlm-mcp login
nlm-mcp stdio
```

Use `nlm-mcp stdio` in local MCP clients that launch a command and communicate over standard input/output.

## Remote HTTP with bearer token

```bash
export NLM_MCP_TRANSPORT=http
export NLM_MCP_AUTH_MODE=token
export NLM_MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export NLM_MCP_BASE_URL=https://your-server.example.com
nlm-mcp serve --host 0.0.0.0 --port 8080
```

Health and metadata endpoints:

```bash
curl https://your-server.example.com/healthz
curl https://your-server.example.com/openapi.json
curl https://your-server.example.com/.well-known/ai-plugin.json
```

## Remote HTTP with GitHub OAuth

```bash
export NLM_MCP_AUTH_MODE=github-oauth
export NLM_MCP_GITHUB_CLIENT_ID=...
export NLM_MCP_GITHUB_CLIENT_SECRET=...
export NLM_MCP_BASE_URL=https://your-server.example.com
nlm-mcp serve
```

Visit `/auth/login`, complete GitHub login, then connect the MCP client to `/mcp`.

## First useful prompt

Ask your MCP client:

```text
List my NotebookLM notebooks, then fetch the sources in the first notebook.
```

The expected tool sequence is `notebook_list`, `source_list`, and optionally `fetch`.
