from pytest import MonkeyPatch, raises

from nlm_mcp.config import AuthMode, Settings, TransportMode
from nlm_mcp.transport.stdio_runner import run_stdio


class FakeServer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def test_run_stdio_rejects_non_stdio_settings() -> None:
    settings = Settings(transport=TransportMode.HTTP, auth_mode=AuthMode.NONE)

    with raises(ValueError, match="transport=stdio"):
        run_stdio(settings)


def test_run_stdio_invokes_fastmcp_stdio_transport(monkeypatch: MonkeyPatch) -> None:
    fake_server = FakeServer()
    captured_settings: list[Settings] = []

    def fake_create_server(settings: Settings) -> FakeServer:
        captured_settings.append(settings)
        return fake_server

    monkeypatch.setattr("nlm_mcp.transport.stdio_runner.create_server", fake_create_server)

    settings = Settings(transport=TransportMode.STDIO)
    run_stdio(settings)

    assert captured_settings == [settings]
    assert fake_server.calls == [{"transport": "stdio", "show_banner": False}]
