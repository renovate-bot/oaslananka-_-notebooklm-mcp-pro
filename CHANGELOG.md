# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-05-13

### Added

- Full HTTP bearer token authentication with header and query parameter support.
- GitHub OAuth authentication with local SQLite session storage.
- OpenAPI 3.1 schema endpoint at `GET /openapi.json`.
- ChatGPT plugin manifest at `GET /.well-known/ai-plugin.json`.
- OAuth protected resource and authorization server metadata endpoints.
- OpenAPI tool action endpoint at `POST /tools/{tool_name}`.
- Complete MkDocs Material documentation site.
- Claude Desktop, Claude.ai Web, ChatGPT, Cursor, and VS Code integration guides.
- Docker Compose, Railway, Fly.io, Kubernetes, and self-hosted deployment templates.
- Multi-stage Dockerfile with uv-based build and non-root runtime user.
- SBOM generation in the release workflow.
- PyPI publish and GHCR Docker push in the release workflow.
- Codecov coverage reporting in CI.
- `notebooklm-mcp-pro[all]` extra for full optional install.
- Dedicated tests for HTTP auth, OAuth, OpenAPI, compatibility tools, and language tools.

### Changed

- Bumped package version to `1.0.0`.
- Marked the package as production/stable.
- Updated package metadata and documentation URLs to `oaslananka/notebooklm-mcp-pro`.
- Raised coverage enforcement to 92%.
- `serve` no longer rejects `auth_mode=token` or `auth_mode=github-oauth`.

### Fixed

- Auth middleware bypasses health, OpenAPI, plugin manifest, OAuth metadata, and OAuth callback endpoints.
- Artifact downloads reject absolute paths and parent traversal.
- Research wait handles failed terminal states and task ID filtering.

## [0.4.0] - 2026-05-12

### Added

- Artifact lifecycle tools: `artifact.list`, `artifact.status`, `artifact.wait`, `artifact.download`, and `artifact.revise_slide`.
- Language tools: `language.list`, `language.get`, and `language.set`.
- Research tools: `research.web_start`, `research.drive_start`, `research.status`, and `research.wait`.
- SQLite-backed task tracking for generated artifacts.
- MCP resources for artifact tasks and mind maps.
- Prompt templates for study packs, research summaries, meeting podcasts, and paper deep dives.

## [0.3.0] - 2026-05-12

### Added

- Notebook, source, chat, resource, and compatibility tools.
- ChatGPT-compatible `search` and `fetch`.

## [0.2.0] - 2026-05-12

### Added

- NotebookLM backend wrapper, retry policies, and exception mapping.

## [0.1.0] - 2026-05-12

### Added

- Core FastMCP server factory, CLI, settings, logging, and admin tools.

## [0.0.1] - 2026-05-12

### Added

- Initial repository scaffold, CI, security workflows, and packaging metadata.
