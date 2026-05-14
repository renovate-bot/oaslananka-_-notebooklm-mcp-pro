# OSPS Baseline Mapping

This page maps repository controls to the Open Source Project Security Baseline
expectations used for production open source projects.

| Area | Status | Evidence | Gap |
|---|---|---|---|
| Vulnerability reporting | Met | `SECURITY.md`, GitHub private security advisory link | None |
| Supported versions | Met | `SECURITY.md` supported versions table | None |
| Automated tests | Met | `pytest` in CI with coverage gate | None |
| Static analysis | Met | Ruff, mypy, Bandit, CodeQL | None |
| Dependency scanning | Met | `pip-audit`, Dependabot, Socket, GitGuardian, Gitleaks | None |
| Release notes | Met | `CHANGELOG.md` and GitHub releases | None |
| SBOM | Met | CycloneDX `sbom.json` generated on release | Add per-artifact SBOMs if package tooling requires them |
| Provenance | Met | GitHub build provenance attestation for wheel, sdist, and SBOM | Verify attestation after each release |
| Artifact signing | Met | Sigstore bundles for wheel, sdist, and SBOM | None |
| Container publishing | Met | GHCR image pushed on tag with SBOM/provenance build metadata | Add registry-side policy checks when available |
| Branch protection | Met | Required PR, required checks, code owner review, no force pushes | Keep settings audited after admin changes |
| Governance | Met | `GOVERNANCE.md`, `MAINTAINERS.md`, `CODEOWNERS` | Add a second maintainer when available |
| Threat model | Met | `docs/THREAT_MODEL.md` | Review every major auth or transport change |
| Secure development policy | Met | `CONTRIBUTING.md`, `SECURITY.md`, CI gates | None |
| Architecture boundaries | Met | `scripts/check_arch_boundaries.py` in local and CI lint | Expand rules as modules evolve |
| Runner policy | Partial | `GOVERNANCE.md` documents self-hosted runner requirements | Hosted runners are preferred when billing allows |
| VEX disposition | Partial | Security policy documents non-leakage and audit process | Add VEX documents when a real false-positive advisory appears |
| Best Practices Badge | Partial | Project meets most passing criteria | Complete OpenSSF Best Practices Badge application |

## Release Verification Evidence

Release verification should include:

1. Confirm the tag matches `pyproject.toml`.
2. Verify the wheel and source distribution hashes from the GitHub release.
3. Verify Sigstore bundles for `dist/*` and `sbom.json`.
4. Verify GitHub artifact attestations for `dist/*` and `sbom.json`.
5. Verify the GHCR image digest for the version tag.
6. Confirm `pip install notebooklm-mcp-pro==<version>` installs the same version
   printed by `nlm-mcp --version`.

## Review Cadence

This mapping is reviewed when release workflows, auth controls, CI gates, or
maintainer access changes. It should also be reviewed before each minor release.
