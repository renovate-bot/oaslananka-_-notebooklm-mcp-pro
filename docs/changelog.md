# Changelog

The canonical changelog lives at:

```text
https://github.com/oaslananka/notebooklm-mcp-pro/blob/main/CHANGELOG.md
```

## 1.0.14

Patch release that syncs the freshest NotebookLM profile storage into the
configured auth file after `nlm-mcp login`, preventing stale auth JSON uploads
from Windows hosts to remote Docker deployments. Docker Compose also mounts the
auth directory read/write by default so refreshed cookies can be persisted.

## 1.0.13

Patch release that forwards NotebookLM auth settings through Docker Compose and
reports unreadable Docker-mounted auth files as sanitized authentication errors.

## 1.0.12

Patch release that makes the Docker runtime create appuser-owned data and config
directories before starting the server.

## 1.0.7

Patch release that suppresses external HTTP client INFO logs so expired
NotebookLM sessions cannot print auth redirect URLs to MCP client stderr.

## 1.0.6

Patch release that publishes PyPI artifacts directly from the self-hosted runner
with `uv publish`, preserving trusted publishing while avoiding Docker action
workspace mount mismatches.

## 1.0.5

Patch release that suppresses backend exception chaining when tool and resource
helpers convert failures into MCP-safe errors.

## 1.0.4

Patch release with NotebookLM auth resolution corrected so the newest canonical
auth file is selected, plus safer expired-session error mapping.

## 1.0.3

Patch release with the release workflow corrected so PyPI receives only wheel
and source distribution files before Sigstore bundles are generated.

## 1.0.2

Patch release with VS Code-compatible MCP tool names, public pull-request runner
hardening, OSPS evidence mapping, Security Insights metadata, governance files,
an expanded threat model, and architecture boundary linting.

## 1.0.1

Patch release with corrected NotebookLM login guidance for the installed
`notebooklm` CLI, safer quoted auth-file paths, and the latest hardening updates.

## 1.0.0

Production release with Streamable HTTP auth, OpenAPI integration, documentation, Docker and hosted deployment templates, and expanded tests.
