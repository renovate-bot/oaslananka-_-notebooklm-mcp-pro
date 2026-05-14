import json
import runpy
from typing import cast

from pydantic import SecretStr
from pytest import MonkeyPatch
from starlette.applications import Starlette
from starlette.testclient import TestClient
from typer.testing import CliRunner

from nlm_mcp import __version__
from nlm_mcp.cli import _http_app, app
from nlm_mcp.config import AuthMode, Settings, TransportMode

HTTP_OK = 200
TEST_HTTP_PORT = 9999
OVERRIDE_HTTP_PORT = 9100


def test_cli_prints_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_cli_prints_help_without_command() -> None:
    result = CliRunner().invoke(app, [])

    assert result.exit_code == 0
    assert "NotebookLM MCP server" in result.stdout


def test_cli_doctor_reports_bootstrap_environment() -> None:
    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    expected = Settings()
    assert payload["version"] == __version__
    assert payload["transport"] == expected.transport.value
    assert payload["auth_mode"] == expected.auth_mode.value


def test_cli_transport_commands_are_present() -> None:
    runner = CliRunner()

    serve = runner.invoke(app, ["serve", "--dry-run"])
    login = runner.invoke(app, ["login", "--dry-run"])

    assert serve.exit_code == 0
    assert "http configuration ok" in serve.stdout
    assert login.exit_code == 0
    assert "notebooklm login" in login.stdout


def test_cli_login_prints_module_command_with_storage_path() -> None:
    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == 0
    assert "python -m notebooklm login --storage" in result.stdout
    assert '--storage "' in result.stdout
    assert "notebooklm_auth.json" in result.stdout


def test_cli_login_ignores_incomplete_http_auth_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("NLM_MCP_AUTH_MODE", "token")
    monkeypatch.delenv("NLM_MCP_BEARER_TOKEN", raising=False)

    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == 0
    assert "python -m notebooklm login --storage" in result.stdout


def test_cli_serve_starts_uvicorn(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_run(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr("nlm_mcp.cli.uvicorn.run", fake_run)

    result = CliRunner().invoke(
        app, ["serve", "--host", "127.0.0.1", "--port", str(TEST_HTTP_PORT)]
    )

    assert result.exit_code == 0
    assert calls
    args, kwargs = calls[0]
    web_app = cast(Starlette, args[0])
    assert kwargs == {
        "host": "127.0.0.1",
        "port": TEST_HTTP_PORT,
        "log_level": "info",
        "access_log": True,
    }
    assert web_app.state.settings.http_port == TEST_HTTP_PORT


def test_cli_serve_preserves_environment_defaults(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_run(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setenv("NLM_MCP_HTTP_HOST", "127.0.0.2")
    monkeypatch.setenv("NLM_MCP_HTTP_PORT", str(OVERRIDE_HTTP_PORT))
    monkeypatch.setattr("nlm_mcp.cli.uvicorn.run", fake_run)

    result = CliRunner().invoke(app, ["serve"])

    assert result.exit_code == 0
    assert calls
    _, kwargs = calls[0]
    assert kwargs["host"] == "127.0.0.2"
    assert kwargs["port"] == OVERRIDE_HTTP_PORT


def test_http_health_uses_preconfigured_settings() -> None:
    settings = Settings(
        transport=TransportMode.HTTP,
        auth_mode=AuthMode.TOKEN,
        bearer_token=SecretStr("placeholder"),
    )

    with TestClient(_http_app(settings)) as client:
        response = client.get("/healthz")

    assert response.status_code == HTTP_OK
    assert response.json()["transport"] == "http"
    assert response.json()["auth_mode"] == "token"


def test_http_app_mounts_streamable_http_endpoint() -> None:
    settings = Settings(transport=TransportMode.HTTP, auth_mode=AuthMode.NONE)
    web_app = _http_app(settings)

    route_paths = {getattr(route, "path", None) for route in web_app.routes}

    assert settings.http_path in route_paths
    assert "/healthz" in route_paths
    assert "/openapi.json" in route_paths
    assert "/.well-known/ai-plugin.json" in route_paths
    assert "/tools/{tool_name:path}" in route_paths


def test_cli_stdio_invokes_runner(monkeypatch: MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_run_stdio(settings: object) -> None:
        calls.append(settings)

    monkeypatch.setattr("nlm_mcp.cli.run_stdio", fake_run_stdio)

    result = CliRunner().invoke(app, ["stdio"])

    assert result.exit_code == 0
    assert calls
    assert isinstance(calls[0], Settings)
    assert calls[0].transport is TransportMode.STDIO


def test_cli_version_command_prints_version() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_module_entrypoint_runs_cli(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["python -m nlm_mcp", "--version"])

    try:
        runpy.run_module("nlm_mcp.__main__", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
