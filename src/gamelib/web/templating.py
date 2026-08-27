"""Instância única de `Jinja2Templates`, compartilhada entre `app.py` e os
routers (`routes_auth.py`, `routes_settings.py`) — extraído pra módulo
próprio pra evitar import circular (os routers não podem importar de
`app.py`, que por sua vez os inclui via `include_router`).
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from gamelib.web.presentation import (
    format_achievements,
    format_playtime,
    format_rating_stars,
    format_release_date,
    metacritic_tier,
)

WEB_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.filters["playtime"] = format_playtime
templates.env.filters["achievements"] = format_achievements
templates.env.filters["release_date"] = format_release_date
templates.env.filters["rating_stars"] = format_rating_stars
templates.env.filters["metacritic_tier"] = metacritic_tier
