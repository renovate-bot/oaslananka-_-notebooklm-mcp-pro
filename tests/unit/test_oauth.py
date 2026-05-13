"""Tests for GitHub OAuth session handling."""

from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Any

import pytest
from pydantic import SecretStr
from starlette.requests import Request

from nlm_mcp.auth.oauth import (
    SESSION_COOKIE,
    GitHubOAuthHandler,
    _allowed_users,
    _require_https,
    _secret_value,
    _secure_cookie,
    _session_token,
    _sqlite_path,
)
from nlm_mcp.config import AuthMode, Settings

HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_REDIRECT = 302
HTTP_UNAUTHORIZED = 401


def _settings(tmp_path: Any, *, allowed_users: str | None = None) -> Settings:
    return Settings(
        auth_mode=AuthMode.GITHUB_OAUTH,
        github_client_id="client-id",
        github_client_secret=SecretStr("client-secret"),
        oauth_allowed_users=allowed_users,
        base_url="https://nlm.example.test",
        data_dir=tmp_path,
    )


def _request(path: str, *, query_string: bytes = b"", cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers,
            "query_string": query_string,
            "server": ("nlm.example.test", 443),
            "client": ("testclient", 50000),
            "scheme": "https",
        }
    )


class FakeOAuthClient:
    """Small Authlib-compatible OAuth client used by tests."""

    def __init__(self, **_: Any) -> None:
        self.kwargs = _

    def create_authorization_url(
        self,
        url: str,
        *,
        redirect_uri: str,
        state: str,
    ) -> tuple[str, str]:
        return f"{url}?client_id=client-id&redirect_uri={redirect_uri}&state={state}", state

    async def fetch_token(self, *_: Any, **__: Any) -> dict[str, str]:
        return {"access_token": "github-token"}


class EmptyTokenOAuthClient(FakeOAuthClient):
    async def fetch_token(self, *_: Any, **__: Any) -> dict[str, str]:
        return {}


def test_oauth_helpers(tmp_path: Any) -> None:
    settings = _settings(tmp_path, allowed_users="oaslananka, collaborator")
    fallback_settings = _settings(tmp_path)
    object.__setattr__(fallback_settings, "session_db", "postgresql://example")

    assert _sqlite_path(settings) == tmp_path / "sessions.db"
    assert _sqlite_path(fallback_settings) == tmp_path / "sessions.db"
    assert _allowed_users(settings) == {"oaslananka", "collaborator"}
    assert _allowed_users(_settings(tmp_path)) == set()
    assert _secure_cookie(settings) is True
    assert _secret_value(None) is None
    assert _secret_value("raw-secret") == "raw-secret"
    assert (
        _session_token(_request("/mcp", cookie=f"{SESSION_COOKIE}=cookie-token")) == "cookie-token"
    )
    assert (
        _session_token(
            Request(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/mcp",
                    "headers": [(b"authorization", b"Bearer bearer-token")],
                    "query_string": b"",
                    "server": ("nlm.example.test", 443),
                    "client": ("testclient", 50000),
                    "scheme": "https",
                }
            )
        )
        == "bearer-token"
    )
    with pytest.raises(RuntimeError, match="https"):
        _require_https("http://example.test/oauth")


async def test_login_redirects_to_github(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path))

    response = await handler.login(_request("/auth/login"))

    assert response.status_code == HTTP_REDIRECT
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize")


async def test_callback_rejects_invalid_requests(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))

    oauth_error = await handler.callback(_request("/auth/callback", query_string=b"error=denied"))
    missing = await handler.callback(_request("/auth/callback"))
    invalid_state = await handler.callback(
        _request("/auth/callback", query_string=b"code=abc&state=missing")
    )

    assert oauth_error.status_code == HTTP_BAD_REQUEST
    assert missing.status_code == HTTP_BAD_REQUEST
    assert invalid_state.status_code == HTTP_BAD_REQUEST


async def test_callback_rejects_missing_access_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", EmptyTokenOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path))
    await handler._store_state("state-empty", "https://nlm.example.test/auth/callback")

    response = await handler.callback(
        _request("/auth/callback", query_string=b"code=abc&state=state-empty")
    )

    assert response.status_code == HTTP_UNAUTHORIZED


async def test_callback_creates_session_and_verify_accepts_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="oaslananka"))

    async def fake_user(_: str) -> dict[str, Any]:
        return {"login": "oaslananka", "id": 123}

    monkeypatch.setattr(handler, "_github_user", fake_user)
    await handler._store_state("state-1", "https://nlm.example.test/auth/callback")
    response = await handler.callback(
        _request("/auth/callback", query_string=b"code=abc&state=state-1")
    )
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    session_token = cookie[SESSION_COOKIE].value

    assert response.status_code == HTTP_REDIRECT
    assert (
        await handler.verify(_request("/mcp", cookie=f"{SESSION_COOKIE}={session_token}")) is True
    )
    assert await handler.verify(_request("/mcp")) is False


async def test_verify_accepts_bearer_fallback(tmp_path: Any) -> None:
    settings = _settings(tmp_path)
    object.__setattr__(settings, "bearer_token", SecretStr("fallback-token"))
    handler = GitHubOAuthHandler(settings)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"authorization", b"Bearer fallback-token")],
            "query_string": b"",
            "server": ("nlm.example.test", 443),
            "client": ("testclient", 50000),
            "scheme": "https",
        }
    )

    assert await handler.verify(request) is True


async def test_callback_rejects_disallowed_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="someone-else"))

    async def fake_user(_: str) -> dict[str, Any]:
        return {"login": "oaslananka", "id": 123}

    monkeypatch.setattr(handler, "_github_user", fake_user)
    await handler._store_state("state-2", "https://nlm.example.test/auth/callback")
    response = await handler.callback(
        _request("/auth/callback", query_string=b"code=abc&state=state-2")
    )

    assert response.status_code == HTTP_FORBIDDEN


async def test_github_user_parses_response(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"login": "oaslananka"}

    class FakeAsyncClient:
        def __init__(self, **_: Any) -> None:
            return None

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def get(self, *_: Any, **__: Any) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr("nlm_mcp.auth.oauth.httpx.AsyncClient", FakeAsyncClient)
    handler = GitHubOAuthHandler(_settings(tmp_path))

    assert await handler._github_user("token") == {"login": "oaslananka"}
