# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x | Active |
| < 1.0 | No support |

## Reporting a Vulnerability

Do not open a public GitHub issue for security vulnerabilities.

Report vulnerabilities through GitHub private security advisories:

```text
https://github.com/oaslananka/notebooklm-mcp-pro/security/advisories/new
```

We aim to respond within 72 hours and release a patch within 14 days for critical issues.

## Security Architecture

### Authentication

- Stdio transport inherits caller process permissions and is intended for local clients.
- HTTP transport supports bearer token authentication through `auth_mode=token`.
- HTTP transport supports GitHub OAuth through `auth_mode=github-oauth`.
- Bearer tokens are compared with `secrets.compare_digest`.
- GitHub OAuth sessions are stored in SQLite with a 24-hour TTL.

### Data Handling

- NotebookLM credentials are supplied by environment variable or mounted file.
- The auth JSON contains session cookies and must be protected with filesystem permissions.
- Audit log path defaults to `~/.local/share/nlm-mcp/audit.log`.
- Artifact downloads are constrained to the configured artifacts directory.

### Dependencies

- `pip-audit` runs in CI.
- `bandit` static analysis runs in CI.
- Dependabot is configured for Python and GitHub Actions.
- Release workflows generate CycloneDX SBOM artifacts.
- OpenSSF Scorecard runs on `main` and on a weekly schedule.
- ClusterFuzzLite runs scheduled Python fuzzing for configuration-boundary validation.
- Release assets are signed with Sigstore bundles.
- GitHub Actions use top-level read-only token permissions with job-level write scopes.
- Docker base images are pinned by digest.

### Docker

- The runtime image uses a non-root user with UID 10001.
- Mount NotebookLM auth files read-only.
- Set secrets through the platform secret manager rather than image layers.

## Known Limitations

- NotebookLM authentication relies on browser session storage produced by `notebooklm-py`.
- In-memory rate limiting is per process. Use a single replica unless a shared backend is configured.
- GitHub OAuth support is provider-specific in 1.0.0.
