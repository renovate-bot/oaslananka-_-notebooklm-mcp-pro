"""Structured logging setup for the NotebookLM MCP server."""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog

from nlm_mcp.config import LogFormat, Settings

SENSITIVE_EXTERNAL_LOGGERS = (
    "httpx",
    "httpcore",
)


def configure_logging(settings: Settings) -> None:
    """Configure stdlib logging and structlog for server processes."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level, force=True)
    external_level = max(level, logging.WARNING)
    for logger_name in SENSITIVE_EXTERNAL_LOGGERS:
        logging.getLogger(logger_name).setLevel(external_level)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Any
    if settings.log_format is LogFormat.JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[*shared_processors, renderer],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a typed structlog logger."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name).bind())
