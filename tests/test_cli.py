import runpy

from pytest import MonkeyPatch
from starlette.requests import Request
from typer.testing import CliRunner

from nlm_mcp import __version__
from nlm_mcp.cli import _health, _http_app, app

HTTP_OK = 200


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
    assert "bootstrap environment ok" in result.stdout


def test_cli_transport_commands_are_present() -> None:
    runner = CliRunner()

    stdio = runner.invoke(app, ["stdio"])
    serve = runner.invoke(app, ["serve", "--dry-run"])

    assert stdio.exit_code == 0
    assert "stdio transport" in stdio.stdout
    assert serve.exit_code == 0
    assert "http transport bootstrap check ok" in serve.stdout


def test_http_app_exposes_health_route() -> None:
    http_app = _http_app()

    assert any(getattr(route, "path", None) == "/healthz" for route in http_app.routes)


async def test_health_response_contains_version() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/healthz", "headers": []})
    response = await _health(request)

    assert response.status_code == HTTP_OK
    assert __version__.encode() in response.body


def test_cli_serve_starts_uvicorn(monkeypatch: MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(*args: object, **kwargs: object) -> None:
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr("nlm_mcp.cli.uvicorn.run", fake_run)

    result = CliRunner().invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9999"])

    assert result.exit_code == 0
    assert calls
    assert calls[0]["kwargs"] == {"host": "127.0.0.1", "port": 9999, "log_level": "info"}


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
