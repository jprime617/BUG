"""Xbox via OpenXBL (xbl.io, não-oficial). Requer `XBOX_OPENXBL_KEY`.

Sem OAuth da Microsoft: o usuário gera a API key logando com a conta Xbox em
xbl.io e usa o header `X-Authorization`. Parsing defensivo (`.get()`) porque o
formato exato de resposta pode mudar entre versões da API — um campo ausente
vira `None` no `Game`, nunca uma exceção que aborta a plataforma inteira.
"""

from __future__ import annotations

import logging

import httpx

from gamelib.collectors.base import CollectorError
from gamelib.config import Settings
from gamelib.models import Game

log = logging.getLogger("gamelib.collectors.xbox")

BASE_URL = "https://xbl.io/api/v2"

# Tier grátis do OpenXBL: 150 requisições/hora. Playtime exige 1 requisição por
# jogo (não vem na lista); paramos antes de estourar pra não quebrar o resto da
# sync — o restante fica sem playtime nesta rodada e é completado numa próxima.
RATE_LIMIT_SAFETY_MARGIN = 5


class XboxCollector:
    platform = "xbox"

    def is_configured(self, settings: Settings) -> bool:
        return settings.xbox_configured

    def fetch(self, settings: Settings) -> list[Game]:
        headers = {"X-Authorization": settings.xbox_openxbl_key, "Accept": "application/json"}
        try:
            with httpx.Client(timeout=30, headers=headers) as client:
                resp = client.get(f"{BASE_URL}/player/titleHistory")
                if resp.status_code != 200:
                    raise CollectorError(f"xbox: titleHistory retornou HTTP {resp.status_code}")
                titles = (resp.json().get("content") or {}).get("titles", [])
                playtime_by_title = self._fetch_playtime(client, titles)
        except httpx.HTTPError as exc:
            raise CollectorError(f"xbox: falha de rede: {exc}") from exc

        games = []
        for entry in titles:
            game = self._to_game(entry, playtime_by_title)
            if game is not None:
                games.append(game)
        return games

    def _fetch_playtime(self, client: httpx.Client, titles: list[dict]) -> dict[str, int]:
        # Prioriza os jogados mais recentemente — são os mais relevantes e os
        # mais prováveis de ter playtime desatualizado.
        ordered = sorted(
            titles,
            key=lambda t: (t.get("titleHistory") or {}).get("lastTimePlayed") or "",
            reverse=True,
        )
        playtime: dict[str, int] = {}
        for entry in ordered:
            title_id = entry.get("titleId")
            if not title_id:
                continue

            resp = client.get(f"{BASE_URL}/achievements/stats/{title_id}")
            if resp.status_code == 200:
                minutes = self._extract_minutes_played(resp.json())
                if minutes is not None:
                    playtime[str(title_id)] = minutes
            else:
                log.debug("xbox: stats de %s retornou HTTP %d, pulando", title_id, resp.status_code)

            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining is not None and int(remaining) <= RATE_LIMIT_SAFETY_MARGIN:
                log.info(
                    "xbox: rate limit da API quase no fim — %d/%d jogo(s) sem playtime "
                    "nesta sync (completa nas próximas)",
                    len(titles) - len(playtime),
                    len(titles),
                )
                break
        return playtime

    @staticmethod
    def _extract_minutes_played(stats_payload: dict) -> int | None:
        for group in (stats_payload.get("content") or {}).get("statlistscollection", []):
            for stat in group.get("stats", []):
                if stat.get("name") == "MinutesPlayed" and stat.get("value") is not None:
                    try:
                        return int(stat["value"])
                    except (TypeError, ValueError):
                        return None
        return None

    def _to_game(self, entry: dict, playtime_by_title: dict[str, int]) -> Game | None:
        title_id = entry.get("titleId")
        name = entry.get("name")
        if not title_id or not name:
            log.debug("xbox: entrada sem titleId/name, pulando: %s", entry)
            return None

        achievement = entry.get("achievement") or {}
        return Game(
            platform="xbox",
            external_id=str(title_id),
            name=name,
            cover_url=(entry.get("displayImage") or None),
            last_played_at=None,  # openxbl não expõe timestamp estruturado consistente aqui
            achievements_unlocked=achievement.get("currentAchievements"),
            achievements_total=achievement.get("totalAchievements"),
            raw=entry,
            playtime_minutes=playtime_by_title.get(str(title_id)),
        )
