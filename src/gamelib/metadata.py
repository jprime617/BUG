"""Metadados externos (RAWG) para o modal de detalhes do jogo — cache local
(`game_metadata`) com TTL para não bater na API a cada clique. Mesmo padrão
de chamada/erro de `collectors/nintendo_csv.py` (httpx + log, sem exceção
não tratada até a fronteira do endpoint).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from gamelib import db

log = logging.getLogger("gamelib.metadata")

RAWG_BASE_URL = "https://api.rawg.io/api/games"
CACHE_TTL = timedelta(days=30)
REQUEST_TIMEOUT = 5.0


class MetadataError(RuntimeError):
    """Falha ao obter metadados externos (rede, timeout, config ausente, não encontrado)."""


@dataclass
class GameMetadata:
    release_date: str | None
    genres: list[str]
    rating: float | None
    video_url: str | None


def _row_is_fresh(row: sqlite3.Row) -> bool:
    fetched = datetime.fromisoformat(row["fetched_at"])
    return datetime.now(UTC) - fetched <= CACHE_TTL


def get_cached_metadata(conn: sqlite3.Connection, game_id: int) -> GameMetadata | None:
    row = db.get_game_metadata(conn, game_id)
    if row is None or not _row_is_fresh(row):
        return None
    return GameMetadata(
        release_date=row["release_date"],
        genres=list(json.loads(row["genres"])),
        rating=row["rating"],
        video_url=row["video_url"],
    )


def _fetch_trailer_url(client: httpx.Client, rawg_id: int, api_key: str) -> str | None:
    try:
        resp = client.get(f"{RAWG_BASE_URL}/{rawg_id}/movies", params={"key": api_key})
    except httpx.HTTPError as exc:
        log.debug("metadata: falha ao buscar trailer (RAWG id=%s): %s", rawg_id, exc)
        return None
    if resp.status_code != 200:
        log.debug(
            "metadata: busca de trailer (RAWG id=%s) retornou HTTP %d", rawg_id, resp.status_code
        )
        return None
    results = resp.json().get("results", [])
    if not results:
        return None
    data = results[0].get("data") or {}
    return data.get("max") or data.get("480") or results[0].get("preview")


def fetch_metadata_from_rawg(client: httpx.Client, name: str, api_key: str) -> GameMetadata:
    try:
        resp = client.get(RAWG_BASE_URL, params={"key": api_key, "search": name, "page_size": 1})
    except httpx.HTTPError as exc:
        raise MetadataError(f"falha ao contatar a RAWG: {exc}") from exc
    if resp.status_code != 200:
        raise MetadataError(f"RAWG retornou HTTP {resp.status_code}")

    results = resp.json().get("results", [])
    if not results:
        raise MetadataError(f"jogo {name!r} não encontrado na RAWG")

    game = results[0]
    return GameMetadata(
        release_date=game.get("released"),
        genres=[g["name"] for g in game.get("genres", [])],
        rating=game.get("rating"),
        video_url=_fetch_trailer_url(client, game["id"], api_key),
    )


def get_or_fetch_metadata(
    conn: sqlite3.Connection, game_id: int, game_name: str, rawg_api_key: str | None
) -> GameMetadata:
    """Cache-first: retorna do SQLite se fresco; senão busca na RAWG e persiste.

    Levanta `MetadataError` (nunca outra exceção) se a chave não estiver
    configurada ou a busca externa falhar — quem chama decide como exibir.
    """
    cached = get_cached_metadata(conn, game_id)
    if cached is not None:
        return cached
    if not rawg_api_key:
        raise MetadataError(
            "RAWG_API_KEY não configurada — defina no .env para ver detalhes do jogo"
        )

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        metadata = fetch_metadata_from_rawg(client, game_name, rawg_api_key)

    db.upsert_game_metadata(
        conn,
        game_id,
        release_date=metadata.release_date,
        genres=metadata.genres,
        rating=metadata.rating,
        video_url=metadata.video_url,
    )
    return metadata
