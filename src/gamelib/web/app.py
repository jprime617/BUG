"""Dashboard FastAPI: rotas finas, formatação em `presentation.py`, dados em
`gamelib.db`. Sem estado em memória — cada request abre/fecha sua conexão.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gamelib import db
from gamelib.config import load_settings
from gamelib.metadata import MetadataError, get_or_fetch_metadata
from gamelib.models import PLATFORMS
from gamelib.sync import run_sync
from gamelib.web.presentation import (
    PLATFORM_META,
    STATUS_LABELS,
    format_achievements,
    format_playtime,
    format_rating_stars,
    format_release_date,
)

WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Biblioteca de Jogos")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.filters["playtime"] = format_playtime
templates.env.filters["achievements"] = format_achievements
templates.env.filters["release_date"] = format_release_date
templates.env.filters["rating_stars"] = format_rating_stars


def get_conn():
    settings = load_settings()
    conn = db.connect(settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def _composition(stats: dict) -> list[dict]:
    total = stats["total_games"] or 1
    return [
        {
            "platform": platform,
            "label": PLATFORM_META[platform]["label"],
            "color": PLATFORM_META[platform]["color"],
            "count": stats["by_platform"].get(platform, 0),
            "pct": round(stats["by_platform"].get(platform, 0) / total * 100, 1),
        }
        for platform in PLATFORMS
        if stats["by_platform"].get(platform, 0) > 0
    ]


def _games(conn, platform: str, q: str, status: str, sort: str) -> list[dict]:
    rows = db.list_games(
        conn, platform=platform or None, query=q or None, status=status or None, sort=sort or "name"
    )
    return [db.row_to_dict(row) for row in rows]


@app.get("/")
def index(
    request: Request,
    conn: Conn,
    platform: str = "",
    q: str = "",
    status: str = "",
    sort: str = "name",
):
    stats = db.get_stats(conn)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "stats": stats,
            "composition": _composition(stats),
            "games": _games(conn, platform, q, status, sort),
            "platforms": PLATFORMS,
            "platform_meta": PLATFORM_META,
            "status_labels": STATUS_LABELS,
            "filters": {"platform": platform, "q": q, "status": status, "sort": sort},
        },
    )


@app.get("/partials/games")
def partial_games(
    request: Request,
    conn: Conn,
    platform: str = "",
    q: str = "",
    status: str = "",
    sort: str = "name",
):
    return templates.TemplateResponse(
        request,
        "_games_grid.html",
        {
            "games": _games(conn, platform, q, status, sort),
            "platform_meta": PLATFORM_META,
            "status_labels": STATUS_LABELS,
        },
    )


@app.get("/games/{game_id}/modal")
def game_modal(request: Request, conn: Conn, game_id: int):
    row = db.get_game(conn, game_id)
    if row is None:
        return templates.TemplateResponse(
            request,
            "games/_game_modal.html",
            {"game": None, "metadata": None, "error": "Jogo não encontrado."},
        )

    game = db.row_to_dict(row)
    settings = load_settings()
    metadata, error = None, None
    try:
        metadata = get_or_fetch_metadata(conn, game_id, game["name"], settings.rawg_api_key)
    except MetadataError as exc:
        error = str(exc)

    return templates.TemplateResponse(
        request,
        "games/_game_modal.html",
        {"game": game, "metadata": metadata, "error": error},
    )


@app.post("/sync")
def sync_now(request: Request, conn: Conn):
    report = run_sync()
    stats = db.get_stats(conn)
    response = templates.TemplateResponse(
        request,
        "_stats.html",
        {
            "stats": stats,
            "composition": _composition(stats),
            "sync_report": report,
            "platform_meta": PLATFORM_META,
        },
    )
    response.headers["HX-Trigger"] = "sync-done"
    return response
