"""GitHub OAuth login and session validation for HTTP transports."""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiosqlite
import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client  # type: ignore[import-untyped]
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from nlm_mcp.auth.token import TokenValidator
from nlm_mcp.config import Settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105
USER_URL = "https://api.github.com/user"
SESSION_COOKIE = "nlm_mcp_session"
SESSION_TTL_SECONDS = 24 * 60 * 60
STATE_TTL_SECONDS = 10 * 60


class GitHubOAuthHandler:
    """Handle GitHub OAuth login, callback, and local session verification."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token_validator = TokenValidator(settings)
        self._db_path = _sqlite_path(settings)

    async def login(self, request: Request) -> Response:
        """Redirect the caller to GitHub's OAuth authorization endpoint."""
        state = secrets.token_urlsafe(32)
        redirect_uri = self._redirect_uri(request)
        await self._store_state(state, redirect_uri)
        client = AsyncOAuth2Client(
            client_id=self._settings.github_client_id,
            scope=self._settings.oauth_required_scopes,
        )
        authorization_url, _ = client.create_authorization_url(
            AUTHORIZE_URL,
            redirect_uri=redirect_uri,
            state=state,
        )
        _require_https(authorization_url)
        return RedirectResponse(authorization_url, status_code=302)

    async def callback(self, request: Request) -> Response:
        """Exchange a GitHub OAuth authorization code for a local session cookie."""
        error = request.query_params.get("error")
        if error:
            return JSONResponse({"error": "oauth_error", "message": error}, status_code=400)

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return JSONResponse(
                {"error": "invalid_request", "message": "Missing OAuth code or state"},
                status_code=400,
            )

        redirect_uri = await self._consume_state(state)
        if redirect_uri is None:
            return JSONResponse(
                {"error": "invalid_state", "message": "OAuth state is invalid or expired"},
                status_code=400,
            )

        client = AsyncOAuth2Client(
            client_id=self._settings.github_client_id,
            client_secret=_secret_value(self._settings.github_client_secret),
            scope=self._settings.oauth_required_scopes,
        )
        token: dict[str, Any] = await client.fetch_token(
            TOKEN_URL,
            code=code,
            redirect_uri=redirect_uri,
        )
        access_token = str(token.get("access_token", ""))
        if not access_token:
            return JSONResponse(
                {"error": "oauth_error", "message": "GitHub did not return an access token"},
                status_code=401,
            )

        user = await self._github_user(access_token)
        login = str(user.get("login", ""))
        allowed = _allowed_users(self._settings)
        if allowed and login.casefold() not in allowed:
            return JSONResponse(
                {"error": "forbidden", "message": "GitHub user is not allowed"},
                status_code=403,
            )

        session_token = secrets.token_urlsafe(32)
        await self._store_session(
            session_token,
            github_login=login,
            github_id=str(user.get("id", "")),
        )
        response = RedirectResponse(self._settings.http_path, status_code=302)
        response.set_cookie(
            SESSION_COOKIE,
            session_token,
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            secure=_secure_cookie(self._settings),
            samesite="lax",
        )
        return response

    async def verify(self, request: Request) -> bool:
        """Validate a GitHub OAuth session cookie or session bearer token."""
        if self._token_validator.verify(request):
            return True
        supplied = _session_token(request)
        if not supplied:
            return False
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT expires_at FROM oauth_sessions WHERE session_token = ?",
                (supplied,),
            )
            row = await cursor.fetchone()
            await db.execute("DELETE FROM oauth_sessions WHERE expires_at <= ?", (now,))
            await db.commit()
        return bool(row and int(row[0]) > now)

    async def _github_user(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                USER_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}

    async def _store_state(self, state: str, redirect_uri: str) -> None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM oauth_states WHERE expires_at <= ?",
                (now,),
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO oauth_states (state, redirect_uri, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (state, redirect_uri, now, now + STATE_TTL_SECONDS),
            )
            await db.commit()

    async def _consume_state(self, state: str) -> str | None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT redirect_uri, expires_at FROM oauth_states WHERE state = ?",
                (state,),
            )
            row = await cursor.fetchone()
            await db.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
            await db.execute("DELETE FROM oauth_states WHERE expires_at <= ?", (now,))
            await db.commit()
        if row is None or int(row[1]) <= now:
            return None
        return str(row[0])

    async def _store_session(
        self,
        session_token: str,
        *,
        github_login: str,
        github_id: str,
    ) -> None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO oauth_sessions
                    (session_token, github_login, github_id, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_token, github_login, github_id, now, now + SESSION_TTL_SECONDS),
            )
            await db.commit()

    async def _ensure_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_sessions (
                    session_token TEXT PRIMARY KEY,
                    github_login TEXT NOT NULL,
                    github_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    redirect_uri TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_oauth_sessions_expires "
                "ON oauth_sessions (expires_at)"
            )
            await db.commit()

    def _redirect_uri(self, request: Request) -> str:
        base_url = self._settings.base_url or str(request.base_url).rstrip("/")
        return f"{base_url}{self._settings.github_redirect_path}"


def _sqlite_path(settings: Settings) -> Path:
    if settings.session_db and settings.session_db.startswith("sqlite+aiosqlite:///"):
        return Path(settings.session_db.removeprefix("sqlite+aiosqlite:///")).expanduser()
    return (settings.data_dir / "sessions.db").expanduser()


def _allowed_users(settings: Settings) -> set[str]:
    if not settings.oauth_allowed_users:
        return set()
    return {
        user.strip().casefold() for user in settings.oauth_allowed_users.split(",") if user.strip()
    }


def _secret_value(secret: Any | None) -> str | None:
    if secret is None:
        return None
    if hasattr(secret, "get_secret_value"):
        value = secret.get_secret_value()
        return str(value) if value else None
    return str(secret)


def _session_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.casefold() == "bearer" and value:
        return value.strip()
    cookie = request.cookies.get(SESSION_COOKIE)
    return cookie.strip() if cookie else ""


def _secure_cookie(settings: Settings) -> bool:
    return bool(settings.base_url and urlparse(settings.base_url).scheme == "https")


def _require_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError("OAuth authorization endpoint must use https")
