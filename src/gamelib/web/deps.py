"""Dependency compartilhada entre `app.py` e os routers (`routes_settings.py`
etc.) — extraída pra módulo próprio pelo mesmo motivo de `templating.py`:
routers não podem importar de `app.py`, que os inclui via `include_router`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from supabase import Client

from gamelib import db
from gamelib.config import load_settings


def get_conn() -> Client:
    settings = load_settings()
    return db.connect(settings)


Conn = Annotated[Client, Depends(get_conn)]
