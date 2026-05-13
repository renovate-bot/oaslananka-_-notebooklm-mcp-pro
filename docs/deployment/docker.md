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
  -v "$HOME/.config/nlm-mcp:/home/appuser/.config/nlm-mcp:ro" \
  notebooklm-mcp-pro:dev
```

## Docker Compose

```bash
docker compose -f deploy/docker-compose.yml up --build
```

## Health check

```bash
curl http://localhost:8080/healthz
```

## Pull from GHCR

```bash
docker pull ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```
