# Quality Score

This page records the repository's quality gates and the current OpenSSF
Scorecard posture. It is a maintenance document for contributors and release
owners.

## Current Gates

| Gate | Status | Enforcement |
|---|---:|---|
| Ruff lint | Passing | CI required check `lint` |
| Ruff format | Passing | CI required check `lint` |
| Mypy strict | Passing | CI required check `typecheck` |
| Pytest | Passing | CI required check `test` |
| Coverage | 92%+ | `--cov-fail-under=92` |
| Build | Passing | CI required check `build` |
| MkDocs strict build | Passing | Docs workflow |
| Docker build | Passing | Release workflow and local target |
| CodeQL | Passing | Code scanning workflow |
| Dependency audit | Passing | Security workflow |
| Secret scan | Passing | Security workflow |

## OpenSSF Scorecard

The source of truth is the public OpenSSF Scorecard badge in `README.md`, the
weekly `OpenSSF Scorecard` workflow, and the GitHub code scanning alert feed.
The last local hardening audit before strict branch-protection changes measured
`7.3 / 10`; the remaining deductions are mostly repository-governance signals
that improve only after GitHub settings, project age, review history, and
community participation accumulate.

The 1.0 hardening pass adds or changes:

- OpenSSF Scorecard workflow with SARIF upload.
- Top-level read-only workflow permissions with job-level write permissions.
- Full SHA pinning for GitHub Actions introduced by the hardening pass.
- Digest pinning for Docker base images and checksum verification for the Gitleaks scanner binary.
- Sigstore signing for new release assets.
- Manual release-signing workflow for existing release assets.
- ClusterFuzzLite batch fuzzing with an Atheris target for settings validation.
- Agent-readable architecture, quality, and debt documentation.
- Self-hosted runner cleanup before checkout so protected workflows do not fail
  on stale root-owned build directories.
- Node 24 opt-in for JavaScript actions and current SHA-pinned action versions.
- Standard PyPI trusted-publishing action for packaging detection.

## Scorecard Posture

| Check | Current posture | Notes |
|---|---|---|
| Binary-Artifacts | Maximal | No checked-in binaries. |
| Branch-Protection | Repository setting | Main requires status checks, linear history, conversation resolution, and strict PR review settings. |
| CI-Tests | Active | CI requires lint, typecheck, tests across supported Python versions, and package build. |
| CII-Best-Practices | External-gated | Requires completing the OpenSSF Best Practices badge application outside this repository. |
| Code-Review | History-gated | Strict branch settings enforce future reviews; score improves as reviewed PR history accumulates. |
| Contributors | Community-gated | A single-maintainer project cannot maximize this score through code changes alone. |
| Dangerous-Workflow | Maximal | No unsafe `pull_request_target` checkout pattern. |
| Dependency-Update-Tool | Maximal | Dependabot is configured for GitHub Actions and Python dependencies. |
| Fuzzing | Active | ClusterFuzzLite and deterministic Atheris smoke coverage are configured. |
| License | Maximal | MIT license is present. |
| Maintained | Time-gated | New repositories score low until there is more than 90 days of maintenance history. |
| Packaging | Active | Release workflow publishes PyPI packages, GHCR images, GitHub releases, SBOMs, and Sigstore bundles. |
| Pinned-Dependencies | Maximal | GitHub Actions are SHA-pinned and Docker bases are digest-pinned. |
| SAST | Maximal | CodeQL and Bandit are configured. |
| Security-Policy | Maximal | Security policy is present and published. |
| Signed-Releases | Strong | Release assets include Sigstore bundles; historical releases can be signed with the manual signing workflow. |
| Token-Permissions | Maximal | Workflows default to read-only permissions with job-level write scopes. |
| Vulnerabilities | Maximal | Dependency and code scanning are enabled; open code scanning alerts should remain at zero. |

## Release Verification

For a release to meet this repository's quality bar:

1. Tag version matches `pyproject.toml`.
2. CI, security, CodeQL, docs, and Scorecard workflows complete successfully.
3. Wheel, sdist, SBOM, and Sigstore bundle assets are present on the GitHub
   release.
4. PyPI install works for the tagged version.
5. GHCR image pull works for the tagged version.
