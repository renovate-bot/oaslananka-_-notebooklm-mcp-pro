from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

from nlm_mcp.backend.tasks import TaskStore


async def test_task_store_serializes_concurrent_initialization(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    entered_connections = 0

    class FakeConnection:
        async def __aenter__(self) -> FakeConnection:
            nonlocal entered_connections
            entered_connections += 1
            await asyncio.sleep(0)
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def execute(self, _sql: str, _params: Any = None) -> None:
            await asyncio.sleep(0)

        async def commit(self) -> None:
            await asyncio.sleep(0)

    def fake_connect(_db_path: Path) -> FakeConnection:
        return FakeConnection()

    monkeypatch.setattr("nlm_mcp.backend.tasks.aiosqlite.connect", fake_connect)
    store = TaskStore(tmp_path / "tasks.db")

    await asyncio.gather(*(store._ensure() for _ in range(8)))

    assert entered_connections == 1
