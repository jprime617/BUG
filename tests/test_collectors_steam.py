from __future__ import annotations

import httpx

from gamelib.collectors.steam import SteamCollector
from gamelib.config import Settings

OWNED_GAMES_RESPONSE = {
    "response": {
        "games": [
            {"appid": 400, "name": "Portal", "playtime_forever": 120},
        ]
    }
}
ACHIEVEMENTS_RESPONSE = {
    "playerstats": {
        "success": True,
        "achievements": [{"achieved": 1}, {"achieved": 0}],
    }
}


def _settings() -> Settings:
    return Settings(
        steam_api_key="KEY",
        steam_id64="123",
        psn_npsso=None,
        xbox_openxbl_key=None,
        legendary_bin="legendary",
    )


def _handler(request: httpx.Request) -> httpx.Response:
    if "GetOwnedGames" in request.url.path:
        return httpx.Response(200, json=OWNED_GAMES_RESPONSE)
    if "GetPlayerAchievements" in request.url.path:
        return httpx.Response(200, json=ACHIEVEMENTS_RESPONSE)
    raise AssertionError(f"URL inesperada: {request.url}")


def test_steam_collector_mapeia_payload_para_game(monkeypatch):
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        return real_client_cls(transport=httpx.MockTransport(_handler))

    monkeypatch.setattr(httpx, "Client", fake_client)

    games = SteamCollector().fetch(_settings())

    assert len(games) == 1
    game = games[0]
    assert game.platform == "steam"
    assert game.external_id == "400"
    assert game.name == "Portal"
    assert game.playtime_minutes == 120
    assert game.achievements_unlocked == 1
    assert game.achievements_total == 2
    assert game.cover_url == "https://cdn.cloudflare.steamstatic.com/steam/apps/400/header.jpg"
