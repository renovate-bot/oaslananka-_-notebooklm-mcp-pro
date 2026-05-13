# Self-hosted Deployment

## systemd service

Create `/etc/systemd/system/notebooklm-mcp-pro.service`:

```ini
[Unit]
Description=NotebookLM MCP Server
After=network-online.target

[Service]
User=nlm-mcp
EnvironmentFile=/etc/notebooklm-mcp-pro.env
ExecStart=/usr/local/bin/nlm-mcp serve --host 127.0.0.1 --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Reverse proxy

Terminate TLS at Caddy, nginx, or a managed load balancer. Forward `/mcp`, `/healthz`, `/openapi.json`, and `/.well-known/*` to the service.

## Backup

Back up:

- `NLM_MCP_DATA_DIR`
- NotebookLM auth file
- Environment file or secret manager entries
