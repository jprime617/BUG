"""Configurações dinâmicas por usuário — credenciais de plataforma
(Steam/PSN/Xbox) que substituíam parte do `.env`. Acesso é o mesmo de
qualquer rota autenticada (garantido pelo middleware `require_login` em
`app.py`) — cada usuário só lê/grava a própria linha em `settings`.

RAWG_API_KEY não está aqui: é credencial global (metadado público de jogos,
não uma conta pessoal), configurada só via variável de ambiente.

Campos nunca são re-preenchidos com o valor real no formulário (só um label
"configurado" + valor mascarado) — evita que reenviar o form sem mexer num
campo grave o placeholder mascarado por cima do segredo de verdade.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request

from gamelib import settings_store
from gamelib.collectors.base import CollectorError
from gamelib.collectors.psn import PsnCollector
from gamelib.collectors.steam import SteamCollector
from gamelib.collectors.xbox import XboxCollector
from gamelib.config import load_settings
from gamelib.web.deps import Conn
from gamelib.web.templating import templates

router = APIRouter()

SETTINGS_FIELDS = [
    {"key": "steam_api_key", "label": "Steam API Key", "integration": "steam"},
    {"key": "steam_id64", "label": "Steam ID64", "integration": "steam"},
    {"key": "psn_npsso", "label": "PSN NPSSO", "integration": "psn"},
    {"key": "xbox_openxbl_key", "label": "Xbox OpenXBL Key", "integration": "xbox"},
]


def _current_fields(user_id: str) -> list[dict]:
    settings = load_settings(user_id)
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
    user = request.state.user
    return templates.TemplateResponse(
        request, "configuracoes.html", {"fields": _current_fields(user.id), "saved": False}
    )


@router.post("/configuracoes")
def configuracoes_submit(
    request: Request,
    conn: Conn,
    steam_api_key: str = Form(default=""),
    steam_id64: str = Form(default=""),
    psn_npsso: str = Form(default=""),
    xbox_openxbl_key: str = Form(default=""),
):
    user = request.state.user

    submitted = {
        "steam_api_key": steam_api_key,
        "steam_id64": steam_id64,
        "psn_npsso": psn_npsso,
        "xbox_openxbl_key": xbox_openxbl_key,
    }
    for key, raw_value in submitted.items():
        value = raw_value.strip()
        if value:
            settings_store.set_setting(
                key, value, user.id, encrypted=True, updated_by=user.email, client=conn
            )

    return templates.TemplateResponse(
        request, "configuracoes.html", {"fields": _current_fields(user.id), "saved": True}
    )


def _test_collector(collector, settings) -> tuple[bool, str]:
    if not collector.is_configured(settings):
        return False, "Credenciais ausentes."
    try:
        games = collector.fetch(settings)
    except CollectorError as exc:
        return False, str(exc)
    return True, f"Conexão OK — {len(games)} jogo(s) encontrado(s)."


_TESTERS = {
    "steam": lambda settings: _test_collector(SteamCollector(), settings),
    "psn": lambda settings: _test_collector(PsnCollector(), settings),
    "xbox": lambda settings: _test_collector(XboxCollector(), settings),
}


@router.post("/configuracoes/testar/{integration}")
def testar_conexao(request: Request, integration: str):
    settings = load_settings(request.state.user.id)
    tester = _TESTERS.get(integration)
    if tester is None:
        ok, message = False, "Integração desconhecida."
    else:
        ok, message = tester(settings)
    return templates.TemplateResponse(request, "_test_result.html", {"ok": ok, "message": message})
