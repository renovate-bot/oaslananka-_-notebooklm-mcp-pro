# Contributing

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful, practical, and specific in issues and pull requests.

## Development Environment

```bash
git clone https://github.com/oaslananka/notebooklm-mcp-pro
cd notebooklm-mcp-pro
make bootstrap
```

The bootstrap target installs development dependencies and pre-commit hooks through `uv`.

## Local Commands

```bash
make lint
make typecheck
make test
make test-cov
make docs
```

## Project Structure

| Path | Purpose |
|---|---|
| `src/nlm_mcp/server.py` | FastMCP server factory. |
| `src/nlm_mcp/cli.py` | Typer CLI and HTTP app wiring. |
| `src/nlm_mcp/config.py` | Pydantic settings and validation. |
| `src/nlm_mcp/auth/` | HTTP auth middleware, token validation, GitHub OAuth. |
| `src/nlm_mcp/backend/` | NotebookLM backend wrapper, retry, errors, task store. |
| `src/nlm_mcp/tools/` | MCP tool families. |
| `src/nlm_mcp/resources/` | MCP resources and resource templates. |
| `src/nlm_mcp/prompts/` | Prompt templates. |
| `tests/` | Unit, integration, and opt-in e2e tests. |
| `docs/` | MkDocs documentation site. |
| `deploy/` | Docker, Railway, Fly.io, and Kubernetes templates. |

## Adding a Tool

1. Add a Pydantic input model in `src/nlm_mcp/tools/models.py`.
2. Add a backend method in `src/nlm_mcp/backend/client.py` if the tool needs NotebookLM access.
3. Register the tool in the appropriate `src/nlm_mcp/tools/*.py` module.
4. Use `run_tool` so errors are sanitized and logged.
5. Add MCP annotations with `tool_annotations`.
6. Add unit tests with a fake backend.
7. Add OpenAPI metadata in `src/nlm_mcp/openapi.py`.
8. Update the docs page for the tool family.

Example shape:

```python
@server.tool(name="notebook.example", annotations=tool_annotations(read_only=True))
async def notebook_example(notebook_id: str) -> dict[str, Any]:
    payload = NotebookIdInput(notebook_id=notebook_id)
    return await run_tool("notebook.example", payload, lambda: _example(backend, payload))
```

## Adding a Transport

1. Put transport-specific code under `src/nlm_mcp/transport/`.
2. Keep `create_server()` transport-neutral.
3. Add CLI wiring in `src/nlm_mcp/cli.py`.
4. Add integration tests that start the transport in-process or as a subprocess.
5. Document authentication and deployment implications.

## Testing

Unit tests must be offline and deterministic. Use in-memory fakes instead of live NotebookLM calls. E2E tests belong under `tests/e2e/` and must be gated by `NLM_MCP_RUN_E2E=1`.

Async tests use `pytest-asyncio` auto mode:

```python
async def test_tool() -> None:
    async with Client(server) as client:
        result = await client.call_tool("admin.health", {})
```

## Commit Convention

Use Conventional Commits:

- `feat: add source wait tool`
- `fix: reject unsafe artifact download paths`
- `docs: document GitHub OAuth setup`
- `ci: publish docker image on release`
- `test: cover OpenAPI schema generation`

## Pull Request Process

Before opening a PR:

```bash
make lint
make typecheck
make test
make docs
```

PR checklist:

- The change is scoped.
- Tests cover new behavior.
- Docs are updated for user-visible changes.
- OpenAPI metadata is updated for new tools.
- No secrets or generated attribution strings are committed.

## Release Process

1. Ensure `CHANGELOG.md` has a versioned entry.
2. Ensure `pyproject.toml` and `src/nlm_mcp/__init__.py` versions match.
3. Run `make release-check`.
4. Tag with `vX.Y.Z`.
5. Push the tag.
6. Verify the release workflow publishes artifacts.

## Documentation

Run:

```bash
make docs
make docs-serve
```

Docs are built with MkDocs Material and mkdocstrings. Keep pages copy-paste runnable.

## Backend Guidelines

- Keep `NotebookLMBackend` thin.
- Prefer one backend method per tool operation.
- Map NotebookLM exceptions through `backend/exceptions.py`.
- Do not leak raw upstream payloads in user-facing errors.
- Keep retry policy conservative for read-only calls.
- Avoid retrying mutating calls unless the operation is proven idempotent.
- Keep auth loading in `resolve_auth_source`.
- Keep generated artifact task metadata JSON-serializable.

## Auth Guidelines

- Token auth must use constant-time comparison.
- Query parameter token support is a fallback for constrained clients.
- GitHub OAuth sessions must have a bounded TTL.
- OAuth redirects must be HTTPS in production.
- Public metadata endpoints may be unauthenticated.
- `/mcp` and `/tools/{tool_name}` must be authenticated in HTTP auth modes.
- Do not log bearer tokens, OAuth codes, client secrets, or NotebookLM cookies.

## OpenAPI Guidelines

- Every public action should have an entry in `src/nlm_mcp/openapi.py`.
- Keep operation IDs stable.
- Use Pydantic model JSON schemas where possible.
- Add aliases only when they map to a real tool implementation.
- Keep `search` and `fetch` response shapes stable.
- Test the schema with `tests/unit/test_openapi.py`.

## Documentation Checklist

- Update the relevant page under `docs/tools/` for tool changes.
- Update `docs/configuration.md` for settings changes.
- Update integration docs when endpoint behavior changes.
- Update deployment docs when environment variables or ports change.
- Update `README.md` for major user-visible behavior.
- Update `CHANGELOG.md` in the active release section.

## Review Checklist

- Does the change alter NotebookLM data?
- Does the change need explicit confirmation?
- Does the change need an audit log event?
- Does the change expose a new HTTP route?
- Does the change need auth middleware coverage?
- Does the change need OpenAPI metadata?
- Does the change keep stdio behavior intact?
- Does the change work on Windows, macOS, and Linux?

## Fixture Guidance

Use small fake backend classes for unit tests.

Prefer:

```python
class FakeBackend:
    async def list_notebooks(self) -> list[dict[str, str]]:
        return [{"id": "nb-1", "title": "Notebook"}]
```

Avoid live network calls in unit tests.

Keep e2e tests under `tests/e2e/`.

Gate e2e with:

```bash
NLM_MCP_RUN_E2E=1
```

## Error Handling Guidance

Use these mappings:

- Validation error: `-32602`.
- Rate limit: `-32001`.
- Auth failure: `-32002`.
- Timeout: `-32003`.
- Not found: `-32004`.
- Backend unavailable: `-32005`.

Tool implementations should raise domain errors from the backend layer and let `run_tool` convert them to sanitized MCP tool errors.

## Security Checklist

- No secrets in code.
- No secrets in docs.
- No secrets in test fixtures.
- No generated auth files in git.
- `.env.example` only contains placeholders.
- Docker runtime uses a non-root user.
- Artifact writes stay inside the artifacts directory.
- Destructive tools require confirmation.
- Auth endpoints do not disclose internal stack traces.

## Dependency Updates

Dependabot opens weekly updates.

For dependency PRs:

1. Read release notes for breaking changes.
2. Run `make lint`.
3. Run `make typecheck`.
4. Run `make test`.
5. Run `make docs` when docs dependencies change.

## Local Troubleshooting

If imports fail, run:

```bash
uv sync --extra dev --extra browser
```

If NotebookLM auth fails, run:

```bash
notebooklm-py login
```

If the HTTP server fails to start, verify:

```bash
nlm-mcp serve --dry-run
nlm-mcp doctor
```

If docs fail, run:

```bash
uv run mkdocs build --strict
```
