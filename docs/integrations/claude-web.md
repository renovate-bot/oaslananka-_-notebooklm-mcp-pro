# Claude.ai Web Integration

Claude.ai supports remote MCP servers over Streamable HTTP. Use this mode when the MCP server is deployed at a public HTTPS URL.

## Prerequisites

- A running `notebooklm-mcp-pro` HTTP server.
- A public HTTPS URL.
- Bearer token or GitHub OAuth authentication.

## Add the MCP server

1. Open Settings.
2. Open Integrations.
3. Add an MCP server.
4. Enter `https://your-server.example.com/mcp`.
5. Choose bearer token or OAuth, matching the server configuration.
6. Save and test with `admin_health`.

## Railway smoke test

Deploy the Docker image, set environment variables, then use the generated domain:

```text
https://your-service.up.railway.app/mcp
```

## Security note

Do not run public remote MCP without authentication. Use `auth_mode=token` for personal deployments and `auth_mode=github-oauth` for multiple users.
