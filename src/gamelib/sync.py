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
    # import tardio: evita puxar httpx/PSNAWP pra quem só usa db.
    from gamelib.collectors.psn import PsnCollector
    from gamelib.collectors.steam import SteamCollector
    from gamelib.collectors.xbox import XboxCollector

    return {
        "steam": SteamCollector(),
        "psn": PsnCollector(),
        "xbox": XboxCollector(),
    }


def _infer_completion_status(game: Game) -> CompletionStatus:
    """Nenhuma API de plataforma reporta status de conclusão — inferimos a
    partir de playtime/achievements.
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


@dataclass
class SyncEvent:
    """Evento de progresso emitido por `run_sync_iter` — consumido tanto
    pelo wrapper síncrono `run_sync` quanto pelo endpoint de streaming SSE
    (`GET /sync/stream` em `web/app.py`).
    """

    type: str  # "targets" | "platform_done"
    targets: list[str] | None = None
    platform: str | None = None
    index: int | None = None
    total: int | None = None
    result: PlatformResult | None = None


def run_sync_iter(
    user_id: str,
    platforms: list[Platform] | None = None,
    settings: Settings | None = None,
    collectors: dict[Platform, Collector] | None = None,
    client: Client | None = None,
):
    """Mesmo trabalho de `run_sync`, mas em forma de gerador: `yield`a um
    `SyncEvent` por plataforma concluída (mais um evento inicial com a
    lista de alvos), pra permitir progresso incremental via streaming.
    Execução é sempre sequencial (sem paralelismo), então quem consome sabe
    que a plataforma "atual" é sempre `targets[<qtd. de eventos recebidos>]`.
    """
    settings = settings or load_settings(user_id)
    conn = client if client is not None else db.connect(settings)
    collectors = collectors if collectors is not None else _collectors()
    targets = platforms or list(collectors)

    log.info("iniciando sync para %d plataforma(s): %s", len(targets), ", ".join(targets))
    yield SyncEvent("targets", targets=list(targets))

    total = len(targets)
    for i, platform in enumerate(targets, start=1):
        collector = collectors.get(platform)
        if collector is None:
            log.warning("[%d/%d] plataforma desconhecida: %s", i, total, platform)
            result = PlatformResult(platform, "skipped", error="plataforma desconhecida")
            yield SyncEvent("platform_done", platform=platform, index=i, total=total, result=result)
            continue

        if not collector.is_configured(settings):
            log.info("[%d/%d] %s sem credenciais configuradas — pulando", i, total, platform)
            result = PlatformResult(platform, "skipped")
            yield SyncEvent("platform_done", platform=platform, index=i, total=total, result=result)
            continue

        started = datetime.now(UTC)
        log.info("[%d/%d] > etapa: %s", i, total, platform)
        try:
            games = collector.fetch(settings)
        except CollectorError as exc:
            finished = datetime.now(UTC)
            log.error("[%d/%d] %s falhou: %s", i, total, platform, exc)
            db.record_sync_run(conn, user_id, platform, started, finished, "failed", None, str(exc))
            result = PlatformResult(platform, "failed", error=str(exc))
            yield SyncEvent("platform_done", platform=platform, index=i, total=total, result=result)
            continue

        for game in games:
            game.completion_status = _infer_completion_status(game)
            db.upsert_game(conn, user_id, game)
        finished = datetime.now(UTC)
        log.info("[%d/%d] %s OK: %d jogo(s)", i, total, platform, len(games))
        db.record_sync_run(conn, user_id, platform, started, finished, "success", len(games))
        result = PlatformResult(platform, "success", games_found=len(games))
        yield SyncEvent("platform_done", platform=platform, index=i, total=total, result=result)

    log.info("sync concluído.")


def run_sync(
    user_id: str,
    platforms: list[Platform] | None = None,
    settings: Settings | None = None,
    collectors: dict[Platform, Collector] | None = None,
    client: Client | None = None,
) -> SyncReport:
    results = [
        event.result
        for event in run_sync_iter(user_id, platforms, settings, collectors, client)
        if event.type == "platform_done"
    ]
    return SyncReport(results)
