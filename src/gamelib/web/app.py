"""Dashboard FastAPI: rotas finas, formatação em `presentation.py`, dados em
`gamelib.db`. Sem estado em memória — cada request abre/fecha sua conexão.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from gamelib import db
from gamelib.config import load_settings
from gamelib.metadata import MetadataError, get_or_fetch_metadata
from gamelib.models import PLATFORMS
from gamelib.sync import run_sync_iter
from gamelib.web.auth import is_public_path, verify_session
from gamelib.web.deps import Conn
from gamelib.web.presentation import PLATFORM_META, STATUS_LABELS
from gamelib.web.routes_auth import router as auth_router
from gamelib.web.routes_settings import router as settings_router
from gamelib.web.templating import WEB_DIR, templates

app = FastAPI(title="Biblioteca de Jogos")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
app.include_router(auth_router)
app.include_router(settings_router)


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Fecha por padrão: só as rotas em `PUBLIC_PATHS`/`/static` passam sem
    sessão. Uma rota nova esquecida fica protegida automaticamente.
    """
    if is_public_path(request.url.path):
        return await call_next(request)

    # `verify_session` bate no Supabase (bloqueante) — roda fora do loop
    # assíncrono pra não travar requests concorrentes.
    user = await run_in_threadpool(verify_session, request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    request.state.user = user
    return await call_next(request)


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


def _games(conn, user_id: str, platform: str, q: str, status: str, sort: str) -> list[dict]:
    rows = db.list_games(
        conn,
        user_id,
        platform=platform or None,
        query=q or None,
        status=status or None,
        sort=sort or "name",
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
    user_id = request.state.user.id
    stats = db.get_stats(conn, user_id)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "stats": stats,
            "composition": _composition(stats),
            "games": _games(conn, user_id, platform, q, status, sort),
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
    user_id = request.state.user.id
    return templates.TemplateResponse(
        request,
        "_games_grid.html",
        {
            "games": _games(conn, user_id, platform, q, status, sort),
            "platform_meta": PLATFORM_META,
            "status_labels": STATUS_LABELS,
        },
    )


@app.get("/partials/stats")
def partial_stats(request: Request, conn: Conn):
    """Reassenta `#stats` com os números reais depois de um sync — chamado
    pelo próprio JS de progresso (`sync-progress.js`) ao receber o evento
    `complete` do stream, não por htmx declarativo.
    """
    user_id = request.state.user.id
    stats = db.get_stats(conn, user_id)
    return templates.TemplateResponse(
        request,
        "_stats.html",
        {
            "stats": stats,
            "composition": _composition(stats),
            "platforms": PLATFORMS,
            "platform_meta": PLATFORM_META,
        },
    )


def _game_context(conn, user_id: str, game_id: int) -> dict:
    row = db.get_game(conn, user_id, game_id)
    if row is None:
        return {"game": None, "metadata": None, "error": "Jogo não encontrado."}

    game = db.row_to_dict(row)
    settings = load_settings(user_id)
    metadata, error = None, None
    try:
        metadata = get_or_fetch_metadata(conn, game_id, game["name"], settings.rawg_api_key)
    except MetadataError as exc:
        error = str(exc)

    return {"game": game, "metadata": metadata, "error": error}


@app.get("/games/{game_id}")
def game_detail(request: Request, conn: Conn, game_id: int):
    ctx = _game_context(conn, request.state.user.id, game_id)
    return templates.TemplateResponse(
        request,
        "games/detail.html",
        {**ctx, "platform_meta": PLATFORM_META, "status_labels": STATUS_LABELS},
        status_code=404 if ctx["game"] is None else 200,
    )


@app.get("/games/{game_id}/modal")
def game_modal(request: Request, conn: Conn, game_id: int):
    ctx = _game_context(conn, request.state.user.id, game_id)
    return templates.TemplateResponse(
        request,
        "games/_game_modal.html",
        {**ctx, "platform_meta": PLATFORM_META, "status_labels": STATUS_LABELS},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _sync_events(user_id: str, conn):
    for event in run_sync_iter(user_id, client=conn):
        if event.type == "targets":
            yield _sse("targets", {"targets": event.targets})
        elif event.type == "platform_done":
            result = event.result
            yield _sse(
                "platform_done",
                {
                    "platform": event.platform,
                    "index": event.index,
                    "total": event.total,
                    "status": result.status,
                    "games_found": result.games_found,
                    "error": result.error,
                },
            )
    yield _sse("complete", {})


@app.get("/sync/stream")
def sync_stream(request: Request, conn: Conn):
    user_id = request.state.user.id
    return StreamingResponse(
        _sync_events(user_id, conn),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
