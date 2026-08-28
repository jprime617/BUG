"""Camada Supabase Postgres (via supabase-py, PostgREST). Schema versionado
em `supabase/schema.sql` — ver `.claude/rules/sql-architecture.md`. Mesma
API pública de quando isto era SQLite: quem chama continua acessando campos
por `row["nome"]`, sem mudança em `app.py`/templates além de `connect()`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from supabase import Client

from gamelib.config import Settings
from gamelib.models import Game
from gamelib.supabase_client import get_service_client


def connect(settings: Settings) -> Client:
    return get_service_client(settings)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def upsert_game(conn: Client, user_id: str, game: Game) -> None:
    # `first_synced_at` fica de fora do payload de propósito: o PostgREST só
    # faz SET das colunas presentes no corpo do upsert, então omiti-la
    # preserva o valor original num conflito e deixa o DEFAULT now() do
    # banco preencher só no insert — equivalente ao ON CONFLICT DO UPDATE
    # SET explícito (sem first_synced_at) que isto tinha em SQLite.
    payload = {
        "user_id": user_id,
        "platform": game.platform,
        "external_id": game.external_id,
        "name": game.name,
        "cover_url": game.cover_url,
        "playtime_minutes": game.playtime_minutes,
        "last_played_at": game.last_played_at.isoformat() if game.last_played_at else None,
        "achievements_unlocked": game.achievements_unlocked,
        "achievements_total": game.achievements_total,
        "completion_status": game.completion_status,
        "added_at": game.added_at.isoformat() if game.added_at else None,
        "raw_json": game.raw,
        "last_synced_at": _now(),
    }
    conn.table("games").upsert(payload, on_conflict="user_id,platform,external_id").execute()


def list_games(
    conn: Client,
    user_id: str,
    platform: str | None = None,
    query: str | None = None,
    status: str | None = None,
    sort: str = "name",
) -> list[dict]:
    q = conn.table("games").select("*").eq("user_id", user_id)
    if platform:
        q = q.eq("platform", platform)
    if status:
        q = q.eq("completion_status", status)
    if query:
        q = q.ilike("name", f"%{query}%")

    if sort == "playtime":
        q = q.order("playtime_minutes", desc=True)
    elif sort == "last_played":
        q = q.order("last_played_at", desc=True)
    elif sort == "platform":
        q = q.order("platform").order("name_sort")
    else:
        q = q.order("name_sort")

    return q.execute().data


def get_game(conn: Client, user_id: str, game_id: int) -> dict | None:
    # `.maybe_single()` faz `.execute()` devolver `None` puro (não uma
    # resposta com `.data = None`) quando a query não acha linha. Filtra por
    # user_id também: impede um usuário de acessar o jogo de outro só
    # adivinhando o id (IDOR).
    response = (
        conn.table("games")
        .select("*")
        .eq("id", game_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return response.data if response is not None else None


def get_game_metadata(conn: Client, game_id: int) -> dict | None:
    response = (
        conn.table("game_metadata").select("*").eq("game_id", game_id).maybe_single().execute()
    )
    return response.data if response is not None else None


def upsert_game_metadata(
    conn: Client,
    game_id: int,
    release_date: str | None,
    genres: list[str],
    rating: float | None,
    metacritic: int | None,
    description: str | None,
    screenshots: list[str],
) -> None:
    conn.table("game_metadata").upsert(
        {
            "game_id": game_id,
            "release_date": release_date,
            "genres": genres,
            "rating": rating,
            "metacritic": metacritic,
            "description": description,
            "screenshots": screenshots,
            "fetched_at": _now(),
        },
        on_conflict="game_id",
    ).execute()


def get_stats(conn: Client, user_id: str) -> dict[str, Any]:
    rows = (
        conn.table("games")
        .select("platform, completion_status, playtime_minutes")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    total_games = len(rows)
    total_playtime = sum(r.get("playtime_minutes") or 0 for r in rows)
    by_platform: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in rows:
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + 1
        by_status[r["completion_status"]] = by_status.get(r["completion_status"], 0) + 1
    return {
        "total_games": total_games,
        "total_playtime_minutes": total_playtime,
        "by_platform": by_platform,
        "by_status": by_status,
    }


def record_sync_run(
    conn: Client,
    user_id: str,
    platform: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    games_found: int | None,
    error_message: str | None = None,
) -> None:
    conn.table("sync_runs").insert(
        {
            "user_id": user_id,
            "platform": platform,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "status": status,
            "games_found": games_found,
            "error_message": error_message,
        }
    ).execute()


def row_to_dict(row: dict) -> dict[str, Any]:
    d = dict(row)
    d["raw"] = d.pop("raw_json", None) or {}
    d["last_played_at"] = _parse_dt(d.get("last_played_at"))
    d["added_at"] = _parse_date(d.get("added_at"))
    return d


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
