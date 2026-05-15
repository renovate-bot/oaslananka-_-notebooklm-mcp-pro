# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.13] - 2026-05-15

### Fixed

- Docker Compose now forwards NotebookLM auth file, inline auth JSON, and default
  language environment variables into the container.
- `nlm-mcp doctor` now reports unreadable NotebookLM auth files as sanitized
  authentication errors instead of raising a `PermissionError` traceback.

### Documentation

- Documented Docker auth-file permissions for the non-root runtime user and the
  inline JSON deployment path for hosted environments.

## [1.0.12] - 2026-05-15

### Fixed

- Ensured the Docker runtime image creates appuser-owned NotebookLM MCP data and
  config directories so OAuth session SQLite storage can be opened on fresh
  named-volume deployments.

## [1.0.11] - 2026-05-15

### Added

- Added a GitHub-backed OAuth authorization-code bridge for hosted MCP clients.
  The server now exposes `/oauth/authorize`, `/oauth/token`, and
  `/oauth/register` when `NLM_MCP_AUTH_MODE=github-oauth`.
- Added PKCE S256 verification and local bearer-token issuance for ChatGPT-style
  OAuth connector flows.
- Docker Compose now forwards GitHub OAuth environment variables into the
  container.

### Changed

- OAuth authorization-server metadata now advertises the real authorization,
  token, and dynamic client registration endpoints instead of the GitHub callback
  endpoint.

## [1.0.10] - 2026-05-15

### Fixed

- Removed the obsolete top-level Docker Compose `version` key so `docker compose`
  deploys without deprecation warnings on current Compose releases.
- `nlm-mcp login` now installs the Playwright Chromium browser binary before
  launching the NotebookLM login flow.
- The base package now includes the Playwright Python dependency so the documented
  plain install path supports `nlm-mcp login`.

## [1.0.9] - 2026-05-15

### Fixed

- `nlm-mcp login` now starts the NotebookLM browser-login flow directly through
  `python -m notebooklm`, avoiding PATH issues on Windows where users may try
  the package name `notebooklm-py` as a command.
- Updated Docker image metadata so the OCI version label matches the released
  package version.

### Documentation

- Documented `nlm-mcp login` as the primary NotebookLM authentication command
  and clarified that `notebooklm-py` is the package name while `notebooklm` is
  the dependency CLI command.

## [1.0.8] - 2026-05-15

### Fixed

- Added path-aware RFC 9728 protected-resource metadata at
  `/.well-known/oauth-protected-resource/mcp` so hosted MCP clients can discover
  authorization requirements for the Streamable HTTP endpoint.
- Added a `resource_metadata` hint to `/mcp` bearer-token challenges when
  `NLM_MCP_BASE_URL` is configured.
- Fixed HTTP auth middleware receive handling so authenticated Streamable HTTP
  requests cannot spin the event loop after the request body has been forwarded.

### Documentation

- Clarified ChatGPT remote MCP setup: use a clean `/mcp` URL and configure bearer
  or OAuth authentication in the client instead of relying on `?token=` URLs.
- Added exact GitHub OAuth App registration values for hosted deployments.

## [1.0.7] - 2026-05-14

### Fixed

- Suppressed INFO-level `httpx` and `httpcore` request logging so expired NotebookLM sessions cannot print Google auth redirect URLs to MCP client stderr.

## [1.0.6] - 2026-05-14

### Fixed

- Release workflow now publishes to PyPI with `uv publish` on the self-hosted runner, avoiding Docker-action workspace mount mismatches while preserving trusted publishing.
- Added an explicit wheel and source distribution check before SBOM generation, attestation, container publishing, PyPI publishing, and release asset signing.

## [1.0.5] - 2026-05-14

### Fixed

- Suppressed chained backend exception context when converting tool and resource failures to MCP-safe `ToolError` and `ResourceError` responses, preventing upstream auth redirect URLs or internal payloads from being formatted into client-side tracebacks.

## [1.0.4] - 2026-05-14

### Fixed

- NotebookLM auth resolution now selects the newest existing canonical auth file when both the active `notebooklm` CLI profile and the legacy project default path exist, preventing stale auth files from shadowing a fresh login.
- Expired NotebookLM sessions reported by `notebooklm-py` as auth redirect errors now map to MCP auth error code `-32002` with a safe storage-neutral re-authentication message.

## [1.0.3] - 2026-05-14

### Fixed

- Release workflow now publishes only wheel and source distribution files to PyPI before generating Sigstore bundle files.
- Build provenance attestations now target the wheel, source distribution, and SBOM explicitly instead of every file under `dist/`.

## [1.0.2] - 2026-05-14

### Added

- OpenSSF Security Insights metadata for repository security posture discovery.
- OSPS Baseline evidence mapping for release, security, governance, and CI controls.
- Governance and maintainer policy documents with sensitive-access review expectations.
- STRIDE-style threat model covering local stdio, Streamable HTTP, OAuth, NotebookLM auth, artifacts, and CI/CD.
- Architecture boundary lint script wired into CI.

### Changed

- MCP-visible tool names now use underscore-safe names such as `admin_health` and `notebook_list` so VS Code and other strict clients do not reject the server's tools.
- Self-hosted runners are preserved for CI because hosted-runner billing is constrained, with the runner policy documented in governance.
- Documentation and generated tool catalog now call out canonical OpenAPI names and MCP-safe names separately.

### Fixed

- Removed VS Code warnings that reported dotted tool names as invalid.
- Documented that `notebooklm-py` is the package name while the installed login command is `notebooklm`, with `python -m notebooklm` as the PATH-safe fallback.

## [1.0.1] - 2026-05-14

### Added

- OpenSSF Scorecard workflow with SARIF upload and public result publishing.
- Manual release artifact signing workflow for existing GitHub releases.
- ClusterFuzzLite batch fuzzing workflow and Python Atheris fuzz target for settings validation.
- Agent operating map, architecture guide, quality score page, and technical debt register.

### Changed

- Hardened workflow token permissions to top-level read-only with job-level write scopes.
- Pinned Docker base images by digest and verified the Gitleaks scanner binary by checksum.
- Pinned release and SARIF upload actions by full commit SHA.
- Release workflow now signs wheel, sdist, and SBOM assets with Sigstore bundles.
- CI, security, docs, CodeQL, release, and manual workflows now define concurrency groups to cancel stale runs.
- CI now runs on pull requests and main-branch pushes, avoiding duplicate feature-branch push runs.

### Fixed

- Corrected NotebookLM login instructions to use the installed `notebooklm` CLI instead of the PyPI package name.
- Quoted the auth-file storage path printed by `nlm-mcp login` so paths containing spaces can be copied safely.
- `nlm-mcp login` now ignores incomplete HTTP auth configuration while printing the NotebookLM backend-auth setup command.
- Documented the `uvx --from notebooklm-py notebooklm login` flow for isolated `uv tool install` environments.

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
