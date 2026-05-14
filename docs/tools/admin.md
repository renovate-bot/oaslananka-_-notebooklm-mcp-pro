# Admin Tools

## admin.health

Returns local server health:

```json
{
  "status": "ok",
  "version": "1.0.1",
  "transport": "http",
  "auth_mode": "token"
}
```

## admin.version

Returns package, Python, and FastMCP versions.

## HTTP metadata

The HTTP app also serves:

- `GET /healthz`
- `GET /openapi.json`
- `GET /.well-known/ai-plugin.json`
- `GET /.well-known/oauth-protected-resource`
- `GET /.well-known/oauth-authorization-server`
