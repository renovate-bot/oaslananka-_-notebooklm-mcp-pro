# Configuration

Configuration precedence is:

1. CLI flags
2. Environment variables with the `NLM_MCP_` prefix
3. `.env` in the current working directory
4. Built-in defaults

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NLM_MCP_TRANSPORT` | `stdio` | `stdio` or `http`. |
| `NLM_MCP_HTTP_HOST` | `0.0.0.0` | HTTP bind address. |
| `NLM_MCP_HTTP_PORT` | `8080` | HTTP port. |
| `NLM_MCP_HTTP_PATH` | `/mcp` | Streamable HTTP MCP endpoint path. |
| `NLM_MCP_BASE_URL` | unset | Public base URL used in OpenAPI and OAuth redirects. |
| `NLM_MCP_STATELESS_HTTP` | `true` | Run FastMCP Streamable HTTP in stateless mode. |
| `NLM_MCP_AUTH_MODE` | `none` | `none`, `token`, or `github-oauth`. |
| `NLM_MCP_BEARER_TOKEN` | unset | Required when `AUTH_MODE=token`. |
| `NLM_MCP_TOKEN_QUERY_PARAM` | `token` | Query parameter used as token fallback. |
| `NLM_MCP_GITHUB_CLIENT_ID` | unset | GitHub OAuth client ID. |
| `NLM_MCP_GITHUB_CLIENT_SECRET` | unset | GitHub OAuth client secret. |
| `NLM_MCP_GITHUB_REDIRECT_PATH` | `/auth/callback` | OAuth callback path. |
| `NLM_MCP_OAUTH_REQUIRED_SCOPES` | `read:user,user:email` | GitHub OAuth scopes. |
| `NLM_MCP_OAUTH_ALLOWED_USERS` | unset | Comma-separated GitHub usernames allowed to log in. |
| `NLM_MCP_NOTEBOOKLM_AUTH_JSON` | unset | Inline NotebookLM storage-state JSON. |
| `NLM_MCP_NOTEBOOKLM_AUTH_FILE` | `~/.config/nlm-mcp/notebooklm_auth.json` | NotebookLM auth file path. |
| `NLM_MCP_DEFAULT_LANGUAGE` | `en` | Default generated artifact language. |
| `NLM_MCP_DATA_DIR` | `~/.local/share/nlm-mcp` | Data directory for sessions, tasks, artifacts, and audit logs. |
| `NLM_MCP_SESSION_DB` | derived | SQLite URL for session storage. |
| `NLM_MCP_ENCRYPTION_KEY` | unset | Reserved for encrypted storage backends. |
| `NLM_MCP_REDIS_URL` | unset | Reserved for distributed rate limiting. |
| `NLM_MCP_RATE_LIMIT_ENABLED` | `true` | Enable local rate limiting. |
| `NLM_MCP_RATE_LIMIT_PER_USER_RPM` | `60` | Per-user requests per minute. |
| `NLM_MCP_RATE_LIMIT_GENERATE_RPM` | `10` | Per-user generation requests per minute. |
| `NLM_MCP_LOG_LEVEL` | `INFO` | Python log level. |
| `NLM_MCP_LOG_FORMAT` | `json` | `json` or `console`. |
| `NLM_MCP_AUDIT_LOG_PATH` | `{DATA_DIR}/audit.log` | Audit log path. |
| `NLM_MCP_DESTRUCTIVE_REQUIRES_CONFIRM` | `true` | Require `confirm=true` for destructive operations. |
| `NLM_MCP_DEFAULT_POLL_INTERVAL_SEC` | `15` | Default polling interval. |
| `NLM_MCP_DEFAULT_POLL_TIMEOUT_SEC` | `600` | Default polling timeout. |

## Example `.env`

```bash
NLM_MCP_TRANSPORT=http
NLM_MCP_AUTH_MODE=token
NLM_MCP_BEARER_TOKEN=replace-with-generated-token
NLM_MCP_BASE_URL=https://notebooklm.example.com
NLM_MCP_NOTEBOOKLM_AUTH_FILE=/run/secrets/notebooklm_auth.json
NLM_MCP_LOG_FORMAT=json
```

## TOML-style settings

The application validates settings through Pydantic. Invalid combinations fail at startup, for example `auth_mode=token` without `bearer_token` or `auth_mode=github-oauth` without a GitHub client ID and secret.
