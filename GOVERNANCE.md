# Governance

`notebooklm-mcp-pro` is maintained as a production Python package and remote MCP
server. Project governance is intentionally small, explicit, and auditable.

## Roles

| Role | Scope | Authority |
|---|---|---|
| Maintainer | Repository-wide code, docs, releases, security response | Merge pull requests, manage releases, maintain CI/CD |
| Code owner | Paths listed in `CODEOWNERS` | Review changes for owned paths |
| Security responder | Vulnerability triage and coordinated disclosure | Triage private advisories and coordinate patches |
| Contributor | Pull requests and issues | Propose changes through review |

The current maintainer list is published in `MAINTAINERS.md`.

## Decision Process

Changes are reviewed through pull requests. Routine changes may be merged by a
maintainer after required checks pass. Security-sensitive changes require extra
scrutiny of authentication, session storage, release workflows, dependency
changes, and logging behavior.

Release changes must preserve these properties:

- version in `pyproject.toml` matches the release tag
- wheel, source distribution, SBOM, and Sigstore bundles are attached to the
  GitHub release
- PyPI publishing uses trusted publishing
- GHCR images are pushed from the release workflow
- provenance attestations are emitted for release artifacts
- branch protection remains enabled on `main`

## Access Review

Sensitive access includes repository administration, branch protection, GitHub
environments, PyPI trusted publishing, GHCR publishing, security advisory
management, release signing, repository secrets, and self-hosted runner
administration.

Sensitive access is reviewed at least every 90 days. Access should be removed
when it is no longer needed. Any new sensitive access grant must be documented
in a pull request or an administrative audit note.

## Single-Maintainer Mode

The project currently operates in single-maintainer mode. This is acceptable for
the 1.x line while the maintainer keeps branch protection, CI gates, security
scans, SBOM generation, Sigstore signing, and provenance attestation enabled.

When a second trusted maintainer is available, `CODEOWNERS` and
`MAINTAINERS.md` should be updated so at least two humans can review
security-sensitive changes and release workflow changes.

## Security Escalation

Security reports are handled through GitHub private security advisories. Public
issues should not include exploit details or private tokens. Critical issues are
triaged within 72 hours and targeted for a patch release within 14 days.

## Self-Hosted Runner Policy

Self-hosted runners are allowed for this repository because hosted-runner billing
is constrained for the project. The runner must be treated as sensitive
infrastructure:

- keep it patched and dedicated to this repository
- do not store NotebookLM credentials, PyPI tokens, or long-lived cloud keys on
  the runner filesystem
- keep workflow permissions least-privilege
- avoid executing untrusted fork pull requests with privileged secrets
- rotate the runner registration token when runner access changes
