# Authentication

`notebooklm-mcp-pro` has two authentication layers:

- NotebookLM backend authentication, handled by `notebooklm-py`.
- HTTP transport authentication, handled by bearer tokens or GitHub OAuth.

Stdio mode does not add an MCP auth layer because it is local to the caller process.

## NotebookLM browser login

Run:

```bash
nlm-mcp login
```

The command starts the NotebookLM browser login and writes the configured auth
file. It uses `python -m notebooklm` internally, so it does not depend on the
`notebooklm` console script being available on `PATH`. The base package includes
the browser-login dependency, and `nlm-mcp login` installs the Playwright
Chromium browser binary before launching the NotebookLM login page.

To run the backend CLI directly:

```bash
python -m notebooklm --storage ~/.config/nlm-mcp/notebooklm_auth.json login
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\nlm-mcp"
python -m notebooklm --storage "$env:USERPROFILE\.config\nlm-mcp\notebooklm_auth.json" login
```

The browser login writes a storage-state JSON file. By default, this project reads:

```text
~/.config/nlm-mcp/notebooklm_auth.json
```

If that file is not present, the server also detects the NotebookLM CLI default
profile:

```text
~/.notebooklm/profiles/default/storage_state.json
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

Prefer the `Authorization` header for hosted clients. Some remote MCP clients
strip query strings while probing `/.well-known/*` discovery endpoints, so a URL
token can work in `curl` and still fail during connector creation.

## GitHub OAuth

Create a GitHub OAuth App:

1. Open GitHub Developer settings.
2. Create a new OAuth App.
3. Use `NotebookLM MCP` as the application name.
4. Set the homepage URL to `https://your-server.example.com`.
5. Set the callback URL to `https://your-server.example.com/auth/callback`.
6. Copy the client ID and client secret.

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

For the hosted MCP URL itself, keep the clean endpoint:

```text
https://your-server.example.com/mcp
```

Clients that support OAuth should discover:

```text
https://your-server.example.com/.well-known/oauth-protected-resource/mcp
```

Hosted MCP clients that support OAuth 2.1 authorization-code + PKCE can start
from the clean MCP endpoint:

```text
https://your-server.example.com/mcp
```

The server publishes authorization metadata at:

```text
https://your-server.example.com/.well-known/oauth-authorization-server
https://your-server.example.com/.well-known/openid-configuration
```

When `github-oauth` mode is enabled, the metadata advertises `/oauth/authorize`,
`/oauth/token`, and `/oauth/register`. The `/oauth/authorize` endpoint redirects
the user through GitHub, `/auth/callback` receives the GitHub response, and
`/oauth/token` exchanges the returned local code for a bearer access token after
PKCE verification.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `bearer_token required` | Set `NLM_MCP_BEARER_TOKEN` when `NLM_MCP_AUTH_MODE=token`. |
| `github_client_id required` | Set GitHub OAuth variables before starting OAuth mode. |
| Redirect URI mismatch | Make the GitHub app callback exactly match `NLM_MCP_BASE_URL + NLM_MCP_GITHUB_REDIRECT_PATH`. |
| NotebookLM login expired | Re-run `nlm-mcp login` and replace the mounted auth file with the path set in `NLM_MCP_NOTEBOOKLM_AUTH_FILE`, or `~/.config/nlm-mcp/notebooklm_auth.json` when unset. |
| `mixed-account cookies` or `account-routing mismatch` | Replace the server auth file with a clean `nlm-mcp login` output from the intended Google account. Do not merge old browser exports into the mounted file; a polluted file can list notebooks but fail on create/write RPCs. |
| Container cannot update auth file | Mount the auth directory read/write, or set `NLM_AUTH_MOUNT_MODE=rw` when using Docker Compose. |
