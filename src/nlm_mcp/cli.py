"""Command line interface for the NotebookLM MCP server."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from nlm_mcp import __version__
from nlm_mcp.config import AuthMode, Settings, TransportMode
from nlm_mcp.logging_setup import configure_logging
from nlm_mcp.server import create_server
from nlm_mcp.tools.admin import build_health, build_version_info
from nlm_mcp.tools.common import to_plain
from nlm_mcp.transport.stdio_runner import run_stdio

app = typer.Typer(help="NotebookLM MCP server.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Print the package version."),
) -> None:
    """Dispatch the CLI or print version metadata."""
    if version:
        typer.echo(__version__)
        raise typer.Exit
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def stdio() -> None:
    """Run the server over stdio."""
    settings = Settings(transport=TransportMode.STDIO)
    configure_logging(settings)
    run_stdio(settings)


async def _health(request: Request) -> JSONResponse:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    return JSONResponse(build_health(settings).model_dump())


async def _openapi_schema(request: Request) -> JSONResponse:
    """Serve the OpenAPI 3.1 schema for ChatGPT Custom Actions."""
    from nlm_mcp.openapi import OPENAPI_SCHEMA  # noqa: PLC0415

    schema = deepcopy(OPENAPI_SCHEMA)
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    base_url = (settings.base_url or str(request.base_url).rstrip("/")).rstrip("/")
    schema["servers"] = [{"url": base_url, "description": "NotebookLM MCP Server"}]
    if settings.auth_mode is AuthMode.TOKEN:
        schema["security"] = [{"BearerAuth": []}]
    return JSONResponse(schema)


async def _ai_plugin_manifest(request: Request) -> JSONResponse:
    """Serve the ChatGPT plugin manifest."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    base_url = (settings.base_url or str(request.base_url)).rstrip("/")
    auth: dict[str, str] = {"type": "none"}
    if settings.auth_mode is AuthMode.TOKEN:
        auth = {"type": "service_http", "authorization_type": "bearer"}
    elif settings.auth_mode is AuthMode.GITHUB_OAUTH:
        auth = {"type": "oauth"}
    manifest = {
        "schema_version": "v1",
        "name_for_human": "NotebookLM MCP",
        "name_for_model": "notebooklm_mcp",
        "description_for_human": (
            "Manage Google NotebookLM notebooks, sources, and generated artifacts."
        ),
        "description_for_model": (
            "Access Google NotebookLM programmatically. Create and manage notebooks and "
            "sources. Generate audio overviews, videos, infographics, slide decks, reports, "
            "mind maps, quizzes, and flashcards. Run web research. Chat with notebook content."
        ),
        "auth": auth,
        "api": {"type": "openapi", "url": f"{base_url}/openapi.json"},
        "logo_url": f"{base_url}/static/logo.png",
        "contact_email": "oaslananka@users.noreply.github.com",
        "legal_info_url": "https://github.com/oaslananka/notebooklm-mcp-pro/blob/main/LICENSE",
    }
    return JSONResponse(manifest)


async def _oauth_protected_resource_metadata(request: Request) -> JSONResponse:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    base_url = (settings.base_url or str(request.base_url)).rstrip("/")
    resource_path = str(request.path_params.get("resource_path", "")).strip("/")
    resource = f"{base_url}/{resource_path}" if resource_path else base_url
    metadata: dict[str, object] = {
        "resource": resource,
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base_url}/openapi.json",
        "scopes_supported": settings.oauth_required_scopes.split(","),
    }
    if settings.auth_mode is AuthMode.GITHUB_OAUTH:
        metadata["authorization_servers"] = [base_url]
    return JSONResponse(metadata)


async def _oauth_authorization_server_metadata(request: Request) -> JSONResponse:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    base_url = (settings.base_url or str(request.base_url)).rstrip("/")
    if settings.auth_mode is not AuthMode.GITHUB_OAUTH:
        return JSONResponse(
            {"error": "not_found", "message": "OAuth authorization server is not enabled"},
            status_code=404,
        )
    return JSONResponse(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "registration_endpoint": f"{base_url}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": settings.oauth_required_scopes.split(","),
            "resource_parameter_supported": False,
        }
    )


async def _tool_action(request: Request) -> JSONResponse:
    """Invoke an MCP tool through an OpenAPI-friendly JSON endpoint."""
    from nlm_mcp.openapi import resolve_tool_name  # noqa: PLC0415

    tool_name = resolve_tool_name(str(request.path_params["tool_name"]))
    payload = await _json_payload(request)
    mcp_server = request.app.state.mcp_server
    try:
        async with Client(mcp_server) as client:
            result = await client.call_tool(tool_name, payload)
    except (ToolError, McpError) as exc:
        return JSONResponse({"error": "tool_error", "message": str(exc)}, status_code=400)
    return JSONResponse(to_plain(result.data if result.data is not None else result.content))


async def _json_payload(request: Request) -> dict[str, object]:
    if not request.headers.get("content-length") and request.method == "POST":
        return {}
    value = await request.json()
    return value if isinstance(value, dict) else {}


def _notebooklm_default_auth_file() -> Path:
    from nlm_mcp.backend.client import (  # noqa: PLC0415
        _notebooklm_default_auth_file as resolve_path,
    )

    return resolve_path().expanduser()


def _readable_regular_file(path: Path) -> bool:
    try:
        if not path.is_file():
            return False
        with path.open("rb"):
            return True
    except OSError:
        return False


def _newest_readable_file(*paths: Path) -> Path | None:
    newest: Path | None = None
    newest_mtime = float("-inf")
    for path in paths:
        expanded = path.expanduser()
        if not _readable_regular_file(expanded):
            continue
        try:
            mtime = expanded.stat().st_mtime
        except OSError:
            continue
        if mtime > newest_mtime:
            newest = expanded
            newest_mtime = mtime
    return newest


def _sync_notebooklm_login_auth_file(auth_file: Path) -> Path:
    requested_auth_file = auth_file.expanduser()
    profile_auth_file = _notebooklm_default_auth_file()
    newest_auth_file = _newest_readable_file(requested_auth_file, profile_auth_file)
    if newest_auth_file is None or newest_auth_file == requested_auth_file:
        return requested_auth_file
    requested_auth_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(newest_auth_file, requested_auth_file)
    return requested_auth_file


def _http_app(settings: Settings | None = None) -> Starlette:
    from nlm_mcp.auth.middleware import AuthMiddleware  # noqa: PLC0415

    resolved = settings if settings is not None else Settings()
    mcp_server = create_server(resolved)
    web_app = mcp_server.http_app(
        path=resolved.http_path,
        stateless_http=resolved.stateless_http,
        transport="streamable-http",
    )
    web_app.router.routes.append(Route("/healthz", _health))
    web_app.router.routes.append(Route("/openapi.json", _openapi_schema))
    web_app.router.routes.append(Route("/.well-known/ai-plugin.json", _ai_plugin_manifest))
    web_app.router.routes.append(
        Route("/.well-known/oauth-protected-resource", _oauth_protected_resource_metadata)
    )
    web_app.router.routes.append(
        Route(
            "/.well-known/oauth-protected-resource/{resource_path:path}",
            _oauth_protected_resource_metadata,
        )
    )
    web_app.router.routes.append(
        Route("/.well-known/oauth-authorization-server", _oauth_authorization_server_metadata)
    )
    web_app.router.routes.append(
        Route("/.well-known/openid-configuration", _oauth_authorization_server_metadata)
    )
    web_app.router.routes.append(Route("/tools/{tool_name:path}", _tool_action, methods=["POST"]))
    if resolved.auth_mode is AuthMode.GITHUB_OAUTH:
        from nlm_mcp.auth.oauth import GitHubOAuthHandler  # noqa: PLC0415

        handler = GitHubOAuthHandler(resolved)
        web_app.router.routes.append(Route("/auth/login", handler.login))
        web_app.router.routes.append(Route("/auth/callback", handler.callback))
        web_app.router.routes.append(Route("/oauth/authorize", handler.oauth_authorize))
        web_app.router.routes.append(Route("/oauth/token", handler.oauth_token, methods=["POST"]))
        web_app.router.routes.append(
            Route("/oauth/register", handler.oauth_register, methods=["POST"])
        )
    web_app.add_middleware(AuthMiddleware, settings=resolved)
    web_app.state.settings = resolved
    web_app.state.mcp_server = mcp_server
    return web_app


@app.command()
def serve(
    host: Annotated[str | None, typer.Option("--host", help="HTTP host to bind.")] = None,
    port: Annotated[
        int | None, typer.Option("--port", min=1, max=65535, help="HTTP port to bind.")
    ] = None,
    auth: Annotated[AuthMode | None, typer.Option("--auth", help="HTTP authentication mode.")] = (
        None
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate command wiring and exit."),
) -> None:
    """Run the server over Streamable HTTP."""
    settings = Settings.from_overrides(
        transport=TransportMode.HTTP,
        http_host=host,
        http_port=port,
        auth_mode=auth,
    )
    configure_logging(settings)
    if dry_run:
        typer.echo("http configuration ok")
        return
    uvicorn.run(
        _http_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


@app.command()
def login(
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate command wiring and exit."),
) -> None:
    """Run the local NotebookLM browser-login flow."""
    if dry_run:
        if importlib.util.find_spec("notebooklm") is None:
            typer.echo("notebooklm module not found; install notebooklm-mcp-pro first.", err=True)
            raise typer.Exit(1)
        if importlib.util.find_spec("playwright") is None:
            typer.echo("playwright module not found; install notebooklm-mcp-pro first.", err=True)
            raise typer.Exit(1)
        typer.echo("notebooklm login command wiring ok")
        return
    auth_file = Settings.from_overrides(auth_mode=AuthMode.NONE).notebooklm_auth_file.expanduser()
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    browser_command = [sys.executable, "-m", "playwright", "install", "chromium"]
    command = [sys.executable, "-m", "notebooklm", "--storage", str(auth_file), "login"]
    typer.echo("Ensuring Playwright Chromium is installed.")
    typer.echo(f"Starting NotebookLM browser login. Auth storage: {auth_file}")
    try:
        subprocess.run(browser_command, check=True)  # noqa: S603
        subprocess.run(command, check=True)  # noqa: S603
    except subprocess.CalledProcessError as exc:
        raise typer.Exit(exc.returncode) from exc
    try:
        auth_file = _sync_notebooklm_login_auth_file(auth_file)
    except OSError as exc:
        typer.echo(f"NotebookLM auth file sync failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"NotebookLM auth file ready: {auth_file}")


@app.command()
def doctor() -> None:
    """Print local environment diagnostics."""
    settings = Settings()
    from nlm_mcp.backend.client import resolve_auth_source  # noqa: PLC0415
    from nlm_mcp.backend.exceptions import BackendAuthError  # noqa: PLC0415

    try:
        auth_source = resolve_auth_source(settings)
        notebooklm_auth = {
            "kind": auth_source.kind,
            "value": "env_json" if auth_source.kind == "env_json" else auth_source.value,
        }
    except BackendAuthError as exc:
        notebooklm_auth = {
            "kind": "missing",
            "value": str(settings.notebooklm_auth_file.expanduser()),
            "message": exc.safe_message,
        }
    data = build_version_info().model_dump()
    data["transport"] = settings.transport.value
    data["auth_mode"] = settings.auth_mode.value
    data["notebooklm_auth"] = notebooklm_auth
    typer.echo(json.dumps(data, sort_keys=True))


@app.command("version")
def version_command() -> None:
    """Print the package version."""
    typer.echo(__version__)
