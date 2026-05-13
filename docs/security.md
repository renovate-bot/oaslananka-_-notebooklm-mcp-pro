# Security

## Threat model

The server bridges local or remote MCP clients to a NotebookLM account. The main assets are NotebookLM session cookies, generated artifacts, source text, and OAuth sessions.

## Authentication

- Stdio: local process boundary only.
- HTTP token: constant-time bearer token comparison with `secrets.compare_digest`.
- HTTP GitHub OAuth: GitHub login creates a 24-hour SQLite session.

## Data handling

- NotebookLM auth JSON is loaded from an environment variable or a mounted file.
- Auth JSON is never logged by application code.
- Artifact downloads are constrained to the configured artifacts directory.
- Destructive tools require `confirm=true`.

## OAuth endpoint safety

OAuth authorization URLs are required to use HTTPS. The implementation never shells out to `mcp-remote`, so authorization endpoint values are not executed.

## Dependency controls

- `pip-audit` runs in security workflow.
- `bandit` runs static analysis.
- `gitleaks` scans commits and the worktree.
- Release builds produce a CycloneDX SBOM.

## Reporting vulnerabilities

Use GitHub private security advisories. Do not open a public issue for vulnerabilities.
