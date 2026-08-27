"""Protocolo comum dos coletores + erro de fronteira (circuit breaker de `sync.py`).

Cada coletor sabe dizer se está configurado (credenciais presentes) e busca a
lista de `Game`s da sua plataforma. Falha de rede/parsing vira `CollectorError`
com a etapa/plataforma já contextualizada — quem decide parar ou seguir é
`sync.run_sync`, não o coletor.
"""

from __future__ import annotations

from typing import Protocol

from gamelib.config import Settings
from gamelib.models import Game


class CollectorError(RuntimeError):
    """Falha de coleta já contextualizada (plataforma + causa)."""


class Collector(Protocol):
    platform: str

    def is_configured(self, settings: Settings) -> bool: ...

    def fetch(self, settings: Settings) -> list[Game]: ...
