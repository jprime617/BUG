"""PlayStation Network via PSNAWP (não-oficial, token `npsso`). Requer `PSN_NPSSO`.

`title_stats` só cobre PS4+ (limitação da própria API da Sony) e dá playtime/
last-played; `trophy_titles` dá o progresso de troféus mas usa `np_communication_id`
como chave, sem correspondência direta com o `title_id` de `title_stats`. Como
melhor-esforço, casamos os dois por nome do título (case-insensitive) — quando
não bate, o jogo fica sem dado de conquistas em vez de errar o valor.
"""

from __future__ import annotations

import logging

from gamelib.collectors.base import CollectorError
from gamelib.config import Settings
from gamelib.models import Game

log = logging.getLogger("gamelib.collectors.psn")


class PsnCollector:
    platform = "psn"

    def is_configured(self, settings: Settings) -> bool:
        return settings.psn_configured

    def fetch(self, settings: Settings) -> list[Game]:
        try:
            from psnawp_api import PSNAWP
            from psnawp_api.core.psnawp_exceptions import PSNAWPError
        except ImportError as exc:  # pragma: no cover - dependência sempre instalada em prod
            raise CollectorError("psn: pacote PSNAWP não instalado") from exc

        try:
            client = PSNAWP(npsso_cookie=settings.psn_npsso).me()
            titles = list(client.title_stats(limit=None))
            trophies_by_name = {
                (t.title_name or "").strip().lower(): t for t in client.trophy_titles(limit=None)
            }
        except PSNAWPError as exc:
            raise CollectorError(f"psn: falha de autenticação/API: {exc}") from exc

        return [self._to_game(title, trophies_by_name) for title in titles]

    def _to_game(self, title, trophies_by_name: dict) -> Game:
        trophy = trophies_by_name.get((title.name or "").strip().lower())
        unlocked = total = None
        if trophy is not None:
            unlocked = (
                trophy.earned_trophies.bronze
                + trophy.earned_trophies.silver
                + trophy.earned_trophies.gold
                + trophy.earned_trophies.platinum
            )
            total = (
                trophy.defined_trophies.bronze
                + trophy.defined_trophies.silver
                + trophy.defined_trophies.gold
                + trophy.defined_trophies.platinum
            )
        return Game(
            platform="psn",
            external_id=title.title_id or (title.name or "sem-id"),
            name=title.name or title.title_id or "Jogo PSN sem nome",
            cover_url=title.image_url,
            playtime_minutes=int(title.play_duration.total_seconds() // 60)
            if title.play_duration
            else None,
            last_played_at=title.last_played_date_time,
            achievements_unlocked=unlocked,
            achievements_total=total,
            raw={"title_id": title.title_id, "category": str(title.category)},
        )
