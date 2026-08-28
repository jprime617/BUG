"""Xbox via OpenXBL (xbl.io, não-oficial). Requer `XBOX_OPENXBL_KEY`.

Sem OAuth da Microsoft: o usuário gera a API key logando com a conta Xbox em
xbl.io e usa o header `X-Authorization`. Parsing defensivo (`.get()`) porque o
formato exato de resposta pode mudar entre versões da API — um campo ausente
vira `None` no `Game`, nunca uma exceção que aborta a plataforma inteira.

Playtime: `POST /player/stats` pedindo explicitamente o stat `MinutesPlayed`
por título (ver openapi.yaml oficial em github.com/OpenXBL/Docs) — o stat não
vem de graça em `GET /achievements/stats/{titleId}` (que devolve só o que a
Xbox Live já tem catalogado por padrão pra aquele jogo, nem sempre inclui
MinutesPlayed). Um único POST em lote pra todos os títulos, em vez de uma
chamada por jogo — também evita estourar o rate limit do tier grátis em
bibliotecas grandes.
"""

from __future__ import annotations

import logging

import httpx

from gamelib.collectors.base import CollectorError
from gamelib.config import Settings
from gamelib.models import Game

log = logging.getLogger("gamelib.collectors.xbox")

BASE_URL = "https://xbl.io/api/v2"


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
                content = resp.json().get("content") or {}
                titles = content.get("titles", [])
                playtime_by_title = self._fetch_playtime(client, content.get("xuid"), titles)
        except httpx.HTTPError as exc:
            raise CollectorError(f"xbox: falha de rede: {exc}") from exc

        games = []
        for entry in titles:
            game = self._to_game(entry, playtime_by_title)
            if game is not None:
                games.append(game)
        return games

    def _fetch_playtime(
        self, client: httpx.Client, xuid: str | None, titles: list[dict]
    ) -> dict[str, int]:
        title_ids = [str(t["titleId"]) for t in titles if t.get("titleId")]
        if not xuid or not title_ids:
            return {}

        body = {
            "xuids": [str(xuid)],
            "groups": [],
            "stats": [{"name": "MinutesPlayed", "titleId": title_id} for title_id in title_ids],
        }
        try:
            resp = client.post(f"{BASE_URL}/player/stats", json=body)
        except httpx.HTTPError as exc:
            log.warning("xbox: falha ao buscar playtime em lote (%s) — seguindo sem playtime", exc)
            return {}
        if resp.status_code != 200:
            log.warning(
                "xbox: player/stats retornou HTTP %d — seguindo sem playtime", resp.status_code
            )
            return {}

        playtime = self._extract_playtime_by_title(resp.json())
        if not playtime:
            log.info(
                "xbox: nenhum jogo reportou MinutesPlayed nesta sync (%d título(s) consultado(s))"
                " — nem todo jogo publica esse stat na Xbox Live",
                len(title_ids),
            )
        return playtime

    @staticmethod
    def _extract_playtime_by_title(payload: dict) -> dict[str, int]:
        playtime: dict[str, int] = {}
        for group in (payload.get("content") or {}).get("statlistscollection", []):
            for stat in group.get("stats", []):
                if stat.get("name") != "MinutesPlayed":
                    continue
                title_id = stat.get("titleid") or stat.get("titleId")
                value = stat.get("value")
                if title_id is None or value is None:
                    continue
                try:
                    playtime[str(title_id)] = int(value)
                except (TypeError, ValueError):
                    continue
        return playtime

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
