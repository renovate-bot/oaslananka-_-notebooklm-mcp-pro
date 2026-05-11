"""Command line interface for the NotebookLM MCP server."""

from __future__ import annotations

import typer
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from nlm_mcp import __version__

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
    typer.echo("stdio transport is implemented in the core server milestone")


async def _health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__})


def _http_app() -> Starlette:
    return Starlette(routes=[Route("/healthz", _health)])


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="HTTP host to bind."),
    port: int = typer.Option(8080, "--port", min=1, max=65535, help="HTTP port to bind."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate command wiring and exit."),
) -> None:
    """Run the server over Streamable HTTP."""
    if dry_run:
        typer.echo("http transport bootstrap check ok")
        return
    uvicorn.run(_http_app(), host=host, port=port, log_level="info")


@app.command()
def doctor() -> None:
    """Print local environment diagnostics."""
    typer.echo("notebooklm-mcp-pro bootstrap environment ok")


@app.command("version")
def version_command() -> None:
    """Print the package version."""
    typer.echo(__version__)
