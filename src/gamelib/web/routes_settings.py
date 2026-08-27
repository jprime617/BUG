"""Configurações dinâmicas — substitui parte do `.env` (chaves de API de
terceiros). Restrito ao admin (ver `gamelib.web.auth.require_admin`).

Campos nunca são re-preenchidos com o valor real no formulário (só um label
"configurado" + valor mascarado) — evita que reenviar o form sem mexer num
campo grave o placeholder mascarado por cima do segredo de verdade.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Form, Request

from gamelib import settings_store
from gamelib.collectors.base import CollectorError
from gamelib.collectors.psn import PsnCollector
from gamelib.collectors.steam import SteamCollector
from gamelib.collectors.xbox import XboxCollector
from gamelib.config import load_settings
from gamelib.metadata import RAWG_BASE_URL
from gamelib.web.auth import require_admin
from gamelib.web.deps import Conn
from gamelib.web.templating import templates

router = APIRouter(dependencies=[Depends(require_admin)])

SETTINGS_FIELDS = [
    {"key": "rawg_api_key", "label": "RAWG API Key", "integration": "rawg"},
    {"key": "steam_api_key", "label": "Steam API Key", "integration": "steam"},
    {"key": "steam_id64", "label": "Steam ID64", "integration": "steam"},
    {"key": "psn_npsso", "label": "PSN NPSSO", "integration": "psn"},
    {"key": "xbox_openxbl_key", "label": "Xbox OpenXBL Key", "integration": "xbox"},
]


def _current_fields() -> list[dict]:
    settings = load_settings()
    fields = []
    for f in SETTINGS_FIELDS:
        value = getattr(settings, f["key"])
        fields.append(
            {
                **f,
                "configured": bool(value),
                "masked": settings_store.mask(value) if value else "",
            }
        )
    return fields


@router.get("/configuracoes")
def configuracoes_form(request: Request):
    return templates.TemplateResponse(
        request, "configuracoes.html", {"fields": _current_fields(), "saved": False}
    )


@router.post("/configuracoes")
def configuracoes_submit(
    request: Request,
    conn: Conn,
    rawg_api_key: str = Form(default=""),
    steam_api_key: str = Form(default=""),
    steam_id64: str = Form(default=""),
    psn_npsso: str = Form(default=""),
    xbox_openxbl_key: str = Form(default=""),
):
    user = getattr(request.state, "user", None)
    updated_by = getattr(user, "email", None)

    submitted = {
        "rawg_api_key": rawg_api_key,
        "steam_api_key": steam_api_key,
        "steam_id64": steam_id64,
        "psn_npsso": psn_npsso,
        "xbox_openxbl_key": xbox_openxbl_key,
    }
    for key, raw_value in submitted.items():
        value = raw_value.strip()
        if value:
            settings_store.set_setting(
                key, value, encrypted=True, updated_by=updated_by, client=conn
            )

    return templates.TemplateResponse(
        request, "configuracoes.html", {"fields": _current_fields(), "saved": True}
    )


def _test_rawg(settings) -> tuple[bool, str]:
    if not settings.rawg_api_key:
        return False, "RAWG_API_KEY não configurada."
    try:
        resp = httpx.get(
            RAWG_BASE_URL, params={"key": settings.rawg_api_key, "page_size": 1}, timeout=10
        )
    except httpx.HTTPError as exc:
        return False, f"Falha de rede: {exc}"
    if resp.status_code == 200:
        return True, "Conexão OK."
    return False, f"RAWG retornou HTTP {resp.status_code}."


def _test_collector(collector, settings) -> tuple[bool, str]:
    if not collector.is_configured(settings):
        return False, "Credenciais ausentes."
    try:
        games = collector.fetch(settings)
    except CollectorError as exc:
        return False, str(exc)
    return True, f"Conexão OK — {len(games)} jogo(s) encontrado(s)."


_TESTERS = {
    "rawg": _test_rawg,
    "steam": lambda settings: _test_collector(SteamCollector(), settings),
    "psn": lambda settings: _test_collector(PsnCollector(), settings),
    "xbox": lambda settings: _test_collector(XboxCollector(), settings),
}


@router.post("/configuracoes/testar/{integration}")
def testar_conexao(request: Request, integration: str):
    settings = load_settings()
    tester = _TESTERS.get(integration)
    if tester is None:
        ok, message = False, "Integração desconhecida."
    else:
        ok, message = tester(settings)
    return templates.TemplateResponse(request, "_test_result.html", {"ok": ok, "message": message})
