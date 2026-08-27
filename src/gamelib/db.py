"""Camada SQLite (stdlib, sem ORM). Schema em snake_case plural, índices em
colunas de filtro/JOIN, `CREATE TABLE IF NOT EXISTS` (idempotente) — ver
`.claude/rules/sql-architecture.md`.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from gamelib.models import Game

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    name TEXT NOT NULL,
    cover_url TEXT,
    playtime_minutes INTEGER,
    last_played_at TEXT,
    achievements_unlocked INTEGER,
    achievements_total INTEGER,
    completion_status TEXT NOT NULL DEFAULT 'unknown',
    added_at TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    first_synced_at TEXT NOT NULL,
    last_synced_at TEXT NOT NULL,
    UNIQUE(platform, external_id)
);
CREATE INDEX IF NOT EXISTS idx_games_platform ON games(platform);
CREATE INDEX IF NOT EXISTS idx_games_completion_status ON games(completion_status);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    games_found INTEGER,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_sync_runs_platform ON sync_runs(platform);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat()


def upsert_game(conn: sqlite3.Connection, game: Game) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO games (
            platform, external_id, name, cover_url, playtime_minutes,
            last_played_at, achievements_unlocked, achievements_total,
            completion_status, added_at, raw_json, first_synced_at, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(platform, external_id) DO UPDATE SET
            name=excluded.name,
            cover_url=excluded.cover_url,
            playtime_minutes=excluded.playtime_minutes,
            last_played_at=excluded.last_played_at,
            achievements_unlocked=excluded.achievements_unlocked,
            achievements_total=excluded.achievements_total,
            completion_status=excluded.completion_status,
            added_at=excluded.added_at,
            raw_json=excluded.raw_json,
            last_synced_at=excluded.last_synced_at
        """,
        (
            game.platform,
            game.external_id,
            game.name,
            game.cover_url,
            game.playtime_minutes,
            game.last_played_at.isoformat() if game.last_played_at else None,
            game.achievements_unlocked,
            game.achievements_total,
            game.completion_status,
            game.added_at.isoformat() if game.added_at else None,
            json.dumps(game.raw, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()


def list_games(
    conn: sqlite3.Connection,
    platform: str | None = None,
    query: str | None = None,
    status: str | None = None,
    sort: str = "name",
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM games WHERE 1=1"
    params: list[Any] = []
    if platform:
        sql += " AND platform = ?"
        params.append(platform)
    if status:
        sql += " AND completion_status = ?"
        params.append(status)
    if query:
        sql += " AND name LIKE ? COLLATE NOCASE"
        params.append(f"%{query}%")
    sort_columns = {
        "name": "name COLLATE NOCASE ASC",
        "playtime": "playtime_minutes DESC",
        "last_played": "last_played_at DESC",
        "platform": "platform ASC, name COLLATE NOCASE ASC",
    }
    sql += f" ORDER BY {sort_columns.get(sort, sort_columns['name'])}"
    return conn.execute(sql, params).fetchall()


def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    total_games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    total_playtime = conn.execute(
        "SELECT COALESCE(SUM(playtime_minutes), 0) FROM games"
    ).fetchone()[0]
    by_platform = {
        row["platform"]: row["n"]
        for row in conn.execute(
            "SELECT platform, COUNT(*) AS n FROM games GROUP BY platform"
        ).fetchall()
    }
    by_status = {
        row["completion_status"]: row["n"]
        for row in conn.execute(
            "SELECT completion_status, COUNT(*) AS n FROM games GROUP BY completion_status"
        ).fetchall()
    }
    return {
        "total_games": total_games,
        "total_playtime_minutes": total_playtime,
        "by_platform": by_platform,
        "by_status": by_status,
    }


def record_sync_run(
    conn: sqlite3.Connection,
    platform: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    games_found: int | None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO sync_runs
            (platform, started_at, finished_at, status, games_found, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            platform,
            started_at.isoformat(),
            finished_at.isoformat(),
            status,
            games_found,
            error_message,
        ),
    )
    conn.commit()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["raw"] = json.loads(d.pop("raw_json") or "{}")
    d["last_played_at"] = _parse_dt(d.get("last_played_at"))
    d["added_at"] = _parse_date(d.get("added_at"))
    return d


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
