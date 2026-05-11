"""Command line interface for the NotebookLM MCP server."""

from __future__ import annotations

import json
from typing import Annotated

import typer
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from nlm_mcp import __version__
from nlm_mcp.config import AuthMode, Settings, TransportMode
from nlm_mcp.logging_setup import configure_logging
from nlm_mcp.server import create_server
from nlm_mcp.tools.admin import build_health, build_version_info
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


def _http_app(settings: Settings | None = None) -> Starlette:
    resolved = settings if settings is not None else Settings()
    web_app = create_server(resolved).http_app(
        path=resolved.http_path,
        stateless_http=resolved.stateless_http,
        transport="streamable-http",
    )
    web_app.router.routes.append(Route("/healthz", _health))
    web_app.state.settings = resolved
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
    if settings.auth_mode is not AuthMode.NONE:
        raise typer.BadParameter("HTTP authentication is implemented in a later milestone.")
    if dry_run:
        typer.echo("http configuration ok")
        return
    uvicorn.run(
        _http_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level="info",
    )


@app.command()
def login(
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate command wiring and exit."),
) -> None:
    """Show the local NotebookLM browser-login command path."""
    if dry_run:
        typer.echo("notebooklm-py login command path ok")
        return
    typer.echo(
        "Use notebooklm-py login to create the auth file configured by "
        "NLM_MCP_NOTEBOOKLM_AUTH_FILE."
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
