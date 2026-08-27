"""Configurações dinâmicas — substitui parte do `.env` (chaves de API de
terceiros). Leitura: banco primeiro, `.env` como fallback; nenhum dos dois
configurado devolve `None` (quem chama decide como sinalizar na UI).

Lê `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`/`SETTINGS_ENCRYPTION_KEY`
direto de `os.environ` (não via `gamelib.config.load_settings()`) porque
`config.py` chama `get_setting` — importar `config` aqui criaria ciclo.

Sem cache em memória: cada invocação serverless na Vercel já é um cold
start, não há problema de invalidação de cache de longa duração a resolver.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from supabase import Client, create_client


def _default_client() -> Client | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def _fernet() -> Fernet:
    key = os.environ.get("SETTINGS_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "SETTINGS_ENCRYPTION_KEY não configurada — necessária pra ler/gravar "
            "configurações cifradas."
        )
    return Fernet(key.encode())


def get_setting(
    key: str,
    *,
    env_fallback: str | None = None,
    client: Client | None = None,
) -> str | None:
    resolved_client = client if client is not None else _default_client()
    if resolved_client is not None:
        row = (
            resolved_client.table("settings")
            .select("value, encrypted")
            .eq("key", key)
            .maybe_single()
            .execute()
            .data
        )
        if row is not None and row.get("value") is not None:
            if row["encrypted"]:
                try:
                    return _fernet().decrypt(row["value"].encode()).decode()
                except InvalidToken as exc:
                    raise RuntimeError(
                        f"não foi possível descriptografar a configuração {key!r} "
                        "— SETTINGS_ENCRYPTION_KEY errada?"
                    ) from exc
            return row["value"]
    if env_fallback:
        return os.environ.get(env_fallback) or None
    return None


def set_setting(
    key: str,
    value: str,
    *,
    encrypted: bool = False,
    updated_by: str | None = None,
    client: Client,
) -> None:
    stored = _fernet().encrypt(value.encode()).decode() if encrypted else value
    client.table("settings").upsert(
        {
            "key": key,
            "value": stored,
            "encrypted": encrypted,
            "updated_by": updated_by,
            "updated_at": datetime.now(UTC).isoformat(),
        },
        on_conflict="key",
    ).execute()


def mask(value: str) -> str:
    """Só os últimos 4 caracteres visíveis — pra exibir em /configuracoes."""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]
