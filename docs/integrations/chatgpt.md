# ChatGPT Custom Actions and Apps

ChatGPT can reach `notebooklm-mcp-pro` in two ways:

- Custom GPT Actions import the OpenAPI schema.
- ChatGPT Apps / remote MCP connectors connect directly to the Streamable HTTP endpoint.

`notebooklm-mcp-pro` exposes:

```text
GET /openapi.json
GET /.well-known/ai-plugin.json
GET /.well-known/oauth-protected-resource
GET /.well-known/oauth-protected-resource/mcp
GET /.well-known/oauth-authorization-server
GET /oauth/authorize
POST /oauth/token
POST /oauth/register
POST /tools/{tool_name}
POST /mcp
```

## Deploy the server

```bash
docker run --rm -p 8080:8080 \
  -e NLM_MCP_AUTH_MODE=token \
  -e NLM_MCP_BEARER_TOKEN=replace-with-generated-token \
  -e NLM_MCP_BASE_URL=https://your-server.example.com \
  ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```

## Remote MCP app setup

Use the Streamable HTTP endpoint as the MCP server URL:

```text
https://your-server.example.com/mcp
```

Do not put the bearer token in the MCP server URL. Some hosted clients normalize
or strip query strings during MCP discovery, which means a URL such as
`https://your-server.example.com/mcp?token=...` can fail even though `curl` works.

For token mode, choose bearer/API-key authentication in the client UI and paste
only the token value. The server accepts the standard header:

```http
Authorization: Bearer replace-with-generated-token
```

The unauthenticated `/mcp` response advertises the protected resource metadata
location through `WWW-Authenticate`, and both root and path-aware metadata URLs
are public:

```text
https://your-server.example.com/.well-known/oauth-protected-resource
https://your-server.example.com/.well-known/oauth-protected-resource/mcp
```

## OpenAPI action setup

1. Create or edit a GPT.
2. Open Actions.
3. Import from URL.
4. Enter `https://your-server.example.com/openapi.json`.
5. Set authentication to bearer token.
6. Paste the bearer token value, not a full `Bearer ...` header.
7. Save.

## GitHub OAuth option

For hosted MCP clients that support OAuth 2.1 authorization-code + PKCE, run the
server in GitHub OAuth mode. The server acts as a small authorization server for
the MCP client and uses GitHub OAuth as the upstream identity provider.

Register a GitHub OAuth App:

| GitHub OAuth App field | Value |
|---|---|
| Application name | `NotebookLM MCP` |
| Homepage URL | `https://your-server.example.com` |
| Application description | `NotebookLM MCP server for secure remote MCP access.` |
| Authorization callback URL | `https://your-server.example.com/auth/callback` |

Then configure the server:

```bash
export NLM_MCP_TRANSPORT=http
export NLM_MCP_AUTH_MODE=github-oauth
export NLM_MCP_BASE_URL=https://your-server.example.com
export NLM_MCP_GITHUB_CLIENT_ID=your-client-id
export NLM_MCP_GITHUB_CLIENT_SECRET=your-client-secret
export NLM_MCP_OAUTH_ALLOWED_USERS=your-github-login
nlm-mcp serve --host 0.0.0.0 --port 8080
```

Use this MCP server URL:

```text
https://your-server.example.com/mcp
```

The server publishes:

```text
https://your-server.example.com/.well-known/oauth-protected-resource/mcp
https://your-server.example.com/.well-known/oauth-authorization-server
```

The OAuth bridge supports dynamic client registration, PKCE S256, authorization
code exchange, and local bearer access tokens scoped to the protected MCP
resource. Browser clients may still start directly at `/auth/login`; hosted MCP
clients should start from the clean `/mcp` connector URL and follow discovery.

## Test prompt

```text
List my NotebookLM notebooks and summarize the first notebook's sources.
```

The action should call `notebook_list`, `source_list`, and `fetch`.

## Notes

- OpenAPI URL paths keep canonical dotted names such as `/tools/notebook.list`;
  generated operation IDs and MCP-visible tool names use underscores for strict
  client compatibility.
- Binary downloads return a local server path when running where the server can write files.
- Long artifact generation should use `artifact_status` or `artifact_wait`.
- The `search` and `fetch` tools return the shape expected by ChatGPT knowledge connectors.
- A `401` from `/mcp` is expected until the client sends bearer auth or completes OAuth.
- A timeout from `/healthz` or `/openapi.json` is not an auth issue; restart the container and
  check the reverse proxy before retrying client setup.
