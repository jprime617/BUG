"""Formatação de exibição — mantida fora do modelo de domínio (`models.py`)
e da camada de dados (`db.py`) de propósito: é só sobre como mostrar o dado
na UI, não o que ele significa.
"""

from __future__ import annotations

from gamelib.models import CompletionStatus, Platform

PLATFORM_META: dict[Platform, dict[str, str]] = {
    "steam": {"label": "Steam", "color": "#6fa8c9"},
    "psn": {"label": "PlayStation", "color": "#8891e0"},
    "xbox": {"label": "Xbox", "color": "#6fbf7f"},
    "epic": {"label": "Epic Games", "color": "#b98ce8"},
    "nintendo": {"label": "Nintendo", "color": "#e2685a"},
}

STATUS_LABELS: dict[CompletionStatus, str] = {
    "not_started": "Não iniciado",
    "playing": "Jogando",
    "completed": "Concluído",
    "abandoned": "Abandonado",
    "unknown": "Desconhecido",
}


def format_playtime(minutes: int | None) -> str:
    """None = plataforma não reporta tempo jogado; 0 = possuído e nunca jogado."""
    if minutes is None:
        return "—"
    if minutes == 0:
        return "não jogado"
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h{mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}min"


def format_achievements(unlocked: int | None, total: int | None) -> str:
    if unlocked is None or total is None:
        return "sem dado"
    if total == 0:
        return "sem conquistas"
    return f"{unlocked}/{total}"
