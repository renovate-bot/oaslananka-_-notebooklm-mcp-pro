"""Tests for GitHub OAuth session handling."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from hashlib import sha256
from http.cookies import SimpleCookie
from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from pydantic import SecretStr
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route
from starlette.testclient import TestClient

from nlm_mcp.auth.oauth import (
    SESSION_COOKIE,
    GitHubOAuthHandler,
    _allowed_users,
    _append_query,
    _require_https,
    _secret_value,
    _secure_cookie,
    _session_token,
    _sqlite_path,
    _validated_scope,
    _verify_pkce,
)
from nlm_mcp.config import AuthMode, Settings

HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_REDIRECT = 302
HTTP_UNAUTHORIZED = 401
HTTP_CREATED = 201
HTTP_OK = 200


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


def _oauth_client(handler: GitHubOAuthHandler) -> TestClient:
    return TestClient(
        Starlette(
            routes=[
                Route("/oauth/register", handler.oauth_register, methods=["POST"]),
                Route("/oauth/authorize", handler.oauth_authorize),
                Route("/auth/callback", handler.callback),
                Route("/oauth/token", handler.oauth_token, methods=["POST"]),
            ]
        )
    )


def _pkce_challenge(verifier: str) -> str:
    digest = sha256(verifier.encode("ascii")).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _register_client(client: TestClient, redirect_uri: str) -> str:
    response = client.post(
        "/oauth/register",
        json={
            "client_name": "ChatGPT",
            "redirect_uris": [redirect_uri],
        },
    )
    assert response.status_code == HTTP_CREATED
    return str(response.json()["client_id"])


def _authorize_and_callback(
    client: TestClient,
    *,
    client_id: str,
    redirect_uri: str,
    verifier: str,
    resource: str,
) -> dict[str, list[str]]:
    authorize = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": "chatgpt-state",
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "resource": resource,
        },
        follow_redirects=False,
    )
    assert authorize.status_code == HTTP_REDIRECT
    github_state = parse_qs(urlparse(authorize.headers["location"]).query)["state"][0]
    callback = client.get(
        "/auth/callback",
        params={"code": "github-code", "state": github_state},
        follow_redirects=False,
    )
    assert callback.status_code == HTTP_REDIRECT
    return _assert_redirect_target(callback.headers["location"], redirect_uri)


def _assert_redirect_target(location: str, redirect_uri: str) -> dict[str, list[str]]:
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == redirect_uri
    return parse_qs(parsed.query)


def _exchange_token(
    client: TestClient,
    *,
    code: str,
    client_id: str,
    redirect_uri: str,
    verifier: str,
    resource: str,
    overrides: dict[str, str] | None = None,
) -> Any:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": verifier,
        "resource": resource,
    }
    if overrides:
        data.update(overrides)
    return client.post("/oauth/token", data=data)


async def _store_bridge_request(
    handler: GitHubOAuthHandler,
    state: str,
    *,
    redirect_uri: str = "https://chatgpt.com/connector/oauth/callback-id",
    client_state: str = "chatgpt-state",
    resource: str = "https://nlm.example.test/mcp",
) -> None:
    await handler._store_authorization_request(
        state,
        client_id="registered-client",
        redirect_uri=redirect_uri,
        client_state=client_state,
        code_challenge=_pkce_challenge("verifier"),
        resource=resource,
        scope="read:user,user:email",
    )


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
        _require_https("custom://example.test/oauth")
    assert (
        _append_query("https://chatgpt.com/callback?existing=1", {"code": "abc", "state": "st"})
        == "https://chatgpt.com/callback?existing=1&code=abc&state=st"
    )
    assert _verify_pkce("verifier", _pkce_challenge("verifier")) is True
    assert _validated_scope("read:user user:email", "read:user,user:email") == (
        "read:user user:email"
    )
    assert _validated_scope("profile", "read:user,user:email") is None


async def test_login_redirects_to_github(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path))

    response = await handler.login(_request("/auth/login"))

    assert response.status_code == HTTP_REDIRECT
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize")
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["redirect_uri"] == ["https://nlm.example.test/auth/callback"]


async def test_login_normalizes_trailing_base_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    settings = _settings(tmp_path)
    object.__setattr__(settings, "base_url", "https://nlm.example.test/")
    handler = GitHubOAuthHandler(settings)

    response = await handler.login(_request("/auth/login"))

    assert response.status_code == HTTP_REDIRECT
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["redirect_uri"] == ["https://nlm.example.test/auth/callback"]


def test_oauth_register_creates_public_client(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))

    with _oauth_client(handler) as client:
        response = client.post(
            "/oauth/register",
            json={
                "client_name": "ChatGPT",
                "redirect_uris": ["https://chatgpt.com/connector/oauth/callback-id"],
            },
        )

    assert response.status_code == HTTP_CREATED
    payload = response.json()
    assert payload["client_id"].startswith("nlm-mcp-")
    assert payload["token_endpoint_auth_method"] == "none"  # noqa: S105


def test_oauth_register_rejects_oversized_metadata(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))

    with _oauth_client(handler) as client:
        too_many = client.post(
            "/oauth/register",
            json={
                "client_name": "ChatGPT",
                "redirect_uris": [
                    f"https://chatgpt.com/connector/oauth/callback-{index}" for index in range(11)
                ],
            },
        )
        too_long = client.post(
            "/oauth/register",
            json={
                "client_name": "ChatGPT",
                "redirect_uris": [f"https://chatgpt.com/{'a' * 2050}"],
            },
        )

    assert too_many.status_code == HTTP_BAD_REQUEST
    assert too_many.json()["error"] == "invalid_client_metadata"
    assert too_long.status_code == HTTP_BAD_REQUEST
    assert too_long.json()["error"] == "invalid_client_metadata"


def test_oauth_bridge_code_flow_issues_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="oaslananka"))
    monkeypatch.setattr(
        handler,
        "_github_user",
        AsyncMock(return_value={"login": "oaslananka", "id": 123}),
    )
    verifier = "correct-horse-battery-staple"
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"
    resource = "https://nlm.example.test/mcp"
    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        callback_params = _authorize_and_callback(
            client,
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier=verifier,
            resource=resource,
        )
        token = _exchange_token(
            client,
            code=callback_params["code"][0],
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier=verifier,
            resource=resource,
        )

    assert callback_params["state"] == ["chatgpt-state"]
    assert token.status_code == HTTP_OK
    assert token.json()["token_type"] == "Bearer"  # noqa: S105


def test_oauth_bridge_rejects_bad_pkce(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="oaslananka"))
    monkeypatch.setattr(
        handler,
        "_github_user",
        AsyncMock(return_value={"login": "oaslananka", "id": 123}),
    )
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"
    resource = "https://nlm.example.test/mcp"
    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        callback_params = _authorize_and_callback(
            client,
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier="expected-verifier",
            resource=resource,
        )
        token = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": callback_params["code"][0],
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": "wrong-verifier",
            },
        )

    assert token.status_code == HTTP_BAD_REQUEST
    assert token.json()["error"] == "invalid_grant"


def test_oauth_bridge_defaults_resource_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="oaslananka"))
    monkeypatch.setattr(
        handler,
        "_github_user",
        AsyncMock(return_value={"login": "oaslananka", "id": 123}),
    )
    verifier = "resource-default-verifier"
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"
    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        authorize = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": "chatgpt-state",
                "code_challenge": _pkce_challenge(verifier),
                "code_challenge_method": "S256",
            },
            follow_redirects=False,
        )
        github_state = parse_qs(urlparse(authorize.headers["location"]).query)["state"][0]
        callback = client.get(
            "/auth/callback",
            params={"code": "github-code", "state": github_state},
            follow_redirects=False,
        )
        callback_params = parse_qs(urlparse(callback.headers["location"]).query)
        token = _exchange_token(
            client,
            code=callback_params["code"][0],
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier=verifier,
            resource="",
        )

    assert token.status_code == HTTP_OK
    assert token.json()["resource"] == "https://nlm.example.test/mcp"


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"redirect_uri": "https://chatgpt.com/connector/oauth/other-callback"}, "invalid_grant"),
        ({"client_id": "wrong-client"}, "invalid_grant"),
        ({"resource": "https://other.example.test/mcp"}, "invalid_target"),
    ],
)
def test_oauth_token_rejects_bound_value_mismatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    overrides: dict[str, str],
    error: str,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="oaslananka"))
    monkeypatch.setattr(
        handler,
        "_github_user",
        AsyncMock(return_value={"login": "oaslananka", "id": 123}),
    )
    verifier = "bound-token-verifier"
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"
    resource = "https://nlm.example.test/mcp"
    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        callback_params = _authorize_and_callback(
            client,
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier=verifier,
            resource=resource,
        )
        token = _exchange_token(
            client,
            code=callback_params["code"][0],
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier=verifier,
            resource=resource,
            overrides=overrides,
        )

    assert token.status_code == HTTP_BAD_REQUEST
    assert token.json()["error"] == error


def test_oauth_token_rejects_missing_or_unknown_code(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))

    with _oauth_client(handler) as client:
        missing = client.post("/oauth/token", data={"grant_type": "authorization_code"})
        missing_client = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "missing-code",
                "redirect_uri": "https://chatgpt.com/connector/oauth/callback-id",
                "code_verifier": "verifier",
            },
        )
        unknown = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "missing-code",
                "redirect_uri": "https://chatgpt.com/connector/oauth/callback-id",
                "client_id": "registered-client",
                "code_verifier": "verifier",
            },
        )

    assert missing.status_code == HTTP_BAD_REQUEST
    assert missing.json()["error"] == "invalid_request"
    assert missing_client.status_code == HTTP_BAD_REQUEST
    assert missing_client.json()["error"] == "invalid_request"
    assert unknown.status_code == HTTP_BAD_REQUEST
    assert unknown.json()["error"] == "invalid_grant"


def test_oauth_authorize_rejects_missing_and_invalid_request_params(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"

    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        missing = client.get("/oauth/authorize", params={"response_type": "token"})
        missing_pkce = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
            },
        )
        bad_redirect = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "custom://chatgpt.com/insecure",
                "code_challenge": _pkce_challenge("verifier"),
                "code_challenge_method": "S256",
            },
        )

    assert missing.status_code == HTTP_BAD_REQUEST
    assert missing.json()["error"] == "invalid_request"
    assert missing_pkce.status_code == HTTP_BAD_REQUEST
    assert missing_pkce.json()["error"] == "invalid_request"
    assert bad_redirect.status_code == HTTP_BAD_REQUEST
    assert bad_redirect.json()["error"] == "invalid_request"


def test_oauth_authorize_rejects_unsupported_resource(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"

    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        response = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": _pkce_challenge("verifier"),
                "code_challenge_method": "S256",
                "resource": "https://other.example.test/mcp",
            },
        )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == "invalid_target"


def test_oauth_authorize_rejects_unsupported_scope(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"

    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        response = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": _pkce_challenge("verifier"),
                "code_challenge_method": "S256",
                "scope": "profile",
            },
        )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == "invalid_scope"


def test_oauth_authorize_accepts_root_mounted_resource(tmp_path: Any) -> None:
    settings = _settings(tmp_path)
    object.__setattr__(settings, "http_path", "/")
    handler = GitHubOAuthHandler(settings)
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"

    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        response = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": _pkce_challenge("verifier"),
                "code_challenge_method": "S256",
                "resource": "https://nlm.example.test",
            },
            follow_redirects=False,
        )

    assert response.status_code == HTTP_REDIRECT


def test_oauth_authorize_rejects_unregistered_redirect_uri(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))
    redirect_uri = "https://chatgpt.com/connector/oauth/callback-id"

    with _oauth_client(handler) as client:
        client_id = _register_client(client, redirect_uri)
        response = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://evil.example.test/callback",
                "code_challenge": _pkce_challenge("verifier"),
                "code_challenge_method": "S256",
            },
        )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == "invalid_client"


def test_oauth_register_rejects_non_https_redirect(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))

    with _oauth_client(handler) as client:
        missing = client.post("/oauth/register", json={})
        malformed = client.post(
            "/oauth/register",
            content="{",
            headers={"content-type": "application/json"},
        )
        response = client.post(
            "/oauth/register",
            json={"redirect_uris": ["custom://chatgpt.com/insecure"]},
        )

    assert missing.status_code == HTTP_BAD_REQUEST
    assert missing.json()["error"] == "invalid_client_metadata"
    assert malformed.status_code == HTTP_BAD_REQUEST
    assert malformed.json()["error"] == "invalid_client_metadata"
    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == "invalid_client_metadata"


async def test_registered_redirect_uris_handles_missing_and_legacy_rows(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))

    assert await handler._registered_redirect_uris("missing-client") == []
    await handler._ensure_schema()

    async with aiosqlite.connect(tmp_path / "sessions.db") as db:
        await db.execute(
            """
            INSERT INTO oauth_clients (client_id, redirect_uris, created_at)
            VALUES (?, ?, ?)
            """,
            (
                "legacy-client",
                "https://chatgpt.com/callback-a,https://chatgpt.com/callback-b",
                1_800_000_000,
            ),
        )
        await db.commit()

    assert await handler._registered_redirect_uris("legacy-client") == [
        "https://chatgpt.com/callback-a",
        "https://chatgpt.com/callback-b",
    ]


def test_pkce_malformed_verifier_fails_closed() -> None:
    assert _verify_pkce("verifier-\u2603", _pkce_challenge("verifier")) is False


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


async def test_callback_redirects_bridge_errors_to_client(tmp_path: Any) -> None:
    handler = GitHubOAuthHandler(_settings(tmp_path))
    await _store_bridge_request(handler, "state-error")
    await _store_bridge_request(handler, "state-missing-code")

    oauth_error = await handler.callback(
        _request("/auth/callback", query_string=b"error=access_denied&state=state-error")
    )
    missing = await handler.callback(
        _request("/auth/callback", query_string=b"state=state-missing-code")
    )

    assert oauth_error.status_code == HTTP_REDIRECT
    oauth_error_query = _assert_redirect_target(
        oauth_error.headers["location"],
        "https://chatgpt.com/connector/oauth/callback-id",
    )
    assert oauth_error_query == {"error": ["access_denied"], "state": ["chatgpt-state"]}
    assert missing.status_code == HTTP_REDIRECT
    missing_query = _assert_redirect_target(
        missing.headers["location"],
        "https://chatgpt.com/connector/oauth/callback-id",
    )
    assert missing_query == {"error": ["invalid_request"], "state": ["chatgpt-state"]}


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


async def test_callback_redirects_bridge_missing_access_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", EmptyTokenOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path))
    await _store_bridge_request(handler, "state-empty-token")

    response = await handler.callback(
        _request("/auth/callback", query_string=b"code=abc&state=state-empty-token")
    )

    assert response.status_code == HTTP_REDIRECT
    query = _assert_redirect_target(
        response.headers["location"],
        "https://chatgpt.com/connector/oauth/callback-id",
    )
    assert query == {"error": ["oauth_error"], "state": ["chatgpt-state"]}


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


async def test_callback_redirects_bridge_disallowed_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr("nlm_mcp.auth.oauth.AsyncOAuth2Client", FakeOAuthClient)
    handler = GitHubOAuthHandler(_settings(tmp_path, allowed_users="someone-else"))
    monkeypatch.setattr(
        handler,
        "_github_user",
        AsyncMock(return_value={"login": "oaslananka", "id": 123}),
    )
    await _store_bridge_request(handler, "state-forbidden")

    response = await handler.callback(
        _request("/auth/callback", query_string=b"code=abc&state=state-forbidden")
    )

    assert response.status_code == HTTP_REDIRECT
    query = _assert_redirect_target(
        response.headers["location"],
        "https://chatgpt.com/connector/oauth/callback-id",
    )
    assert query == {"error": ["forbidden"], "state": ["chatgpt-state"]}


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
