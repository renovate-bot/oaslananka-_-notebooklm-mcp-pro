# ChatGPT Custom Actions

ChatGPT Custom Actions can import an OpenAPI schema. `notebooklm-mcp-pro` exposes:

```text
GET /openapi.json
GET /.well-known/ai-plugin.json
POST /tools/{tool_name}
```

## Deploy the server

```bash
docker run --rm -p 8080:8080 \
  -e NLM_MCP_AUTH_MODE=token \
  -e NLM_MCP_BEARER_TOKEN=replace-with-generated-token \
  -e NLM_MCP_BASE_URL=https://your-server.example.com \
  ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```

## Import the schema

1. Create or edit a GPT.
2. Open Actions.
3. Import from URL.
4. Enter `https://your-server.example.com/openapi.json`.
5. Set authentication to bearer token.
6. Save.

## Test prompt

```text
List my NotebookLM notebooks and summarize the first notebook's sources.
```

The action should call `notebook.list`, `source.list`, and `fetch`.

## Notes

- Binary downloads return a local server path when running where the server can write files.
- Long artifact generation should use `artifact.status` or `artifact.wait`.
- The `search` and `fetch` tools return the shape expected by ChatGPT knowledge connectors.
