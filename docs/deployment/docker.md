# Docker Deployment

## Build

```bash
docker build -f deploy/Dockerfile -t notebooklm-mcp-pro:dev .
```

## Run HTTP transport

```bash
docker run --rm -p 8080:8080 \
  -e NLM_MCP_TRANSPORT=http \
  -e NLM_MCP_AUTH_MODE=token \
  -e NLM_MCP_BEARER_TOKEN=replace-with-generated-token \
  -e NLM_MCP_BASE_URL=http://localhost:8080 \
  notebooklm-mcp-pro:dev
```

## Mount auth file

```bash
docker run --rm -p 8080:8080 \
  -v "$HOME/.config/nlm-mcp:/home/appuser/.config/nlm-mcp:rw" \
  notebooklm-mcp-pro:dev
```

The runtime container runs as UID `10001`. If the host auth file is `0600`
under your user account, grant read/write access to that UID or use inline JSON
instead. A writable mount lets `notebooklm-py` persist refreshed cookies:

```bash
setfacl -m u:10001:rx "$HOME/.config" "$HOME/.config/nlm-mcp"
setfacl -m u:10001:rw "$HOME/.config/nlm-mcp/notebooklm_auth.json"
```

For hosted deployments, inline JSON is usually simpler because it avoids bind
mount permissions:

```bash
export NLM_MCP_NOTEBOOKLM_AUTH_JSON="$(cat "$HOME/.config/nlm-mcp/notebooklm_auth.json")"
docker run --rm -p 8080:8080 \
  -e NLM_MCP_TRANSPORT=http \
  -e NLM_MCP_AUTH_MODE=github-oauth \
  -e NLM_MCP_NOTEBOOKLM_AUTH_JSON \
  notebooklm-mcp-pro:dev
```

## Docker Compose

```bash
docker compose -f deploy/docker-compose.yml up --build
```

`deploy/docker-compose.yml` forwards both `NLM_MCP_NOTEBOOKLM_AUTH_FILE` and
`NLM_MCP_NOTEBOOKLM_AUTH_JSON`. Use `NLM_AUTH_FILE` only for the host mount
source path; use `NLM_MCP_NOTEBOOKLM_AUTH_FILE` for the path seen by the
application inside the container. The default auth mount mode is `rw`; set
`NLM_AUTH_MOUNT_MODE=ro` only for immutable deployments where refresh warnings
are acceptable.

## Health check

```bash
curl http://localhost:8080/healthz
```

## Pull from GHCR

```bash
docker pull ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```
