# Installation

## Requirements

- Python 3.11, 3.12, or 3.13.
- A Google account with NotebookLM access.
- A local NotebookLM auth file created by `nlm-mcp login`, or an inline auth JSON value supplied through `NLM_MCP_NOTEBOOKLM_AUTH_JSON`.
- `uv`, `pipx`, `pip`, or Docker.

The default auth file path is:

```text
~/.config/nlm-mcp/notebooklm_auth.json
```

If you run `notebooklm login` without `--storage`, the NotebookLM CLI writes:

```text
~/.notebooklm/profiles/default/storage_state.json
```

The server detects that default profile when the project-specific auth file does
not exist.

Run this once on a workstation with a browser:

```bash
nlm-mcp login
```

`nlm-mcp login` calls `python -m notebooklm --storage <path> login`, so it works
even when the dependency's `notebooklm` console script is not on `PATH`. The
base package includes the browser-login dependency, so no separate browser extra
is required for this command. It also installs the Playwright Chromium browser
binary before launching the NotebookLM login page.

To run the dependency CLI directly:

```bash
python -m notebooklm --storage ~/.config/nlm-mcp/notebooklm_auth.json login
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\nlm-mcp"
python -m notebooklm --storage "$env:USERPROFILE\.config\nlm-mcp\notebooklm_auth.json" login
```

## Install with uv

`uv` is the fastest way to install the command as an isolated tool.

```bash
uv tool install notebooklm-mcp-pro
nlm-mcp --version
```

If you use `uv tool install`, the dependency CLI is isolated from your system
Python. Create the NotebookLM auth file with the installed server command:

```bash
nlm-mcp login
```

If you specifically want to run the backend dependency CLI through `uvx`, include
its browser extra:

```bash
uvx --from "notebooklm-py[browser]" notebooklm --storage ~/.config/nlm-mcp/notebooklm_auth.json login
```

## Install with pip

```bash
python -m pip install --upgrade notebooklm-mcp-pro
nlm-mcp --version
```

## Install with pipx

```bash
pipx install notebooklm-mcp-pro
nlm-mcp login
```

## Install with Docker

```bash
docker pull ghcr.io/oaslananka/notebooklm-mcp-pro:latest
docker run --rm -p 8080:8080 ghcr.io/oaslananka/notebooklm-mcp-pro:latest
```

Mount the NotebookLM auth directory when the container needs live NotebookLM access:

```bash
docker run --rm -p 8080:8080 \
  -v "$HOME/.config/nlm-mcp:/home/appuser/.config/nlm-mcp:rw" \
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

When running as a systemd service, set `NLM_MCP_DATA_DIR` to a writable
directory owned by the service user. If NotebookLM browser storage is mounted
from the host, keep it writable so refreshed cookies can be persisted.

## Verify

```bash
nlm-mcp doctor
nlm-mcp serve --dry-run
```

The `doctor` command prints package, Python, transport, and auth mode metadata without contacting NotebookLM.
