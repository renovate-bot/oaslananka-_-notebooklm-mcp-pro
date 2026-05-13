# Installation

## Requirements

- Python 3.11, 3.12, or 3.13.
- A Google account with NotebookLM access.
- A local NotebookLM auth file created by `notebooklm-py login`, or an inline auth JSON value supplied through `NLM_MCP_NOTEBOOKLM_AUTH_JSON`.
- `uv`, `pipx`, `pip`, or Docker.

The default auth file path is:

```text
~/.config/nlm-mcp/notebooklm_auth.json
```

Run this once on a workstation with a browser:

```bash
notebooklm-py login
```

## Install with uv

`uv` is the fastest way to install the command as an isolated tool.

```bash
uv tool install notebooklm-mcp-pro
nlm-mcp --version
```

For browser login support in the same environment:

```bash
uv tool install "notebooklm-mcp-pro[browser]"
```

## Install with pip

```bash
python -m pip install --upgrade notebooklm-mcp-pro
nlm-mcp --version
```

## Install with pipx

```bash
pipx install notebooklm-mcp-pro
pipx inject notebooklm-mcp-pro "notebooklm-mcp-pro[browser]"
```

## Install with Docker

```bash
docker pull ghcr.io/oaslananka/notebooklm-mcp-pro:latest
docker run --rm -p 8080:8080 ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```

Mount the NotebookLM auth directory when the container needs live NotebookLM access:

```bash
docker run --rm -p 8080:8080 \
  -v "$HOME/.config/nlm-mcp:/home/appuser/.config/nlm-mcp:ro" \
  ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```

## Install from source

```bash
git clone https://github.com/oaslananka/notebooklm-mcp-pro
cd notebooklm-mcp-pro
make bootstrap
make test
```

`make bootstrap` runs:

```bash
uv sync --extra dev --extra browser
uv run pre-commit install
```

## Platform notes

### Windows

Use PowerShell and keep the auth file path explicit when running inside services:

```powershell
$env:NLM_MCP_NOTEBOOKLM_AUTH_FILE="$env:USERPROFILE\.config\nlm-mcp\notebooklm_auth.json"
nlm-mcp stdio
```

### macOS

For desktop clients, the command installed by `uv tool install` or `pipx install` must be visible in the GUI application's PATH. Use the full command path if the client cannot find `nlm-mcp`.

### Linux

When running as a systemd service, set `NLM_MCP_DATA_DIR` to a writable directory owned by the service user and mount the auth file read-only.

## Verify

```bash
nlm-mcp doctor
nlm-mcp serve --dry-run
```

The `doctor` command prints package, Python, transport, and auth mode metadata without contacting NotebookLM.
