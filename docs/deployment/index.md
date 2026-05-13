# Deployment Overview

Deploy `notebooklm-mcp-pro` wherever Python 3.11+ or containers are available.

## Recommended modes

| Scenario | Transport | Auth |
|---|---|---|
| Local desktop | stdio | none |
| Personal remote | HTTP | bearer token |
| Team remote | HTTP | GitHub OAuth |

## Required production settings

```bash
NLM_MCP_TRANSPORT=http
NLM_MCP_BASE_URL=https://your-server.example.com
NLM_MCP_AUTH_MODE=token
NLM_MCP_BEARER_TOKEN=replace-with-generated-token
NLM_MCP_NOTEBOOKLM_AUTH_JSON='{"cookies":[]}'
```

Use HTTPS at the edge and keep the NotebookLM auth JSON in a secret manager.
