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
    legendary_bin: str
    rawg_api_key: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    settings_encryption_key: str | None = None
    admin_email: str | None = None

    @property
    def steam_configured(self) -> bool:
        return bool(self.steam_api_key and self.steam_id64)

    @property
    def psn_configured(self) -> bool:
        return bool(self.psn_npsso)

    @property
    def xbox_configured(self) -> bool:
        return bool(self.xbox_openxbl_key)


def load_settings() -> Settings:
    _load_dotenv()

    # Bootstrap: precisam existir antes de qualquer leitura no banco ser
    # possível, então vêm direto do ambiente, nunca de `settings_store`.
    supabase_url = os.environ.get("SUPABASE_URL") or None
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY") or None
    supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or None
    settings_encryption_key = os.environ.get("SETTINGS_ENCRYPTION_KEY") or None
    admin_email = os.environ.get("ADMIN_EMAIL") or None

    return Settings(
        steam_api_key=settings_store.get_setting("steam_api_key", env_fallback="STEAM_API_KEY"),
        steam_id64=settings_store.get_setting("steam_id64", env_fallback="STEAM_ID64"),
        psn_npsso=settings_store.get_setting("psn_npsso", env_fallback="PSN_NPSSO"),
        xbox_openxbl_key=settings_store.get_setting(
            "xbox_openxbl_key", env_fallback="XBOX_OPENXBL_KEY"
        ),
        rawg_api_key=settings_store.get_setting("rawg_api_key", env_fallback="RAWG_API_KEY"),
        legendary_bin=os.environ.get("LEGENDARY_BIN", "legendary"),
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        supabase_service_role_key=supabase_service_role_key,
        settings_encryption_key=settings_encryption_key,
        admin_email=admin_email,
    )
