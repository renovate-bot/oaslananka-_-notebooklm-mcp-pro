from pathlib import Path

from pydantic import SecretStr, ValidationError
from pytest import MonkeyPatch

from nlm_mcp.config import AuthMode, LogFormat, Settings, TransportMode

ENV_PORT = 9090
OVERRIDE_PORT = 9000


def test_settings_reads_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("NLM_MCP_TRANSPORT", "http")
    monkeypatch.setenv("NLM_MCP_HTTP_HOST", "127.0.0.1")
    monkeypatch.setenv("NLM_MCP_HTTP_PORT", str(ENV_PORT))
    monkeypatch.setenv("NLM_MCP_LOG_FORMAT", "console")

    settings = Settings()

    assert settings.transport is TransportMode.HTTP
    assert settings.http_host == "127.0.0.1"
    assert settings.http_port == ENV_PORT
    assert settings.log_format is LogFormat.CONSOLE


def test_settings_expands_default_user_paths() -> None:
    settings = Settings()

    assert settings.notebooklm_auth_file == Path.home() / ".config/nlm-mcp/notebooklm_auth.json"
    assert settings.data_dir == Path.home() / ".local/share/nlm-mcp"


def test_settings_derives_storage_paths_from_data_dir(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    settings = Settings(data_dir=data_dir)

    assert settings.session_db == f"sqlite+aiosqlite:///{(data_dir / 'sessions.db').as_posix()}"
    assert settings.audit_log_path == str(data_dir / "audit.log")


def test_settings_preserves_explicit_storage_paths(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        session_db="sqlite+aiosqlite:///custom.db",
        audit_log_path="custom-audit.log",
    )

    assert settings.session_db == "sqlite+aiosqlite:///custom.db"
    assert settings.audit_log_path == "custom-audit.log"


def test_settings_renders_data_dir_placeholders(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    settings = Settings(
        data_dir=data_dir,
        session_db="sqlite+aiosqlite:///{DATA_DIR}/sessions.db",
        audit_log_path="{DATA_DIR}/audit.log",
    )

    assert settings.session_db == f"sqlite+aiosqlite:///{data_dir.as_posix()}/sessions.db"
    assert settings.audit_log_path == f"{data_dir.as_posix()}/audit.log"


def test_settings_rejects_invalid_http_port() -> None:
    try:
        Settings(http_port=70000)
    except ValidationError as exc:
        assert "http_port" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("invalid port was accepted")


def test_github_oauth_requires_client_credentials() -> None:
    try:
        Settings(auth_mode=AuthMode.GITHUB_OAUTH)
    except ValidationError as exc:
        message = str(exc)
        assert "github_client_id" in message
        assert "github_client_secret" in message
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("github oauth without credentials was accepted")


def test_token_auth_requires_bearer_token() -> None:
    try:
        Settings(auth_mode=AuthMode.TOKEN)
    except ValidationError as exc:
        assert "bearer_token" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("token auth without bearer_token was accepted")


def test_token_auth_rejects_blank_bearer_token() -> None:
    try:
        Settings(auth_mode=AuthMode.TOKEN, bearer_token=SecretStr(""))
    except ValidationError as exc:
        assert "bearer_token" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("token auth with blank bearer_token was accepted")


def test_token_auth_accepts_bearer_token() -> None:
    settings = Settings(auth_mode=AuthMode.TOKEN, bearer_token=SecretStr("placeholder"))

    assert settings.auth_mode is AuthMode.TOKEN


def test_github_oauth_rejects_blank_client_secret() -> None:
    try:
        Settings(
            auth_mode=AuthMode.GITHUB_OAUTH,
            github_client_id="client-id",
            github_client_secret=SecretStr(""),
        )
    except ValidationError as exc:
        assert "github_client_secret" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("github oauth with blank client secret was accepted")


def test_cli_overrides_are_validated() -> None:
    settings = Settings.from_overrides(
        transport="http",
        http_port=OVERRIDE_PORT,
        auth_mode="token",
        bearer_token=SecretStr("placeholder"),
    )

    assert settings.transport is TransportMode.HTTP
    assert settings.http_port == OVERRIDE_PORT
    assert settings.auth_mode is AuthMode.TOKEN
