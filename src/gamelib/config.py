"""Configuração via variáveis de ambiente + configurações dinâmicas no
Supabase. Credenciais nunca em código (ver env.example).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from gamelib import settings_store

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    steam_api_key: str | None
    steam_id64: str | None
    psn_npsso: str | None
    xbox_openxbl_key: str | None
    rawg_api_key: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    settings_encryption_key: str | None = None

    @property
    def steam_configured(self) -> bool:
        return bool(self.steam_api_key and self.steam_id64)

    @property
    def psn_configured(self) -> bool:
        return bool(self.psn_npsso)

    @property
    def xbox_configured(self) -> bool:
        return bool(self.xbox_openxbl_key)


def load_settings(user_id: str | None = None) -> Settings:
    """Carrega config. `user_id` escopa as credenciais de plataforma
    (Steam/PSN/Xbox), que são pessoais — sem usuário (bootstrap, antes do
    login) esses campos ficam `None`. `RAWG_API_KEY` é a única credencial
    ainda global (metadado público de jogos, não uma conta pessoal), vinda
    só de `os.environ`.
    """
    _load_dotenv()

    # Bootstrap: precisam existir antes de qualquer leitura no banco ser
    # possível, então vêm direto do ambiente, nunca de `settings_store`.
    supabase_url = os.environ.get("SUPABASE_URL") or None
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY") or None
    supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or None
    settings_encryption_key = os.environ.get("SETTINGS_ENCRYPTION_KEY") or None

    if user_id is not None:
        steam_api_key = settings_store.get_setting("steam_api_key", user_id)
        steam_id64 = settings_store.get_setting("steam_id64", user_id)
        psn_npsso = settings_store.get_setting("psn_npsso", user_id)
        xbox_openxbl_key = settings_store.get_setting("xbox_openxbl_key", user_id)
    else:
        steam_api_key = steam_id64 = psn_npsso = xbox_openxbl_key = None

    return Settings(
        steam_api_key=steam_api_key,
        steam_id64=steam_id64,
        psn_npsso=psn_npsso,
        xbox_openxbl_key=xbox_openxbl_key,
        rawg_api_key=os.environ.get("RAWG_API_KEY") or None,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        supabase_service_role_key=supabase_service_role_key,
        settings_encryption_key=settings_encryption_key,
    )
