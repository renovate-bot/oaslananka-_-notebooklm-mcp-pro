# Maintainers

| Handle | Role | Scope | Sensitive Access |
|---|---|---|---|
| @oaslananka | Maintainer | All repository areas | GitHub admin, PyPI trusted publishing, GHCR publishing, security advisories, release workflows |

## Access Review Policy

Escalated access to repository settings, PyPI publishing, GHCR publishing,
release signing, GitHub environments, self-hosted runners, repository secrets,
and security advisories requires documented review before access is granted.

All sensitive access should be reviewed at least every 90 days.

## Maintainer Responsibilities

- Keep `main` releasable.
- Keep required checks green before merging release branches.
- Preserve branch protection and least-privilege workflow permissions.
- Triage security reports through GitHub private security advisories.
- Publish release artifacts with SBOM, Sigstore signatures, and provenance
  attestations.
- Keep documentation accurate for stdio, Streamable HTTP, VS Code, Claude, and
  ChatGPT integrations.

## Adding Maintainers

New maintainers should have a history of high-quality pull requests, security
judgment, and willingness to participate in reviews. Adding a maintainer requires
a pull request updating this file, `GOVERNANCE.md`, and `.github/CODEOWNERS`.
