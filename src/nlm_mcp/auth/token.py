"""Bearer-token validation for HTTP transports."""

from __future__ import annotations

import secrets

from starlette.requests import Request
from starlette.responses import JSONResponse

from nlm_mcp.config import Settings


class TokenValidator:
    """Validate bearer tokens from the Authorization header or query string."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def verify(self, request: Request) -> bool:
        """Return true when the request contains the configured bearer token."""
        expected = self._expected_token()
        if not expected:
            return False
        supplied = self._request_token(request)
        if not supplied:
            return False
        return secrets.compare_digest(supplied, expected)

    @staticmethod
    def unauthorized_response() -> JSONResponse:
        """Build the standard unauthorized response for token-auth failures."""
        return JSONResponse(
            {"error": "unauthorized", "message": "Invalid or missing authentication token"},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="nlm-mcp"'},
        )

    def _expected_token(self) -> str:
        token = self._settings.bearer_token
        if token is None:
            return ""
        return token.get_secret_value()

    def _request_token(self, request: Request) -> str:
        header = request.headers.get("authorization", "")
        scheme, _, value = header.partition(" ")
        if scheme.casefold() == "bearer" and value:
            return value.strip()
        query_token = request.query_params.get(self._settings.token_query_param)
        return query_token.strip() if query_token else ""
