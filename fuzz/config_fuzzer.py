"""Atheris fuzz target for configuration boundary parsing."""

from __future__ import annotations

import sys
from contextlib import suppress
from enum import Enum
from typing import TypeVar

import atheris

with atheris.instrument_imports():
    from pydantic import ValidationError

    from nlm_mcp.config import AuthMode, LogFormat, Settings, TransportMode

EnumT = TypeVar("EnumT", bound=Enum)


def _choose_enum(enum_type: type[EnumT], data: bytes, offset: int) -> EnumT:
    values = list(enum_type)
    if not data:
        return values[0]
    return values[data[offset % len(data)] % len(values)]


def _http_path(text: str) -> str:
    cleaned = "".join(ch for ch in text[:64] if ch.isalnum() or ch in "-_/.")
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned if cleaned != "/" else "/mcp"


def test_one_input(data: bytes) -> None:
    """Exercise settings validation with arbitrary byte input."""
    text = data.decode("utf-8", "ignore")
    port = int.from_bytes(data[:2].ljust(2, b"\0"), "big") % 65535 + 1

    with suppress(ValueError, ValidationError, UnicodeError):
        Settings(
            transport=_choose_enum(TransportMode, data, 0),
            auth_mode=AuthMode.NONE,
            http_host="127.0.0.1",
            http_port=port,
            http_path=_http_path(text),
            log_format=_choose_enum(LogFormat, data, 1),
            default_language=text[:8] or "en",
        )


def main() -> None:
    """Run the fuzz target."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
