# Claude Desktop Integration

## stdio transport

Edit the desktop configuration file:

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

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

## With uv

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "uvx",
      "args": ["notebooklm-mcp-pro", "stdio"]
    }
  }
}
```

## Auth file override

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "nlm-mcp",
      "args": ["stdio"],
      "env": {
        "NLM_MCP_NOTEBOOKLM_AUTH_FILE": "/Users/me/.config/nlm-mcp/notebooklm_auth.json",
        "NLM_MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

## Verify

Restart the desktop app and ask:

```text
Run admin.health and list my NotebookLM notebooks.
```

## Common issues

| Problem | Resolution |
|---|---|
| Command not found | Use the absolute path from `which nlm-mcp` or `where nlm-mcp`. |
| Login expired | Run `notebooklm-py login` again. |
| No tools shown | Restart the desktop app after editing the config file. |
