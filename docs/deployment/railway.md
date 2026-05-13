# Railway Deployment

## One-click style setup

Create a Railway project from the GitHub repository and set the Dockerfile path to:

```text
deploy/Dockerfile
```

## railway.json

The repository includes:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "deploy/Dockerfile"
  },
  "deploy": {
    "startCommand": "nlm-mcp serve",
    "healthcheckPath": "/healthz",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

## Environment variables

Set:

```bash
NLM_MCP_TRANSPORT=http
NLM_MCP_AUTH_MODE=token
NLM_MCP_BEARER_TOKEN=replace-with-generated-token
NLM_MCP_BASE_URL=https://your-service.up.railway.app
NLM_MCP_NOTEBOOKLM_AUTH_JSON={"cookies":[]}
```

## Custom domain

After adding a custom domain, update `NLM_MCP_BASE_URL` to the final HTTPS URL and redeploy.
