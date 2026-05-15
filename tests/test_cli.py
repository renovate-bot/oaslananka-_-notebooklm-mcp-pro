import importlib.util
import json
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from pydantic import SecretStr
from pytest import MonkeyPatch
from starlette.applications import Starlette
from starlette.testclient import TestClient
from typer.testing import CliRunner

from nlm_mcp import __version__
from nlm_mcp import cli as cli_module
from nlm_mcp.cli import _http_app, app
from nlm_mcp.config import AuthMode, Settings, TransportMode

HTTP_OK = 200
TEST_HTTP_PORT = 9999
OVERRIDE_HTTP_PORT = 9100
LOGIN_FAILURE_EXIT_CODE = 7


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
    assert payload["notebooklm_auth"]["kind"] in {"default", "env_json", "file", "missing"}


def test_cli_doctor_reports_missing_custom_auth_file(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE", "missing-custom-auth.json")

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["notebooklm_auth"]["kind"] == "missing"
    assert "missing-custom-auth.json" in payload["notebooklm_auth"]["value"]


def test_cli_transport_commands_are_present() -> None:
    runner = CliRunner()

    serve = runner.invoke(app, ["serve", "--dry-run"])
    login = runner.invoke(app, ["login", "--dry-run"])

    assert serve.exit_code == 0
    assert "http configuration ok" in serve.stdout
    assert login.exit_code == 0
    assert "notebooklm login command wiring ok" in login.stdout


def test_cli_login_dry_run_reports_missing_notebooklm(monkeypatch: MonkeyPatch) -> None:
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, package: str | None = None) -> object | None:
        if name == "notebooklm":
            return None
        return original_find_spec(name, package)

    monkeypatch.setattr("nlm_mcp.cli.importlib.util.find_spec", fake_find_spec)

    result = CliRunner().invoke(app, ["login", "--dry-run"])

    assert result.exit_code == 1
    assert "notebooklm module not found" in result.stderr


def test_cli_login_dry_run_reports_missing_playwright(monkeypatch: MonkeyPatch) -> None:
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, package: str | None = None) -> object | None:
        if name == "playwright":
            return None
        return original_find_spec(name, package)

    monkeypatch.setattr("nlm_mcp.cli.importlib.util.find_spec", fake_find_spec)

    result = CliRunner().invoke(app, ["login", "--dry-run"])

    assert result.exit_code == 1
    assert "playwright module not found" in result.stderr


def test_cli_login_runs_module_command_with_storage_path(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "notebooklm_auth.json"
    calls: list[tuple[list[str], bool]] = []
    browser_command = [sys.executable, "-m", "playwright", "install", "chromium"]

    def fake_run(command: list[str], *, check: bool) -> None:
        calls.append((command, check))

    monkeypatch.setenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE", str(auth_file))
    monkeypatch.setattr("nlm_mcp.cli.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == 0
    assert calls == [
        (browser_command, True),
        ([sys.executable, "-m", "notebooklm", "--storage", str(auth_file), "login"], True),
    ]
    assert "Ensuring Playwright Chromium is installed." in result.stdout
    assert f"Auth storage: {auth_file}" in result.stdout
    assert f"NotebookLM auth file ready: {auth_file}" in result.stdout


def test_cli_login_syncs_newer_notebooklm_profile_storage(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "config" / "notebooklm_auth.json"
    profile_storage = tmp_path / "profiles" / "default" / "storage_state.json"
    profile_payload = '{"cookies": [{"name": "fresh"}]}'
    browser_command = [sys.executable, "-m", "playwright", "install", "chromium"]
    login_command = [sys.executable, "-m", "notebooklm", "--storage", str(auth_file), "login"]
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        calls.append(command)
        assert check is True
        if command == login_command:
            profile_storage.parent.mkdir(parents=True)
            profile_storage.write_text(profile_payload, encoding="utf-8")

    monkeypatch.setenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE", str(auth_file))
    monkeypatch.setattr("nlm_mcp.cli.subprocess.run", fake_run)
    monkeypatch.setattr(
        "nlm_mcp.cli._notebooklm_default_auth_file",
        lambda: profile_storage,
        raising=False,
    )

    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == 0
    assert calls == [browser_command, login_command]
    assert auth_file.read_text(encoding="utf-8") == profile_payload
    assert f"NotebookLM auth file ready: {auth_file}" in result.stdout


def test_cli_sync_auth_file_keeps_requested_file_when_it_is_newest(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "notebooklm_auth.json"
    profile_storage = tmp_path / "profiles" / "default" / "storage_state.json"
    auth_file.write_text('{"cookies": [{"name": "requested"}]}', encoding="utf-8")

    monkeypatch.setattr("nlm_mcp.cli._notebooklm_default_auth_file", lambda: profile_storage)

    resolved = cli_module._sync_notebooklm_login_auth_file(auth_file)

    assert resolved == auth_file
    assert auth_file.read_text(encoding="utf-8") == '{"cookies": [{"name": "requested"}]}'


def test_cli_notebooklm_default_auth_file_delegates_to_backend(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    profile_storage = tmp_path / "profiles" / "default" / "storage_state.json"

    monkeypatch.setattr(
        "nlm_mcp.backend.client._notebooklm_default_auth_file",
        lambda: profile_storage,
    )

    assert cli_module._notebooklm_default_auth_file() == profile_storage


def test_cli_auth_storage_helpers_tolerate_filesystem_races(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    path_type = type(tmp_path)
    unreadable = tmp_path / "unreadable.json"
    raced = tmp_path / "raced.json"
    unreadable.write_text("{}", encoding="utf-8")
    raced.write_text("{}", encoding="utf-8")
    stat_calls = 0

    def fake_is_file(self: Path) -> bool:
        if self.name == "raced-is-file.json":
            raise OSError("raced")
        return True

    def fake_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self.name == "unreadable.json":
            raise OSError("raced")
        return Path.open(self, *args, **kwargs)

    def fake_stat(self: Path) -> object:
        nonlocal stat_calls
        stat_calls += 1
        raise OSError("raced")

    monkeypatch.setattr(path_type, "is_file", fake_is_file)
    assert cli_module._readable_regular_file(tmp_path / "raced-is-file.json") is False

    monkeypatch.setattr(path_type, "open", fake_open)
    assert cli_module._readable_regular_file(unreadable) is False

    monkeypatch.setattr(path_type, "stat", fake_stat)
    assert cli_module._newest_readable_file(raced) is None
    assert stat_calls == 1


def test_cli_login_reports_auth_sync_filesystem_error(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "config" / "notebooklm_auth.json"
    profile_storage = tmp_path / "profiles" / "default" / "storage_state.json"
    login_command = [sys.executable, "-m", "notebooklm", "--storage", str(auth_file), "login"]

    def fake_run(command: list[str], *, check: bool) -> None:
        assert check is True
        if command == login_command:
            profile_storage.parent.mkdir(parents=True)
            profile_storage.write_text('{"cookies": [{"name": "fresh"}]}', encoding="utf-8")

    def fake_copy2(source: Path, destination: Path) -> None:
        assert source == profile_storage
        assert destination == auth_file
        raise OSError("disk full")

    monkeypatch.setenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE", str(auth_file))
    monkeypatch.setattr("nlm_mcp.cli.subprocess.run", fake_run)
    monkeypatch.setattr("nlm_mcp.cli._notebooklm_default_auth_file", lambda: profile_storage)
    monkeypatch.setattr("nlm_mcp.cli.shutil.copy2", fake_copy2)

    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == 1
    assert "NotebookLM auth file sync failed: disk full" in result.stderr
    assert "Traceback" not in result.output


def test_cli_login_ignores_incomplete_http_auth_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "notebooklm_auth.json"
    calls: list[list[str]] = []
    browser_command = [sys.executable, "-m", "playwright", "install", "chromium"]

    def fake_run(command: list[str], *, check: bool) -> None:
        calls.append(command)

    monkeypatch.setenv("NLM_MCP_AUTH_MODE", "token")
    monkeypatch.delenv("NLM_MCP_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE", str(auth_file))
    monkeypatch.setattr("nlm_mcp.cli.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == 0
    assert calls == [
        browser_command,
        [sys.executable, "-m", "notebooklm", "--storage", str(auth_file), "login"],
    ]


def test_cli_login_returns_notebooklm_login_exit_code(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "notebooklm_auth.json"
    command = [sys.executable, "-m", "notebooklm", "--storage", str(auth_file), "login"]
    browser_command = [sys.executable, "-m", "playwright", "install", "chromium"]
    calls: list[list[str]] = []

    def fake_run(received_command: list[str], *, check: bool) -> None:
        calls.append(received_command)
        assert check is True
        if received_command == command:
            raise subprocess.CalledProcessError(LOGIN_FAILURE_EXIT_CODE, received_command)

    monkeypatch.setenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE", str(auth_file))
    monkeypatch.setattr("nlm_mcp.cli.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["login"])

    assert result.exit_code == LOGIN_FAILURE_EXIT_CODE
    assert calls == [browser_command, command]


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
