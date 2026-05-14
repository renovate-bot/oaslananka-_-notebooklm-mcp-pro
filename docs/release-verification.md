# Release Verification

Use this checklist for every tagged release.

## Package Version

```bash
TAG_VERSION="${GITHUB_REF_NAME#v}"
python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
```

The tag version must match `pyproject.toml`.
Export `TAG_VERSION` before running the remaining commands when verifying a
release outside GitHub Actions.

## PyPI Install

```bash
python -m pip install "notebooklm-mcp-pro==${TAG_VERSION}"
python -m nlm_mcp --version
```

The command should print the released version.

## Sigstore Bundles

Release assets include Sigstore bundles for wheel, source distribution, and
SBOM files. Verify each bundle with the current Sigstore tooling for the target
artifact.

## GitHub Attestations

Release assets include GitHub build provenance attestations for:

- `dist/*.whl`
- `dist/*.tar.gz`
- `sbom.json`

Verify an artifact with:

```bash
gh attestation verify <artifact-path> --repo oaslananka/notebooklm-mcp-pro
```

## SBOM

The release workflow emits CycloneDX JSON as `sbom.json`. Consumers should store
the SBOM with the package artifacts and use it for dependency inventory.

## GHCR Image

Pull the exact version tag and inspect the digest:

```bash
docker pull ghcr.io/oaslananka/notebooklm-mcp-pro:${TAG_VERSION}
docker image inspect ghcr.io/oaslananka/notebooklm-mcp-pro:${TAG_VERSION} --format '{{index .RepoDigests 0}}'
```

The release workflow builds the container with BuildKit provenance and SBOM
metadata enabled.
