"""Orquestração da sincronização: um coletor falhar não derruba os outros.

Circuit breaker por plataforma (`.claude/rules/python-data-rules.md`): cada
`fetch()` roda isolado, erro vira linha em `sync_runs` com a causa, e o loop
segue para a próxima plataforma. Log estruturado por etapa em vez de `print()`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from supabase import Client

from gamelib import db
from gamelib.collectors.base import Collector, CollectorError
from gamelib.config import Settings, load_settings
from gamelib.models import CompletionStatus, Game, Platform

log = logging.getLogger("gamelib.sync")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _collectors() -> dict[Platform, Collector]:
    # import tardio: evita puxar httpx/PSNAWP/subprocess pra quem só usa CSV/db.
    from gamelib.collectors.epic import EpicCollector
    from gamelib.collectors.psn import PsnCollector
    from gamelib.collectors.steam import SteamCollector
    from gamelib.collectors.xbox import XboxCollector

    return {
        "steam": SteamCollector(),
        "psn": PsnCollector(),
        "xbox": XboxCollector(),
        "epic": EpicCollector(),
    }


def _infer_completion_status(game: Game) -> CompletionStatus:
    """Nenhuma API de plataforma reporta status de conclusão — inferimos a
    partir de playtime/achievements. `nintendo` fica de fora: o CSV manual já
    traz o status escolhido pelo usuário, não deve ser sobrescrito.
    """
    if game.achievements_total and game.achievements_unlocked == game.achievements_total:
        return "completed"
    if game.playtime_minutes is None:
        return "unknown"
    if game.playtime_minutes == 0:
        return "not_started"
    return "playing"


@dataclass
class PlatformResult:
    platform: str
    status: str  # "success" | "failed" | "skipped"
    games_found: int | None = None
    error: str | None = None


@dataclass
class SyncReport:
    results: list[PlatformResult]

    @property
    def ok(self) -> bool:
        return all(r.status != "failed" for r in self.results)


def run_sync(
    user_id: str,
    platforms: list[Platform] | None = None,
    settings: Settings | None = None,
    collectors: dict[Platform, Collector] | None = None,
    client: Client | None = None,
) -> SyncReport:
    settings = settings or load_settings(user_id)
    conn = client if client is not None else db.connect(settings)
    collectors = collectors if collectors is not None else _collectors()
    targets = platforms or list(collectors)

    log.info("iniciando sync para %d plataforma(s): %s", len(targets), ", ".join(targets))
    results: list[PlatformResult] = []
    for i, platform in enumerate(targets, start=1):
        collector = collectors.get(platform)
        if collector is None:
            log.warning("[%d/%d] plataforma desconhecida: %s", i, len(targets), platform)
            results.append(PlatformResult(platform, "skipped", error="plataforma desconhecida"))
            continue

        if not collector.is_configured(settings):
            log.info("[%d/%d] %s sem credenciais configuradas — pulando", i, len(targets), platform)
            results.append(PlatformResult(platform, "skipped"))
            continue

        started = datetime.now(UTC)
        log.info("[%d/%d] > etapa: %s", i, len(targets), platform)
        try:
            games = collector.fetch(settings)
        except CollectorError as exc:
            finished = datetime.now(UTC)
            log.error("[%d/%d] %s falhou: %s", i, len(targets), platform, exc)
            db.record_sync_run(conn, user_id, platform, started, finished, "failed", None, str(exc))
            results.append(PlatformResult(platform, "failed", error=str(exc)))
            continue

        for game in games:
            if game.platform != "nintendo":
                game.completion_status = _infer_completion_status(game)
            db.upsert_game(conn, user_id, game)
        finished = datetime.now(UTC)
        log.info("[%d/%d] %s OK: %d jogo(s)", i, len(targets), platform, len(games))
        db.record_sync_run(conn, user_id, platform, started, finished, "success", len(games))
        results.append(PlatformResult(platform, "success", games_found=len(games)))

    log.info("sync concluído.")
    return SyncReport(results)
