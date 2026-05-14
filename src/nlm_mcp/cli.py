"""Command line interface for the NotebookLM MCP server."""

from __future__ import annotations

import json
from copy import deepcopy
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
    base_url = settings.base_url or str(request.base_url).rstrip("/")
    schema["servers"] = [{"url": base_url, "description": "NotebookLM MCP Server"}]
    if settings.auth_mode is AuthMode.TOKEN:
        schema["security"] = [{"BearerAuth": []}]
    return JSONResponse(schema)


async def _ai_plugin_manifest(request: Request) -> JSONResponse:
    """Serve the ChatGPT plugin manifest."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    base_url = settings.base_url or str(request.base_url).rstrip("/")
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
    base_url = settings.base_url or str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "resource": base_url,
            "authorization_servers": [base_url],
            "bearer_methods_supported": ["header"],
            "resource_documentation": f"{base_url}/openapi.json",
        }
    )


async def _oauth_authorization_server_metadata(request: Request) -> JSONResponse:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = Settings()
    base_url = settings.base_url or str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/auth/login",
            "token_endpoint": f"{base_url}/auth/callback",
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": settings.oauth_required_scopes.split(","),
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
        Route("/.well-known/oauth-authorization-server", _oauth_authorization_server_metadata)
    )
    web_app.router.routes.append(Route("/tools/{tool_name:path}", _tool_action, methods=["POST"]))
    if resolved.auth_mode is AuthMode.GITHUB_OAUTH:
        from nlm_mcp.auth.oauth import GitHubOAuthHandler  # noqa: PLC0415

        handler = GitHubOAuthHandler(resolved)
        web_app.router.routes.append(Route("/auth/login", handler.login))
        web_app.router.routes.append(Route("/auth/callback", handler.callback))
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
    """Show the local NotebookLM browser-login command path."""
    if dry_run:
        typer.echo("notebooklm login command path ok")
        return
    auth_file = Settings.from_overrides(auth_mode=AuthMode.NONE).notebooklm_auth_file.expanduser()
    typer.echo(
        "Use the NotebookLM CLI to create the auth file configured by "
        f'NLM_MCP_NOTEBOOKLM_AUTH_FILE:\npython -m notebooklm login --storage "{auth_file}"'
    )


@app.command()
def doctor() -> None:
    """Print local environment diagnostics."""
    settings = Settings()
    data = build_version_info().model_dump()
    data["transport"] = settings.transport.value
    data["auth_mode"] = settings.auth_mode.value
    typer.echo(json.dumps(data, sort_keys=True))


@app.command("version")
def version_command() -> None:
    """Print the package version."""
    typer.echo(__version__)
