# Agent Operating Map

This repository is structured so an automated engineering agent can make safe,
small, verifiable changes without relying on chat history or external notes.

## Primary References

- `README.md` is the public product overview and quickstart.
- `docs/ARCHITECTURE.md` is the system map and module boundary reference.
- `docs/QUALITY_SCORE.md` records current quality gates, OpenSSF Scorecard
  status, and known score constraints.
- `docs/TECH_DEBT.md` records bounded follow-up work that should not be mixed
  into unrelated changes.
- `SECURITY.md` is the public vulnerability disclosure and security model.
- `CONTRIBUTING.md` is the contributor workflow and review policy.

## Local Verification

Run these before proposing or merging code changes:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict
docker build -f deploy/Dockerfile -t notebooklm-mcp-pro:dev .
```

On systems with `make`, the equivalent targets are:

```bash
make lint
make typecheck
make test
make docs
make docker-build
```

## Change Rules

- Keep changes scoped to one behavior or one hardening area.
- Prefer existing module boundaries under `src/nlm_mcp/`.
- Add tests for behavior changes and update docs for public surface changes.
- Do not commit secrets, auth files, generated virtual environments, coverage
  HTML, or local build outputs.
- Keep GitHub Actions permissions least-privilege: top-level read-only, job-level
  write permissions only where the job publishes artifacts, pages, packages, or
  SARIF.
- Pin GitHub Actions by full commit SHA and container images by digest.
- Preserve signed release and SBOM generation in release workflows.

## Architecture Boundaries

- `config.py` owns settings parsing and validation.
- `backend/` owns NotebookLM client integration, retries, exceptions, and task
  persistence.
- `auth/` owns HTTP authentication and session verification.
- `tools/` owns MCP tool registration and typed tool inputs/outputs.
- `resources/` owns MCP resource handlers.
- `prompts/` owns named workflow prompt templates.
- `transport/` owns stdio and Streamable HTTP transport entry points.
- `ui/` owns self-contained MCP UI resources.

When adding a feature, place the code in the narrowest existing layer and expose
it through `server.create_server()` only after the module has tests.

## Release Rules

- Release tags must match `pyproject.toml` version.
- Release artifacts include wheel, sdist, CycloneDX SBOM, and Sigstore bundles.
- PyPI publishing uses trusted publishing.
- Container images are published to GHCR.
- Existing releases can be re-signed with the `Sign Release Artifacts` workflow.
