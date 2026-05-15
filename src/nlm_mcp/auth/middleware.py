"""ASGI middleware enforcing HTTP authentication."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from nlm_mcp.auth.oauth import GitHubOAuthHandler
from nlm_mcp.auth.token import TokenValidator
from nlm_mcp.config import AuthMode, Settings


class AuthMiddleware:
    """ASGI middleware that enforces HTTP authentication."""

    EXEMPT_PATHS = frozenset(
        {
            "/healthz",
            "/auth/login",
            "/auth/callback",
            "/openapi.json",
            "/.well-known/ai-plugin.json",
            "/.well-known/oauth-authorization-server",
        }
    )

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self._token_validator = TokenValidator(settings)
        self._oauth_handler = GitHubOAuthHandler(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        path = str(scope.get("path", ""))
        if method == "OPTIONS" or self._is_exempt(path) or self.settings.auth_mode is AuthMode.NONE:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if await self._authenticated(request):
            await self.app(scope, receive, send)
            return

        response = self._unauthorized_response(path)
        await response(scope, receive, send)

    async def _authenticated(self, request: Request) -> bool:
        if self.settings.auth_mode is AuthMode.TOKEN:
            return self._token_validator.verify(request)
        if self.settings.auth_mode is AuthMode.GITHUB_OAUTH:
            return await self._oauth_handler.verify(request)
        return True

    def _unauthorized_response(self, path: str) -> JSONResponse:
        return TokenValidator.unauthorized_response(self._resource_metadata_url(path))

    def _is_exempt(self, path: str) -> bool:
        if self._path_matches(path, "/.well-known/oauth-protected-resource"):
            return not self._path_matches_configured_http_path(path)
        return path in self.EXEMPT_PATHS or path.startswith("/static/")

    def _path_matches_configured_http_path(self, path: str) -> bool:
        http_path = self.settings.http_path.rstrip("/") or "/"
        if http_path == "/":
            return False
        return self._path_matches(path, http_path)

    @staticmethod
    def _path_matches(path: str, prefix: str) -> bool:
        normalized_prefix = prefix.rstrip("/") or "/"
        if normalized_prefix == "/":
            return path.startswith("/")
        return path == normalized_prefix or path.startswith(f"{normalized_prefix}/")

    def _resource_metadata_url(self, path: str) -> str | None:
        if not self.settings.base_url:
            return None
        base_url = self.settings.base_url.rstrip("/")
        http_path = self.settings.http_path.rstrip("/") or "/"
        if http_path == "/":
            resource_path = path.strip("/")
            suffix = f"/{resource_path}" if resource_path else ""
            return f"{base_url}/.well-known/oauth-protected-resource{suffix}"
        if not (path == http_path or path.startswith(f"{http_path}/")):
            return None
        resource_path = path.strip("/")
        return f"{base_url}/.well-known/oauth-protected-resource/{resource_path}"
