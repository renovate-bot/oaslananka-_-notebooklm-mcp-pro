"""Tests for HTTP authentication middleware and validators."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from nlm_mcp.auth.middleware import AuthMiddleware
from nlm_mcp.auth.token import TokenValidator
from nlm_mcp.config import AuthMode, Settings

HTTP_OK = 200
HTTP_UNAUTHORIZED = 401


def _request(
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": headers or [],
            "query_string": query_string,
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


def _settings(mode: AuthMode = AuthMode.TOKEN) -> Settings:
    return Settings(auth_mode=mode, bearer_token=SecretStr("secret-token"))


class TestTokenValidator:
    def test_valid_token_bearer_header(self) -> None:
        validator = TokenValidator(_settings())
        request = _request(headers=[(b"authorization", b"Bearer secret-token")])

        assert validator.verify(request) is True

    def test_valid_token_query_param(self) -> None:
        validator = TokenValidator(_settings())
        request = _request(query_string=b"token=secret-token")

        assert validator.verify(request) is True

    def test_invalid_token_returns_false(self) -> None:
        validator = TokenValidator(_settings())
        request = _request(headers=[(b"authorization", b"Bearer wrong")])

        assert validator.verify(request) is False

    def test_empty_token_returns_false(self) -> None:
        validator = TokenValidator(_settings())
        request = _request()

        assert validator.verify(request) is False

    def test_missing_configured_token_returns_false(self) -> None:
        validator = TokenValidator(Settings(auth_mode=AuthMode.NONE))
        request = _request(headers=[(b"authorization", b"Bearer secret-token")])

        assert validator.verify(request) is False

    def test_timing_safe_comparison(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, str]] = []

        def fake_compare_digest(left: str, right: str) -> bool:
            calls.append((left, right))
            return True

        monkeypatch.setattr("nlm_mcp.auth.token.secrets.compare_digest", fake_compare_digest)
        validator = TokenValidator(_settings())
        request = _request(headers=[(b"authorization", b"Bearer secret-token")])

        assert validator.verify(request) is True
        assert calls == [("secret-token", "secret-token")]


async def _ok(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


async def _echo_body(request: Request) -> JSONResponse:
    return JSONResponse({"body": (await request.body()).decode()})


def _app(settings: Settings) -> Starlette:
    app = Starlette(
        routes=[
            Route("/healthz", _ok),
            Route("/openapi.json", _ok),
            Route("/.well-known/oauth-protected-resource/mcp", _ok),
            Route("/.well-known/private", _ok),
            Route("/mcp", _ok, methods=["GET", "POST", "OPTIONS"]),
            Route("/echo", _echo_body, methods=["POST"]),
        ]
    )
    app.add_middleware(AuthMiddleware, settings=settings)
    return app


class TestAuthMiddleware:
    def test_exempt_path_healthz_bypassed(self) -> None:
        with TestClient(_app(_settings())) as client:
            response = client.get("/healthz")

        assert response.status_code == HTTP_OK
        assert response.json() == {"ok": True}

    def test_exempt_path_openapi_bypassed(self) -> None:
        with TestClient(_app(_settings())) as client:
            response = client.get("/openapi.json")

        assert response.status_code == HTTP_OK

    def test_well_known_subpaths_bypassed(self) -> None:
        with TestClient(_app(_settings())) as client:
            response = client.get("/.well-known/oauth-protected-resource/mcp")

        assert response.status_code == HTTP_OK

    def test_metadata_subpath_is_not_exempt_when_used_as_mcp_path(self) -> None:
        settings = Settings(
            auth_mode=AuthMode.TOKEN,
            bearer_token=SecretStr("secret-token"),
            http_path="/.well-known/oauth-protected-resource/mcp",
        )

        with TestClient(_app(settings)) as client:
            missing = client.get("/.well-known/oauth-protected-resource/mcp")
            valid = client.get(
                "/.well-known/oauth-protected-resource/mcp",
                headers={"Authorization": "Bearer secret-token"},
            )

        assert missing.status_code == HTTP_UNAUTHORIZED
        assert valid.status_code == HTTP_OK

    def test_metadata_subpath_stays_exempt_for_root_mcp_path(self) -> None:
        settings = Settings(
            auth_mode=AuthMode.TOKEN,
            bearer_token=SecretStr("secret-token"),
            http_path="/",
        )

        with TestClient(_app(settings)) as client:
            response = client.get("/.well-known/oauth-protected-resource/mcp")

        assert response.status_code == HTTP_OK

    def test_path_matcher_handles_root_prefix(self) -> None:
        assert AuthMiddleware._path_matches("/anything", "/") is True

    def test_unrelated_well_known_subpaths_require_auth(self) -> None:
        with TestClient(_app(_settings())) as client:
            response = client.get("/.well-known/private")

        assert response.status_code == HTTP_UNAUTHORIZED

    def test_auth_mode_none_always_passes(self) -> None:
        settings = Settings(auth_mode=AuthMode.NONE)

        with TestClient(_app(settings)) as client:
            response = client.get("/mcp")

        assert response.status_code == HTTP_OK

    def test_auth_mode_token_requires_valid_token(self) -> None:
        with TestClient(_app(_settings())) as client:
            missing = client.get("/mcp")
            valid = client.get("/mcp", headers={"Authorization": "Bearer secret-token"})

        assert missing.status_code == HTTP_UNAUTHORIZED
        assert missing.json()["error"] == "unauthorized"
        assert missing.headers["www-authenticate"] == 'Bearer realm="nlm-mcp"'
        assert valid.status_code == HTTP_OK

    def test_mcp_unauthorized_includes_resource_metadata_when_base_url_set(self) -> None:
        settings = Settings(
            auth_mode=AuthMode.TOKEN,
            bearer_token=SecretStr("secret-token"),
            base_url="https://nlm.example.test",
        )

        with TestClient(_app(settings)) as client:
            response = client.get("/mcp")

        assert response.status_code == HTTP_UNAUTHORIZED
        assert response.headers["www-authenticate"] == (
            'Bearer realm="nlm-mcp", '
            'resource_metadata="https://nlm.example.test/.well-known/oauth-protected-resource/mcp"'
        )

    def test_resource_metadata_url_only_matches_configured_http_path_boundary(self) -> None:
        settings = Settings(
            auth_mode=AuthMode.TOKEN,
            bearer_token=SecretStr("secret-token"),
            base_url="https://nlm.example.test",
            http_path="/mcp",
        )
        middleware = AuthMiddleware(_app(Settings(auth_mode=AuthMode.NONE)), settings=settings)

        assert middleware._resource_metadata_url("/mcp") == (
            "https://nlm.example.test/.well-known/oauth-protected-resource/mcp"
        )
        assert middleware._resource_metadata_url("/mcp/extra") == (
            "https://nlm.example.test/.well-known/oauth-protected-resource/mcp/extra"
        )
        assert middleware._resource_metadata_url("/mcp_extra") is None

    def test_resource_metadata_url_supports_root_http_path(self) -> None:
        settings = Settings(
            auth_mode=AuthMode.TOKEN,
            bearer_token=SecretStr("secret-token"),
            base_url="https://nlm.example.test/",
            http_path="/",
        )
        middleware = AuthMiddleware(_app(Settings(auth_mode=AuthMode.NONE)), settings=settings)

        assert middleware._resource_metadata_url("/") == (
            "https://nlm.example.test/.well-known/oauth-protected-resource"
        )
        assert middleware._resource_metadata_url("/nested") == (
            "https://nlm.example.test/.well-known/oauth-protected-resource/nested"
        )

    def test_options_request_bypassed(self) -> None:
        with TestClient(_app(_settings())) as client:
            response = client.options("/mcp")

        assert response.status_code == HTTP_OK

    def test_valid_token_preserves_post_body(self) -> None:
        with TestClient(_app(_settings())) as client:
            response = client.post(
                "/echo",
                content="payload",
                headers={"Authorization": "Bearer secret-token"},
            )

        assert response.status_code == HTTP_OK
        assert response.json() == {"body": "payload"}

    async def test_github_oauth_delegates_to_handler(self, tmp_path: Path) -> None:
        settings = Settings(
            auth_mode=AuthMode.GITHUB_OAUTH,
            github_client_id="client-id",
            github_client_secret=SecretStr("client-secret"),
            data_dir=tmp_path,
        )
        middleware = AuthMiddleware(_app(Settings(auth_mode=AuthMode.NONE)), settings=settings)

        class FakeOAuthHandler:
            async def verify(self, _: Request) -> bool:
                return True

        object.__setattr__(middleware, "_oauth_handler", FakeOAuthHandler())

        assert await middleware._authenticated(_request()) is True

    async def test_none_mode_authenticated_returns_true(self) -> None:
        middleware = AuthMiddleware(_app(Settings(auth_mode=AuthMode.NONE)), settings=Settings())

        assert await middleware._authenticated(_request()) is True


async def test_non_http_scope_is_forwarded() -> None:
    calls: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        calls.append(str(scope["type"]))

    middleware = AuthMiddleware(app, settings=Settings(auth_mode=AuthMode.NONE))

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(_: Message) -> None:
        return None

    await middleware({"type": "lifespan"}, receive, send)

    assert calls == ["lifespan"]
