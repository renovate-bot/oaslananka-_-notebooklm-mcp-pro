"""Persistent artifact task tracking."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any

import aiosqlite

from nlm_mcp.config import Settings


@dataclass(frozen=True)
class ArtifactTaskRecord:
    """Persisted NotebookLM artifact task metadata."""

    task_id: str
    notebook_id: str
    kind: str
    status: str
    metadata: dict[str, Any]
    created_at: float
    updated_at: float


class TaskStore:
    """SQLite-backed task store for generated NotebookLM artifacts."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path.expanduser()
        self._initialized = False
        self._init_lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings: Settings) -> TaskStore:
        """Create a task store under the configured data directory."""
        return cls(settings.data_dir / "artifact_tasks.db")

    async def upsert(
        self,
        *,
        task_id: str,
        notebook_id: str,
        kind: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactTaskRecord:
        """Insert or update one task record."""
        await self._ensure()
        now = time()
        existing = await self.get(task_id)
        created_at = existing.created_at if existing is not None else now
        payload = json.dumps(metadata or {}, sort_keys=True, default=str)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO artifact_tasks (
                    task_id, notebook_id, kind, status, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    notebook_id = excluded.notebook_id,
                    kind = excluded.kind,
                    status = excluded.status,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (task_id, notebook_id, kind, status, payload, created_at, now),
            )
            await db.commit()
        return ArtifactTaskRecord(
            task_id=task_id,
            notebook_id=notebook_id,
            kind=kind,
            status=status,
            metadata=metadata or {},
            created_at=created_at,
            updated_at=now,
        )

    async def get(self, task_id: str) -> ArtifactTaskRecord | None:
        """Return one task by id, if present."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT task_id, notebook_id, kind, status, metadata_json, created_at, updated_at
                FROM artifact_tasks
                WHERE task_id = ?
                """,
                (task_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        metadata = json.loads(row[4]) if row[4] else {}
        return ArtifactTaskRecord(
            task_id=str(row[0]),
            notebook_id=str(row[1]),
            kind=str(row[2]),
            status=str(row[3]),
            metadata=metadata,
            created_at=float(row[5]),
            updated_at=float(row[6]),
        )

    async def list_for_notebook(self, notebook_id: str) -> list[ArtifactTaskRecord]:
        """Return tracked tasks for a notebook."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT task_id, notebook_id, kind, status, metadata_json, created_at, updated_at
                FROM artifact_tasks
                WHERE notebook_id = ?
                ORDER BY updated_at DESC
                """,
                (notebook_id,),
            )
            rows = await cursor.fetchall()
        records: list[ArtifactTaskRecord] = []
        for row in rows:
            records.append(
                ArtifactTaskRecord(
                    task_id=str(row[0]),
                    notebook_id=str(row[1]),
                    kind=str(row[2]),
                    status=str(row[3]),
                    metadata=json.loads(row[4]) if row[4] else {},
                    created_at=float(row[5]),
                    updated_at=float(row[6]),
                )
            )
        return records

    async def _ensure(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await asyncio.to_thread(self.db_path.parent.mkdir, parents=True, exist_ok=True)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS artifact_tasks (
                        task_id TEXT PRIMARY KEY,
                        notebook_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                    """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_artifact_tasks_notebook_updated
                    ON artifact_tasks (notebook_id, updated_at DESC)
                    """
                )
                await db.commit()
            self._initialized = True
