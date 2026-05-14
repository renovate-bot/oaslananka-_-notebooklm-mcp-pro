# Authentication

`notebooklm-mcp-pro` has two authentication layers:

- NotebookLM backend authentication, handled by `notebooklm-py`.
- HTTP transport authentication, handled by bearer tokens or GitHub OAuth.

Stdio mode does not add an MCP auth layer because it is local to the caller process.

## NotebookLM browser login

Run:

```bash
python -m notebooklm login --storage ~/.config/nlm-mcp/notebooklm_auth.json
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\nlm-mcp"
python -m notebooklm login --storage "$env:USERPROFILE\.config\nlm-mcp\notebooklm_auth.json"
```

The browser login writes a storage-state JSON file. By default, this project reads:

```text
~/.config/nlm-mcp/notebooklm_auth.json
```

Override it with:

```bash
export NLM_MCP_NOTEBOOKLM_AUTH_FILE=/secure/path/notebooklm_auth.json
```

## Inline auth JSON

For containers and hosted services, inject the JSON directly:

```bash
export NLM_MCP_NOTEBOOKLM_AUTH_JSON='{"cookies":[],"origins":[]}'
```

Treat this value as a secret. Do not commit it, print it, or put it in an image layer.

## HTTP bearer token auth

Generate a token:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run the server:

```bash
export NLM_MCP_TRANSPORT=http
export NLM_MCP_AUTH_MODE=token
export NLM_MCP_BEARER_TOKEN=replace-with-generated-token
nlm-mcp serve --host 0.0.0.0 --port 8080
```

Clients can authenticate with a header:

```bash
curl -H "Authorization: Bearer replace-with-generated-token" \
  http://127.0.0.1:8080/mcp
```

The server also accepts a query token for simple hosted setups:

```text
https://your-server.example.com/mcp?token=replace-with-generated-token
```

## GitHub OAuth

Create a GitHub OAuth App:

1. Open GitHub Developer settings.
2. Create a new OAuth App.
3. Set the callback URL to `https://your-server.example.com/auth/callback`.
4. Copy the client ID and client secret.

Configure the server:

```bash
export NLM_MCP_TRANSPORT=http
export NLM_MCP_AUTH_MODE=github-oauth
export NLM_MCP_BASE_URL=https://your-server.example.com
export NLM_MCP_GITHUB_CLIENT_ID=your-client-id
export NLM_MCP_GITHUB_CLIENT_SECRET=your-client-secret
export NLM_MCP_OAUTH_ALLOWED_USERS=oaslananka
nlm-mcp serve --host 0.0.0.0 --port 8080
```

Users authenticate at:

```text
https://your-server.example.com/auth/login
```

The callback stores a 24-hour local session token in SQLite and sends it as a secure, HTTP-only cookie when the public URL uses HTTPS.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `bearer_token required` | Set `NLM_MCP_BEARER_TOKEN` when `NLM_MCP_AUTH_MODE=token`. |
| `github_client_id required` | Set GitHub OAuth variables before starting OAuth mode. |
| Redirect URI mismatch | Make the GitHub app callback exactly match `NLM_MCP_BASE_URL + NLM_MCP_GITHUB_REDIRECT_PATH`. |
| NotebookLM login expired | Re-run `python -m notebooklm login --storage <path>` and replace the mounted auth file. |
| Container cannot read auth file | Mount the file read-only and ensure the container user can read it. |
