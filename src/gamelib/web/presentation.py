"""Formatação de exibição — mantida fora do modelo de domínio (`models.py`)
e da camada de dados (`db.py`) de propósito: é só sobre como mostrar o dado
na UI, não o que ele significa.
"""

from __future__ import annotations

from datetime import date

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


_MESES_PT = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip


def format_release_date(value: str | None) -> str:
    """RAWG retorna `released` como 'AAAA-MM-DD' ou None (data desconhecida)."""
    if not value:
        return "—"
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return value
    return f"{d.day} de {_MESES_PT[d.month - 1]} de {d.year}"


def format_rating_stars(rating: float | None) -> str:
    """RAWG usa escala 0–5. None = jogo sem avaliações suficientes na RAWG."""
    if rating is None:
        return "sem avaliação"
    full = max(0, min(5, round(rating)))
    return "★" * full + "☆" * (5 - full)
