# VS Code Continue Integration

Use stdio for local development:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "nlm-mcp",
      "args": ["stdio"]
    }
  }
}
```

For remote HTTP, configure the client to connect to:

```text
https://your-server.example.com/mcp
```

Set bearer token authentication when the server uses `NLM_MCP_AUTH_MODE=token`.

Verify with:

```text
Run admin.version, then search NotebookLM records for "project".
```
