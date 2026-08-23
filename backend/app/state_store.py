from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

try:
    import psycopg
    from psycopg.types.json import Json
except ImportError:  # pragma: no cover - optional until deps are installed in deployment
    psycopg = None
    Json = None


@dataclass
class StateStore:
    dsn: Optional[str] = None
    _memory: dict[str, dict[str, Any]] = field(default_factory=dict)
    _schema_ready: bool = False

    @classmethod
    def from_env(cls) -> "StateStore":
        return cls(dsn=os.getenv("DATABASE_URL"))

    def _connect(self):
        if not self.dsn or psycopg is None:
            return None
        return psycopg.connect(self.dsn, autocommit=True)

    def connection_status(self) -> dict:
        """Definitive, live answer to 'is persistence actually working right now' — used by
        /health so this never has to be diagnosed by symptom-watching again."""
        if not self.dsn:
            return {"configured": False, "connected": False, "detail": "DATABASE_URL is not set; state is in-memory only and resets on every deploy."}
        if psycopg is None:
            return {"configured": True, "connected": False, "detail": "DATABASE_URL is set but the psycopg driver isn't installed."}
        try:
            conn = self._connect()
            conn.close()
            return {"configured": True, "connected": True, "detail": "Connected to Postgres; state persists across deploys."}
        except Exception as error:
            return {"configured": True, "connected": False, "detail": f"DATABASE_URL is set but the connection failed: {error}"}

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        conn = self._connect()
        if conn is None:
            return
        with conn.cursor() as cursor:
            cursor.execute(
                """
                create table if not exists agent_state (
                    state_key text primary key,
                    payload jsonb not null,
                    updated_at timestamptz not null default now()
                );
                """
            )
            cursor.execute(
                """
                create table if not exists agent_events (
                    id bigserial primary key,
                    event_type text not null,
                    payload jsonb not null,
                    created_at timestamptz not null default now()
                );
                """
            )
        conn.close()
        self._schema_ready = True

    def load(self, state_key: str, default: dict[str, Any]) -> dict[str, Any]:
        conn = self._connect()
        if conn is None:
            return copy.deepcopy(self._memory.get(state_key, default))
        self.ensure_schema()
        with conn.cursor() as cursor:
            cursor.execute("select payload from agent_state where state_key = %s", (state_key,))
            row = cursor.fetchone()
        conn.close()
        if row is None:
            return copy.deepcopy(default)
        payload = row[0]
        return dict(payload)

    def save(self, state_key: str, payload: dict[str, Any]) -> None:
        conn = self._connect()
        if conn is None:
            self._memory[state_key] = copy.deepcopy(payload)
            return
        self.ensure_schema()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                insert into agent_state (state_key, payload, updated_at)
                values (%s, %s, now())
                on conflict (state_key)
                do update set payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (state_key, Json(payload) if Json is not None else json.dumps(payload)),
            )
        conn.close()

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        conn = self._connect()
        if conn is None:
            return
        self.ensure_schema()
        with conn.cursor() as cursor:
            cursor.execute(
                "insert into agent_events (event_type, payload) values (%s, %s)",
                (event_type, Json(payload) if Json is not None else json.dumps(payload)),
            )
        conn.close()

    def load_events(self, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._connect()
        if conn is None:
            return []
        self.ensure_schema()
        with conn.cursor() as cursor:
            cursor.execute(
                "select event_type, payload, created_at from agent_events order by id desc limit %s",
                (limit,),
            )
            rows = cursor.fetchall()
        conn.close()
        return [
            {
                "event_type": row[0],
                "payload": row[1],
                "created_at": row[2].isoformat() if isinstance(row[2], datetime) else str(row[2]),
            }
            for row in rows
        ]
