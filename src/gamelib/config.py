"""Configuração via variáveis de ambiente. Credenciais nunca em código (ver env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
    database_path: Path
    rawg_api_key: str | None = None

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
    db_path = os.environ.get("DATABASE_PATH", "data/games.db")
    return Settings(
        steam_api_key=os.environ.get("STEAM_API_KEY") or None,
        steam_id64=os.environ.get("STEAM_ID64") or None,
        psn_npsso=os.environ.get("PSN_NPSSO") or None,
        xbox_openxbl_key=os.environ.get("XBOX_OPENXBL_KEY") or None,
        legendary_bin=os.environ.get("LEGENDARY_BIN", "legendary"),
        database_path=(ROOT / db_path) if not Path(db_path).is_absolute() else Path(db_path),
        rawg_api_key=os.environ.get("RAWG_API_KEY") or None,
    )
