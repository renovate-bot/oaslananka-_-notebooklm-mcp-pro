# Threat Model

This threat model covers `notebooklm-mcp-pro` as a local stdio MCP server and as
a remote Streamable HTTP MCP server.

## Assets

| Asset | Sensitivity | Notes |
|---|---|---|
| NotebookLM session cookies | High | Stored in the NotebookLM auth JSON file or injected through environment |
| OAuth client secret | High | Required only for GitHub OAuth mode |
| Bearer token | High | Required for token-authenticated HTTP deployments |
| OAuth session tokens | High | Stored in SQLite with TTL |
| Notebook source full text | High | May contain private documents, transcripts, PDFs, or Drive content |
| Generated artifacts | Medium to high | Reports, slides, audio, and summaries may contain source data |
| SQLite task/session DB | Medium to high | Tracks auth sessions and artifact state |
| GitHub Actions OIDC token | High | Used for PyPI publishing, Sigstore signing, and attestations |
| GHCR/PyPI release permissions | High | Control public distribution artifacts |

## Trust Boundaries

| Boundary | Trusted Side | Untrusted Side | Controls |
|---|---|---|---|
| Local stdio client | User process | MCP client prompts and tool calls | Local filesystem permissions, destructive confirmations |
| Streamable HTTP endpoint | Server app | Remote MCP clients | Auth middleware, bearer token, OAuth sessions |
| Auth middleware | Verified principal | Headers, cookies, query params | Constant-time token comparison, TTL sessions |
| GitHub OAuth callback | OAuth handler | Browser redirects and state | State validation, allowlist, HTTPS deployment guidance |
| NotebookLM backend | Backend wrapper | Unofficial NotebookLM web surface | Retry policy, sanitized errors, auth-file isolation |
| Tool execution | Typed tool inputs | Client-provided arguments | Pydantic validation, confirmation flags |
| Artifact downloads | Output writer | Local path input | Backend validation and documented operator control |
| OpenAPI action endpoint | Tool dispatcher | HTTP action callers | Same auth and validation path as MCP tools |
| CI/CD | Release workflow | Pull requests and dependencies | Branch protection, scanners, pinned actions, signing |

## STRIDE Analysis

| Category | Scenario | Mitigation |
|---|---|---|
| Spoofing | Attacker sends a forged bearer token | `secrets.compare_digest`, token required in HTTP token mode |
| Spoofing | OAuth session cookie replay | SQLite TTL sessions and HTTPS deployment requirement |
| Tampering | Malicious tool input mutates notebook state | Typed inputs and explicit `confirm=true` for destructive tools |
| Tampering | Release artifact replaced after build | Sigstore bundles, GitHub release assets, provenance attestations |
| Repudiation | User denies destructive tool invocation | Structured audit entries include tool name and argument hash |
| Information disclosure | Auth JSON appears in logs | Secret settings are not logged; docs require secret handling |
| Information disclosure | Notebook source text returned to the wrong user | HTTP deployments require auth; local stdio inherits user account |
| Denial of service | Upstream rate limits or long artifact generation | Tenacity retry policy, polling timeout, rate-limit settings |
| Elevation of privilege | Public PR abuses a privileged workflow | Least-privilege workflow permissions and no untrusted secrets on PRs |

## Abuse Cases

| Abuse Case | Control |
|---|---|
| Token leakage through logs | Do not log raw headers, cookies, auth JSON, or `SecretStr` values |
| OAuth callback manipulation | Validate state, deploy behind HTTPS, restrict allowed users when needed |
| Artifact path misuse | Treat `output_path` as operator-controlled and avoid exposing it to untrusted users |
| Malicious source ingestion | Mark open-world source tools and require user review of imported content |
| Prompt/tool injection through notebook content | Keep tool annotations explicit and do not treat source text as authority for destructive actions |
| Public share enablement abuse | Require confirmation for public sharing |
| Destructive tool invocation | Confirmation required for deletes, cancellation, language changes, and sharing |
| Stale session reuse | OAuth sessions expire after 24 hours |
| Dependency compromise | Dependabot, Socket, `pip-audit`, pinned actions, SBOM, release attestations |
| Compromised CI runner | Keep secrets out of PR jobs, use least-privilege permissions, audit self-hosted runner access |

## Security Review Triggers

Review this model when any of these change:

- authentication middleware
- OAuth provider configuration
- NotebookLM auth storage
- artifact download behavior
- release workflow permissions
- self-hosted runner configuration
- public HTTP endpoints
- tool confirmation semantics
