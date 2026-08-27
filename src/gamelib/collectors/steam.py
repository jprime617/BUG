"""Steam Web API (oficial). Requer `STEAM_API_KEY` + `STEAM_ID64`.

Docs: https://steamcommunity.com/dev — playtime e biblioteca vêm de
`IPlayerService/GetOwnedGames`; conquistas por jogo (melhor-esforço, já que
perfis privados/jogos sem stats retornam erro) de
`ISteamUserStats/GetPlayerAchievements`.
"""

from __future__ import annotations

import logging

import httpx

from gamelib.collectors.base import CollectorError
from gamelib.config import Settings
from gamelib.models import Game

log = logging.getLogger("gamelib.collectors.steam")

BASE_URL = "https://api.steampowered.com"
COVER_URL = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"


class SteamCollector:
    platform = "steam"

    def is_configured(self, settings: Settings) -> bool:
        return settings.steam_configured

    def fetch(self, settings: Settings) -> list[Game]:
        try:
            with httpx.Client(timeout=30) as client:
                owned = self._get_owned_games(client, settings)
                return [self._to_game(client, settings, entry) for entry in owned]
        except httpx.HTTPError as exc:
            raise CollectorError(f"steam: falha de rede: {exc}") from exc

    def _get_owned_games(self, client: httpx.Client, settings: Settings) -> list[dict]:
        resp = client.get(
            f"{BASE_URL}/IPlayerService/GetOwnedGames/v0001/",
            params={
                "key": settings.steam_api_key,
                "steamid": settings.steam_id64,
                "format": "json",
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
        )
        if resp.status_code != 200:
            raise CollectorError(f"steam: GetOwnedGames retornou HTTP {resp.status_code}")
        return resp.json().get("response", {}).get("games", [])

    def _get_achievements(
        self, client: httpx.Client, settings: Settings, appid: int
    ) -> tuple[int | None, int | None]:
        try:
            resp = client.get(
                f"{BASE_URL}/ISteamUserStats/GetPlayerAchievements/v0001/",
                params={
                    "key": settings.steam_api_key,
                    "steamid": settings.steam_id64,
                    "appid": appid,
                },
            )
            data = resp.json().get("playerstats", {})
            if not data.get("success"):
                return None, None
            achievements = data.get("achievements", [])
            unlocked = sum(1 for a in achievements if a.get("achieved") == 1)
            return unlocked, len(achievements)
        except (httpx.HTTPError, ValueError) as exc:
            log.debug("steam: sem conquistas para appid %s (%s)", appid, exc)
            return None, None

    def _to_game(self, client: httpx.Client, settings: Settings, entry: dict) -> Game:
        appid = entry["appid"]
        unlocked, total = self._get_achievements(client, settings, appid)
        return Game(
            platform="steam",
            external_id=str(appid),
            name=entry.get("name", f"App {appid}"),
            cover_url=COVER_URL.format(appid=appid),
            playtime_minutes=entry.get("playtime_forever"),
            achievements_unlocked=unlocked,
            achievements_total=total,
            raw=entry,
        )
