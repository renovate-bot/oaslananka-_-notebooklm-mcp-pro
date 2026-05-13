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

The latest local Scorecard baseline before this hardening pass was:

```text
Aggregate score: 5.6 / 10
Commit: 46538068a5c5de5ba84b8dff40045019cf4e1f56
```

The hardening pass adds or changes:

- OpenSSF Scorecard workflow with SARIF upload and public result publishing.
- Top-level read-only workflow permissions with job-level write permissions.
- Full SHA pinning for GitHub Actions introduced by the hardening pass.
- Digest pinning for Docker base images and checksum verification for the Gitleaks scanner binary.
- Sigstore signing for new release assets.
- Manual release-signing workflow for existing release assets.
- ClusterFuzzLite batch fuzzing with an Atheris target for settings validation.
- Agent-readable architecture, quality, and debt documentation.

## Expected Score Movement

| Check | Before | Expected after merge and workflow runs | Notes |
|---|---:|---:|---|
| Binary-Artifacts | 10 | 10 | No checked-in binaries. |
| Dangerous-Workflow | 10 | 10 | No `pull_request_target` checkout pattern. |
| Dependency-Update-Tool | 10 | 10 | Dependabot is configured. |
| License | 10 | 10 | MIT license is present. |
| Packaging | 10 | 10 | PyPI, GHCR, and GitHub Release workflows exist. |
| SAST | 10 | 10 | CodeQL is configured. |
| Security-Policy | 10 | 10 | Security policy is present. |
| Vulnerabilities | 10 | 10 | No known open vulnerabilities at baseline. |
| Pinned-Dependencies | 7 | 9-10 | Remaining result depends on Scorecard parser support for pinned composite actions. |
| Token-Permissions | 0 | 9-10 | Write scopes moved to job-level only. |
| Signed-Releases | 0 | 8-10 | Requires running `Sign Release Artifacts` for existing releases. |
| Branch-Protection | 4 | 8-10 | Requires stricter repository settings after this branch is merged. |
| CI-Tests | -1 | 8-10 | Requires a merged pull request with passing checks. |
| Code-Review | 0 | 0-10 | Requires a real non-author review or implicit merge-by-different-user history. |
| Maintained | 0 | Time-gated | Scorecard does not fully score repos younger than 90 days. |
| Contributors | 3 | Community-gated | Requires contributors from multiple organizations. |
| CII-Best-Practices | 0 | External-gated | Requires an OpenSSF Best Practices badge application. |
| Fuzzing | 0 | 8-10 | ClusterFuzzLite is deployed with a Python Atheris fuzz target. |

## Release Verification

For a release to meet this repository's quality bar:

1. Tag version matches `pyproject.toml`.
2. CI, security, CodeQL, docs, and Scorecard workflows complete successfully.
3. Wheel, sdist, SBOM, and Sigstore bundle assets are present on the GitHub
   release.
4. PyPI install works for the tagged version.
5. GHCR image pull works for the tagged version.
