"""Modelo unificado de jogo. Campos sem dado disponível na plataforma ficam None."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

Platform = Literal["steam", "psn", "xbox", "epic", "nintendo"]
CompletionStatus = Literal["not_started", "playing", "completed", "abandoned", "unknown"]

PLATFORMS: tuple[Platform, ...] = ("steam", "psn", "xbox", "epic", "nintendo")
COMPLETION_STATUSES: tuple[CompletionStatus, ...] = (
    "not_started",
    "playing",
    "completed",
    "abandoned",
    "unknown",
)


@dataclass
class Game:
    """Representação unificada de um jogo possuído em alguma plataforma."""

    platform: Platform
    external_id: str
    name: str
    cover_url: str | None = None
    playtime_minutes: int | None = None
    last_played_at: datetime | None = None
    achievements_unlocked: int | None = None
    achievements_total: int | None = None
    completion_status: CompletionStatus = "unknown"
    added_at: date | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.platform not in PLATFORMS:
            raise ValueError(f"plataforma inválida: {self.platform!r}")
        if not self.external_id:
            raise ValueError("external_id não pode ser vazio")
        if not self.name:
            raise ValueError("name não pode ser vazio")
        if self.completion_status not in COMPLETION_STATUSES:
            raise ValueError(f"completion_status inválido: {self.completion_status!r}")
