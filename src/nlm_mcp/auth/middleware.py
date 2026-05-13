"""ASGI middleware enforcing HTTP authentication."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
            "/.well-known/oauth-protected-resource",
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
            await self.app(scope, _receive_with_cached_body(request, receive), send)
            return

        response = self._unauthorized_response()
        await response(scope, receive, send)

    async def _authenticated(self, request: Request) -> bool:
        if self.settings.auth_mode is AuthMode.TOKEN:
            return self._token_validator.verify(request)
        if self.settings.auth_mode is AuthMode.GITHUB_OAUTH:
            return await self._oauth_handler.verify(request)
        return True

    def _unauthorized_response(self) -> JSONResponse:
        return TokenValidator.unauthorized_response()

    def _is_exempt(self, path: str) -> bool:
        return path in self.EXEMPT_PATHS or path.startswith("/static/")


def _receive_with_cached_body(
    request: Request,
    receive: Receive,
) -> Callable[[], Awaitable[Message]]:
    body_cache: dict[str, bytes] = {}
    sent = False

    async def wrapped_receive() -> Message:
        nonlocal sent
        if "body" not in body_cache:
            body_cache["body"] = await request.body()
        if not sent:
            sent = True
            return {"type": "http.request", "body": body_cache["body"], "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    return wrapped_receive
