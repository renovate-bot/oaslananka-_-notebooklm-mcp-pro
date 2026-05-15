"""GitHub OAuth login and session validation for HTTP transports."""

from __future__ import annotations

import json
import secrets
import time
from base64 import urlsafe_b64encode
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

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
AUTHORIZATION_CODE_TTL_SECONDS = 10 * 60
OAUTH_CLIENT_TTL_SECONDS = 30 * 24 * 60 * 60
OAUTH_REGISTRATION_MAX_BYTES = 16 * 1024
OAUTH_CLIENT_MAX_REDIRECT_URIS = 10
OAUTH_REDIRECT_URI_MAX_LENGTH = 2048


class GitHubOAuthHandler:
    """Handle GitHub OAuth login, OAuth bridge code exchange, and session verification."""

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

    async def oauth_authorize(self, request: Request) -> Response:  # noqa: PLR0911
        """Start an OAuth authorization-code + PKCE flow backed by GitHub login."""
        client_id = request.query_params.get("client_id", "").strip()
        redirect_uri = request.query_params.get("redirect_uri", "").strip()
        code_challenge = request.query_params.get("code_challenge", "").strip()
        code_challenge_method = request.query_params.get("code_challenge_method", "").strip()
        response_type = request.query_params.get("response_type", "").strip()
        if response_type != "code" or not client_id or not redirect_uri:
            return JSONResponse(
                {"error": "invalid_request", "message": "OAuth code flow parameters are required"},
                status_code=400,
            )
        if code_challenge_method != "S256" or not code_challenge:
            return JSONResponse(
                {"error": "invalid_request", "message": "PKCE S256 is required"},
                status_code=400,
            )
        try:
            _require_https(redirect_uri)
        except RuntimeError as exc:
            return JSONResponse(
                {"error": "invalid_request", "message": str(exc)},
                status_code=400,
            )

        registered_redirects = await self._registered_redirect_uris(client_id)
        if redirect_uri not in registered_redirects:
            return JSONResponse(
                {"error": "invalid_client", "message": "Redirect URI is not registered"},
                status_code=400,
            )

        github_state = secrets.token_urlsafe(32)
        default_resource = self._default_resource(request)
        resource = request.query_params.get("resource") or default_resource
        if resource != default_resource:
            return JSONResponse(
                {"error": "invalid_target", "message": "Resource is not supported"},
                status_code=400,
            )
        scope = _validated_scope(
            request.query_params.get("scope", ""),
            self._settings.oauth_required_scopes,
        )
        if scope is None:
            return JSONResponse(
                {"error": "invalid_scope", "message": "Requested scope is not supported"},
                status_code=400,
            )
        await self._store_authorization_request(
            github_state,
            client_id=client_id,
            redirect_uri=redirect_uri,
            client_state=request.query_params.get("state", ""),
            code_challenge=code_challenge,
            resource=resource,
            scope=scope,
        )
        return self._github_redirect(github_state, self._redirect_uri(request))

    async def oauth_token(self, request: Request) -> Response:  # noqa: PLR0911
        """Exchange a local authorization code for a bearer token."""
        try:
            form = await request.form()
        except Exception:
            return JSONResponse(
                {"error": "invalid_request", "message": "Invalid OAuth token request"},
                status_code=400,
            )
        grant_type = str(form.get("grant_type", ""))
        code = str(form.get("code", ""))
        redirect_uri = str(form.get("redirect_uri", ""))
        client_id = str(form.get("client_id", ""))
        code_verifier = str(form.get("code_verifier", ""))
        resource = str(form.get("resource", ""))
        if grant_type != "authorization_code" or not code or not redirect_uri or not code_verifier:
            return JSONResponse(
                {"error": "invalid_request", "message": "Invalid OAuth token request"},
                status_code=400,
            )
        if not client_id:
            return JSONResponse(
                {"error": "invalid_request", "message": "client_id is required"},
                status_code=400,
            )

        authorization_code = await self._consume_authorization_code(code)
        if authorization_code is None:
            return JSONResponse(
                {"error": "invalid_grant", "message": "Authorization code is invalid or expired"},
                status_code=400,
            )
        if redirect_uri != authorization_code["redirect_uri"]:
            return JSONResponse(
                {"error": "invalid_grant", "message": "Redirect URI does not match"},
                status_code=400,
            )
        if client_id != authorization_code["client_id"]:
            return JSONResponse(
                {"error": "invalid_grant", "message": "Client ID does not match"},
                status_code=400,
            )
        if resource and resource != authorization_code["resource"]:
            return JSONResponse(
                {"error": "invalid_target", "message": "Resource does not match"},
                status_code=400,
            )
        if not _verify_pkce(code_verifier, authorization_code["code_challenge"]):
            return JSONResponse(
                {"error": "invalid_grant", "message": "PKCE verification failed"},
                status_code=400,
            )

        access_token = secrets.token_urlsafe(32)
        await self._store_session(
            access_token,
            github_login=authorization_code["github_login"],
            github_id=authorization_code["github_id"],
        )
        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": SESSION_TTL_SECONDS,
                "scope": authorization_code["scope"],
                "resource": authorization_code["resource"],
            }
        )

    async def oauth_register(self, request: Request) -> Response:  # noqa: PLR0911
        """Register a public OAuth client for ChatGPT dynamic client registration."""
        content_length = request.headers.get("content-length")
        if (
            content_length
            and content_length.isdecimal()
            and int(content_length) > OAUTH_REGISTRATION_MAX_BYTES
        ):
            return JSONResponse(
                {
                    "error": "invalid_client_metadata",
                    "message": "Registration payload is too large",
                },
                status_code=400,
            )
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse(
                {"error": "invalid_client_metadata", "message": "Malformed JSON payload"},
                status_code=400,
            )
        data = payload if isinstance(payload, dict) else {}
        redirect_uris = data.get("redirect_uris", [])
        if not isinstance(redirect_uris, list) or not redirect_uris:
            return JSONResponse(
                {"error": "invalid_client_metadata", "message": "redirect_uris is required"},
                status_code=400,
            )
        if len(redirect_uris) > OAUTH_CLIENT_MAX_REDIRECT_URIS:
            return JSONResponse(
                {"error": "invalid_client_metadata", "message": "Too many redirect_uris"},
                status_code=400,
            )
        normalized_redirects = [str(uri) for uri in redirect_uris]
        for redirect_uri in normalized_redirects:
            if len(redirect_uri) > OAUTH_REDIRECT_URI_MAX_LENGTH:
                return JSONResponse(
                    {"error": "invalid_client_metadata", "message": "redirect_uri is too long"},
                    status_code=400,
                )
            try:
                _require_https(redirect_uri)
            except RuntimeError as exc:
                return JSONResponse(
                    {"error": "invalid_client_metadata", "message": str(exc)},
                    status_code=400,
                )
        client_id = f"nlm-mcp-{secrets.token_urlsafe(24)}"
        await self._prune_oauth_clients()
        await self._store_client(client_id, normalized_redirects)
        issued_at = int(time.time())
        return JSONResponse(
            {
                "client_id": client_id,
                "client_id_issued_at": issued_at,
                "redirect_uris": normalized_redirects,
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "client_name": str(data.get("client_name", "NotebookLM MCP")),
            },
            status_code=201,
        )

    async def callback(self, request: Request) -> Response:  # noqa: PLR0911
        """Exchange a GitHub OAuth authorization code for a local session cookie."""
        state = request.query_params.get("state")
        authorization_request = (
            await self._consume_authorization_request(state) if state is not None else None
        )

        error = request.query_params.get("error")
        if error:
            return _callback_error_response(
                authorization_request,
                json_error="oauth_error",
                message=error,
                status_code=400,
                client_error=error,
            )

        code = request.query_params.get("code")
        if not code or not state:
            return _callback_error_response(
                authorization_request,
                json_error="invalid_request",
                message="Missing OAuth code or state",
                status_code=400,
            )

        redirect_uri = await self._callback_redirect_uri(request, state, authorization_request)
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
            return _callback_error_response(
                authorization_request,
                json_error="oauth_error",
                message="GitHub did not return an access token",
                status_code=401,
            )

        user = await self._github_user(access_token)
        login = str(user.get("login", ""))
        allowed = _allowed_users(self._settings)
        if allowed and login.casefold() not in allowed:
            return _callback_error_response(
                authorization_request,
                json_error="forbidden",
                message="GitHub user is not allowed",
                status_code=403,
            )

        if authorization_request is not None:
            return await self._complete_authorization_callback(authorization_request, user, login)
        return await self._complete_session_callback(user, login)

    async def _callback_redirect_uri(
        self,
        request: Request,
        state: str,
        authorization_request: dict[str, str] | None,
    ) -> str | None:
        if authorization_request is not None:
            return self._redirect_uri(request)
        return await self._consume_state(state)

    async def _complete_authorization_callback(
        self,
        authorization_request: dict[str, str],
        user: dict[str, Any],
        login: str,
    ) -> Response:
        local_code = secrets.token_urlsafe(32)
        await self._store_authorization_code(
            local_code,
            github_login=login,
            github_id=str(user.get("id", "")),
            client_id=authorization_request["client_id"],
            redirect_uri=authorization_request["redirect_uri"],
            code_challenge=authorization_request["code_challenge"],
            resource=authorization_request["resource"],
            scope=authorization_request["scope"],
        )
        return RedirectResponse(
            _append_query(
                authorization_request["redirect_uri"],
                {
                    "code": local_code,
                    "state": authorization_request["client_state"],
                },
            ),
            status_code=302,
        )

    async def _complete_session_callback(self, user: dict[str, Any], login: str) -> Response:
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

    async def _store_client(self, client_id: str, redirect_uris: list[str]) -> None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO oauth_clients (client_id, redirect_uris, created_at)
                VALUES (?, ?, ?)
                """,
                (client_id, json.dumps(redirect_uris), now),
            )
            await db.commit()

    async def _registered_redirect_uris(self, client_id: str) -> list[str]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT redirect_uris, created_at FROM oauth_clients WHERE client_id = ?",
                (client_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return []
        created_at = int(row[1])
        if created_at + OAUTH_CLIENT_TTL_SECONDS < int(time.time()):
            await self._delete_oauth_client(client_id)
            return []
        value = str(row[0])
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value.split(",")
        return [str(uri) for uri in parsed if str(uri)]

    async def _delete_oauth_client(self, client_id: str) -> None:
        await self._ensure_schema()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM oauth_clients WHERE client_id = ?", (client_id,))
            await db.commit()

    async def _prune_oauth_clients(self) -> None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM oauth_clients WHERE created_at < ?",
                (now - OAUTH_CLIENT_TTL_SECONDS,),
            )
            await db.commit()

    async def _store_authorization_request(
        self,
        github_state: str,
        *,
        client_id: str,
        redirect_uri: str,
        client_state: str,
        code_challenge: str,
        resource: str,
        scope: str,
    ) -> None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM oauth_authorization_requests WHERE expires_at <= ?",
                (now,),
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO oauth_authorization_requests
                    (
                        github_state,
                        client_id,
                        redirect_uri,
                        client_state,
                        code_challenge,
                        resource,
                        scope,
                        created_at,
                        expires_at
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    github_state,
                    client_id,
                    redirect_uri,
                    client_state,
                    code_challenge,
                    resource,
                    scope,
                    now,
                    now + STATE_TTL_SECONDS,
                ),
            )
            await db.commit()

    async def _consume_authorization_request(self, github_state: str) -> dict[str, str] | None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT client_id, redirect_uri, client_state, code_challenge, resource, scope,
                       expires_at
                FROM oauth_authorization_requests
                WHERE github_state = ?
                """,
                (github_state,),
            )
            row = await cursor.fetchone()
            await db.execute(
                "DELETE FROM oauth_authorization_requests WHERE github_state = ?",
                (github_state,),
            )
            await db.execute(
                "DELETE FROM oauth_authorization_requests WHERE expires_at <= ?",
                (now,),
            )
            await db.commit()
        if row is None or int(row[6]) <= now:
            return None
        return {
            "client_id": str(row[0]),
            "redirect_uri": str(row[1]),
            "client_state": str(row[2]),
            "code_challenge": str(row[3]),
            "resource": str(row[4]),
            "scope": str(row[5]),
        }

    async def _store_authorization_code(
        self,
        code: str,
        *,
        github_login: str,
        github_id: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        resource: str,
        scope: str,
    ) -> None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM oauth_authorization_codes WHERE expires_at <= ?",
                (now,),
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO oauth_authorization_codes
                    (
                        code,
                        github_login,
                        github_id,
                        client_id,
                        redirect_uri,
                        code_challenge,
                        resource,
                        scope,
                        created_at,
                        expires_at
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    github_login,
                    github_id,
                    client_id,
                    redirect_uri,
                    code_challenge,
                    resource,
                    scope,
                    now,
                    now + AUTHORIZATION_CODE_TTL_SECONDS,
                ),
            )
            await db.commit()

    async def _consume_authorization_code(self, code: str) -> dict[str, str] | None:
        await self._ensure_schema()
        now = int(time.time())
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT github_login, github_id, client_id, redirect_uri, code_challenge,
                       resource, scope, expires_at
                FROM oauth_authorization_codes
                WHERE code = ?
                """,
                (code,),
            )
            row = await cursor.fetchone()
            await db.execute("DELETE FROM oauth_authorization_codes WHERE code = ?", (code,))
            await db.execute("DELETE FROM oauth_authorization_codes WHERE expires_at <= ?", (now,))
            await db.commit()
        if row is None or int(row[7]) <= now:
            return None
        return {
            "github_login": str(row[0]),
            "github_id": str(row[1]),
            "client_id": str(row[2]),
            "redirect_uri": str(row[3]),
            "code_challenge": str(row[4]),
            "resource": str(row[5]),
            "scope": str(row[6]),
        }

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
                """
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id TEXT PRIMARY KEY,
                    redirect_uris TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_authorization_requests (
                    github_state TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    client_state TEXT NOT NULL,
                    code_challenge TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
                    code TEXT PRIMARY KEY,
                    github_login TEXT NOT NULL,
                    github_id TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    code_challenge TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_oauth_sessions_expires "
                "ON oauth_sessions (expires_at)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_oauth_authorization_requests_expires "
                "ON oauth_authorization_requests (expires_at)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_oauth_authorization_codes_expires "
                "ON oauth_authorization_codes (expires_at)"
            )
            await db.commit()

    def _redirect_uri(self, request: Request) -> str:
        base_url = (self._settings.base_url or str(request.base_url)).rstrip("/")
        return f"{base_url}{self._settings.github_redirect_path}"

    def _default_resource(self, request: Request) -> str:
        base_url = (self._settings.base_url or str(request.base_url)).rstrip("/")
        http_path = self._settings.http_path.strip("/")
        return base_url if not http_path else f"{base_url}/{http_path}"

    def _github_redirect(self, state: str, redirect_uri: str) -> RedirectResponse:
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


def _split_scope(value: str) -> list[str]:
    scopes: list[str] = []
    for chunk in value.split(","):
        scopes.extend(part.strip() for part in chunk.split() if part.strip())
    return scopes


def _validated_scope(requested_scope: str, allowed_scope: str) -> str | None:
    allowed = _split_scope(allowed_scope)
    requested = _split_scope(requested_scope) if requested_scope.strip() else allowed
    if not requested:
        return ""
    allowed_set = set(allowed)
    if any(scope not in allowed_set for scope in requested):
        return None
    return " ".join(requested)


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


def _append_query(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    clean_params = {key: value for key, value in params.items() if value}
    query = urlencode(clean_params)
    separator = "&" if parsed.query else ""
    return urlunparse(parsed._replace(query=f"{parsed.query}{separator}{query}"))


def _client_error_redirect(authorization_request: dict[str, str], error: str) -> RedirectResponse:
    return RedirectResponse(
        _append_query(
            authorization_request["redirect_uri"],
            {
                "error": error,
                "state": authorization_request["client_state"],
            },
        ),
        status_code=302,
    )


def _callback_error_response(
    authorization_request: dict[str, str] | None,
    *,
    json_error: str,
    message: str,
    status_code: int,
    client_error: str | None = None,
) -> Response:
    if authorization_request is not None:
        return _client_error_redirect(authorization_request, client_error or json_error)
    return JSONResponse({"error": json_error, "message": message}, status_code=status_code)


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    try:
        digest = sha256(code_verifier.encode("ascii")).digest()
        calculated = urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    except (TypeError, UnicodeEncodeError):
        return False
    return secrets.compare_digest(calculated, code_challenge)
