"""
Postgres data access layer (replaces the Supabase client).

Works with any PostgreSQL database — Neon in production, a local Postgres in
development. It exposes the same small query-builder API the services were
already written against, so the business logic did not have to change:

    db = get_db()
    db.table("tasks").select("*", count="exact").eq("status", "pending") \
        .order("created_at", desc=True).range(0, 49).execute()
    db.table("tasks").insert({...}).execute()
    db.table("tasks").update({...}).eq("id", task_id).execute()
    db.table("rooms").upsert([...], on_conflict="floor_id,room_number,name").execute()

Uploaded photos / audio are stored in the `media` table and served by the
API itself at /media/{bucket}/{path} (see app/routers/media.py).
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Optional
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _ident(name: str) -> str:
    """Validate and quote a table/column identifier (never user input, but be strict)."""
    name = name.strip()
    if not _IDENT.match(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return f'"{name}"'


def _jsonable(v: Any) -> Any:
    """Return values the way the old REST client did (UUIDs/dates as strings)."""
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _row(r: dict) -> dict:
    return {k: _jsonable(v) for k, v in r.items()}


@dataclass
class Result:
    data: list
    count: Optional[int] = None


# ── Connection management ────────────────────────────────────

class Database:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._conn: Optional[psycopg.Connection] = None
        self._lock = threading.RLock()

    def _connect(self) -> psycopg.Connection:
        # prepare_threshold=None keeps it compatible with PgBouncer / Neon pooled URLs
        return psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)

    def run(self, sql: str, params: list | tuple = ()) -> list[dict]:
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._conn is None or self._conn.closed:
                        self._conn = self._connect()
                    with self._conn.cursor() as cur:
                        cur.execute(sql, params or None)
                        return list(cur.fetchall()) if cur.description else []
                except (psycopg.OperationalError, psycopg.InterfaceError):
                    # Serverless Postgres drops idle connections — reconnect once.
                    try:
                        if self._conn is not None:
                            self._conn.close()
                    finally:
                        self._conn = None
                    if attempt == 2:
                        raise
        return []

    # Supabase-compatible surface
    def table(self, name: str) -> "Query":
        return Query(self, name)

    @property
    def storage(self) -> "Storage":
        return Storage(self)


# ── Query builder ────────────────────────────────────────────

class Query:
    def __init__(self, db: Database, table: str):
        self._db = db
        self._table = table
        self._op = "select"
        self._columns = "*"
        self._count: Optional[str] = None
        self._where: list[tuple[str, Any]] = []
        self._order: list[tuple[str, bool]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._payload: Any = None
        self._on_conflict: Optional[str] = None

    # reads
    def select(self, columns: str = "*", count: Optional[str] = None) -> "Query":
        self._op, self._columns, self._count = "select", columns, count
        return self

    def eq(self, column: str, value: Any) -> "Query":
        self._where.append((f"{_ident(column)} = %s", _jsonable(value)))
        return self

    def in_(self, column: str, values) -> "Query":
        self._where.append((f"{_ident(column)}::text = ANY(%s::text[])", [str(_jsonable(v)) for v in values]))
        return self

    def order(self, column: str, desc: bool = False) -> "Query":
        self._order.append((column, desc))
        return self

    def range(self, start: int, end: int) -> "Query":
        self._offset, self._limit = start, end - start + 1
        return self

    def limit(self, n: int) -> "Query":
        self._limit = n
        return self

    # writes
    def insert(self, payload) -> "Query":
        self._op, self._payload = "insert", payload
        return self

    def update(self, payload: dict) -> "Query":
        self._op, self._payload = "update", payload
        return self

    def upsert(self, payload, on_conflict: Optional[str] = None) -> "Query":
        self._op, self._payload, self._on_conflict = "upsert", payload, on_conflict or "id"
        return self

    # helpers
    def _where_sql(self) -> tuple[str, list]:
        if not self._where:
            return "", []
        return " WHERE " + " AND ".join(c for c, _ in self._where), [v for _, v in self._where]

    def _parse_columns(self) -> tuple[list[str], list[str]]:
        """Split 'a, b, other_table(*)' into plain columns and embedded tables."""
        cols, embeds = [], []
        for part in [p.strip() for p in self._columns.split(",") if p.strip()]:
            m = re.match(r"^([a-z_][a-z0-9_]*)\(\*\)$", part)
            if m:
                embeds.append(m.group(1))
            else:
                cols.append(part)
        return cols or ["*"], embeds

    def execute(self) -> Result:
        t = _ident(self._table)

        if self._op == "select":
            cols, embeds = self._parse_columns()
            col_sql = ", ".join("*" if c == "*" else _ident(c) for c in cols)
            where, params = self._where_sql()
            sql = f"SELECT {col_sql} FROM {t}{where}"
            if self._order:
                sql += " ORDER BY " + ", ".join(f"{_ident(c)} {'DESC' if d else 'ASC'}" for c, d in self._order)
            if self._limit is not None:
                sql += f" LIMIT {int(self._limit)}"
            if self._offset:
                sql += f" OFFSET {int(self._offset)}"
            rows = [_row(r) for r in self._db.run(sql, params)]
            for emb in embeds:  # profiles(*) ← student_profiles(*) etc., linked through user_id
                ids = [r["user_id"] for r in rows if r.get("user_id")]
                children = [_row(c) for c in self._db.run(f"SELECT * FROM {_ident(emb)} WHERE user_id::text = ANY(%s::text[])", [ids])] if ids else []
                for r in rows:
                    r[emb] = [c for c in children if c.get("user_id") == r.get("user_id")]
            total = None
            if self._count:
                total = self._db.run(f"SELECT count(*) AS n FROM {t}{where}", params)[0]["n"]
            return Result(rows, total)

        if self._op in ("insert", "upsert"):
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            if not items:
                return Result([])
            if self._op == "upsert":  # one row per conflict key, or Postgres rejects the batch
                keys = [k.strip() for k in self._on_conflict.split(",")]
                dedup = {}
                for it in items:
                    dedup[tuple(str(it.get(k)) for k in keys)] = it
                items = list(dedup.values())
            columns = list(dict.fromkeys(k for it in items for k in it))
            col_sql = ", ".join(_ident(c) for c in columns)
            row_sql = "(" + ", ".join(["%s"] * len(columns)) + ")"
            params = [_jsonable(it.get(c)) for it in items for c in columns]
            sql = f"INSERT INTO {t} ({col_sql}) VALUES " + ", ".join([row_sql] * len(items))
            if self._op == "upsert":
                conflict = [k.strip() for k in self._on_conflict.split(",")]
                updates = [c for c in columns if c not in conflict] or conflict[:1]
                sql += f" ON CONFLICT ({', '.join(_ident(c) for c in conflict)}) DO UPDATE SET " + \
                       ", ".join(f"{_ident(c)} = EXCLUDED.{_ident(c)}" for c in updates)
            sql += " RETURNING *"
            return Result([_row(r) for r in self._db.run(sql, params)])

        if self._op == "update":
            if not self._payload:
                return Result([])
            sets = ", ".join(f"{_ident(c)} = %s" for c in self._payload)
            where, wparams = self._where_sql()
            if not where:
                raise ValueError("Refusing to UPDATE without a filter")
            sql = f"UPDATE {t} SET {sets}{where} RETURNING *"
            return Result([_row(r) for r in self._db.run(sql, [_jsonable(v) for v in self._payload.values()] + wparams)])

        raise ValueError(f"Unsupported operation {self._op}")


# ── Media storage (photos / audio kept in Postgres) ──────────

def public_base_url() -> str:
    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    vercel = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL") or os.environ.get("VERCEL_URL")
    if vercel:
        return f"https://{vercel}"
    return "http://localhost:8000"


class Bucket:
    def __init__(self, db: Database, name: str):
        self._db, self._name = db, name

    def upload(self, path: str, file: bytes, file_options: Optional[dict] = None):
        content_type = (file_options or {}).get("content-type", "application/octet-stream")
        self._db.run(
            "INSERT INTO media (bucket, path, content_type, data) VALUES (%s, %s, %s, %s)",
            [self._name, path, content_type, file],
        )
        return {"path": path}

    def get_public_url(self, path: str) -> str:
        return f"{public_base_url()}/media/{self._name}/{path}"


class Storage:
    def __init__(self, db: Database):
        self._db = db

    def from_(self, bucket: str) -> Bucket:
        return Bucket(self._db, bucket)


@lru_cache()
def get_db() -> Database:
    """Shared database handle (one connection, reconnects automatically)."""
    return Database(get_settings().database_url)
