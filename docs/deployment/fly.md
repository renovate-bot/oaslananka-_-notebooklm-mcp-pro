# Fly.io Deployment

## Initialize

```bash
fly launch --no-deploy
```

Use `deploy/fly.toml` as the app template.

## Secrets

```bash
fly secrets set NLM_MCP_AUTH_MODE=token
fly secrets set NLM_MCP_BEARER_TOKEN=replace-with-generated-token
fly secrets set NLM_MCP_NOTEBOOKLM_AUTH_JSON='{"cookies":[]}'
fly secrets set NLM_MCP_BASE_URL=https://notebooklm-mcp-pro.fly.dev
```

## Deploy

```bash
fly deploy --config deploy/fly.toml
```

## Check

```bash
curl https://notebooklm-mcp-pro.fly.dev/healthz
```
