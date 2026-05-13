# Cursor Integration

Cursor can use local MCP commands. Install the package, authenticate NotebookLM, then add:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "nlm-mcp",
      "args": ["stdio"],
      "env": {
        "NLM_MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

Restart Cursor and run:

```text
List my notebooks and fetch the first source.
```

For teams, deploy Streamable HTTP and point Cursor to the remote `/mcp` endpoint if your Cursor build supports remote MCP URLs.
