"""Factories de cliente Supabase. Dois clientes, dois propósitos:

- `service`: chave `service_role`, ignora RLS — usado pra todo I/O de jogos
  e configurações (o servidor é sempre o dono dos dados, nunca o browser).
- `anon`: chave pública, usada só pra `auth.*` (login/registro/reset) — é
  assim que o próprio Supabase espera que a autenticação seja feita.
"""

from __future__ import annotations

from supabase import Client, create_client

from gamelib.config import Settings


def get_service_client(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não configuradas — "
            "necessárias pra qualquer leitura/escrita de dados."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_anon_client(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError(
            "SUPABASE_URL/SUPABASE_ANON_KEY não configuradas — necessárias pra autenticação."
        )
    return create_client(settings.supabase_url, settings.supabase_anon_key)
