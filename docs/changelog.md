# Changelog

The canonical changelog lives at:

```text
https://github.com/oaslananka/notebooklm-mcp-pro/blob/main/CHANGELOG.md
```

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
