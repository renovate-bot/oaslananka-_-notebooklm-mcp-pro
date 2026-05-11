# Contributing

Thank you for helping improve `notebooklm-mcp-pro`.

## Development Setup

```bash
make bootstrap
make lint
make typecheck
make test
```

The project uses Python 3.11+ and `uv` for reproducible local environments.

## Commit Convention

Use Conventional Commits:

- `feat:` user-facing feature
- `fix:` user-facing bug fix
- `docs:` documentation only
- `test:` tests only
- `refactor:` behavior-preserving code change
- `ci:` workflow and automation changes
- `build:` packaging and dependency changes
- `chore:` repository maintenance
- `perf:` performance improvement

## Pull Requests

1. Keep PRs scoped to one coherent change.
2. Include tests for behavior changes.
3. Run `make lint && make typecheck && make test` before requesting review.
4. Update docs when public behavior or configuration changes.
