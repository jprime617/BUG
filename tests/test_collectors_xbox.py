from __future__ import annotations

import httpx
import pytest

from gamelib.collectors.base import CollectorError
from gamelib.collectors.xbox import XboxCollector
from gamelib.config import Settings


def _title_history(titles: list[dict]) -> dict:
    return {"content": {"xuid": "1", "titles": titles}, "code": 0}


def _stats_response(minutes: int | None) -> dict:
    if minutes is None:
        return {"content": {"statlistscollection": []}, "code": 0}
    return {
        "content": {
            "statlistscollection": [
                {"stats": [{"name": "MinutesPlayed", "type": "Integer", "value": str(minutes)}]}
            ]
        },
        "code": 0,
    }


def _settings() -> Settings:
    return Settings(
        steam_api_key=None,
        steam_id64=None,
        psn_npsso=None,
        xbox_openxbl_key="OPENXBL_KEY",
        legendary_bin="legendary",
        database_path="/tmp/unused.db",  # type: ignore[arg-type]
    )


def _patch_client(monkeypatch, handler) -> None:
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def test_xbox_collector_mapeia_payload_e_busca_playtime_por_titulo(monkeypatch):
    titles = [
        {
            "titleId": "abc123",
            "name": "Forza Horizon 5",
            "displayImage": "https://example.com/cover.jpg",
            "titleHistory": {"lastTimePlayed": "2026-01-01T00:00:00Z"},
            "achievement": {"currentAchievements": 10, "totalAchievements": 50},
        },
        {"name": "sem titleId, deve ser ignorado"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-authorization"] == "OPENXBL_KEY"
        if request.url.path == "/api/v2/player/titleHistory":
            return httpx.Response(200, json=_title_history(titles))
        assert request.url.path == "/api/v2/achievements/stats/abc123"
        return httpx.Response(200, json=_stats_response(300))

    _patch_client(monkeypatch, handler)

    games = XboxCollector().fetch(_settings())

    assert len(games) == 1
    game = games[0]
    assert game.external_id == "abc123"
    assert game.name == "Forza Horizon 5"
    assert game.playtime_minutes == 300
    assert game.achievements_unlocked == 10
    assert game.achievements_total == 50


def test_xbox_collector_sem_stat_minutesplayed_fica_sem_playtime(monkeypatch):
    titles = [{"titleId": "old1", "name": "Jogo antigo sem stat"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/player/titleHistory":
            return httpx.Response(200, json=_title_history(titles))
        return httpx.Response(200, json=_stats_response(None))

    _patch_client(monkeypatch, handler)

    games = XboxCollector().fetch(_settings())

    assert games[0].playtime_minutes is None


def test_xbox_collector_para_de_buscar_playtime_quando_rate_limit_acaba(monkeypatch):
    titles = [{"titleId": f"t{i}", "name": f"Jogo {i}"} for i in range(3)]
    stats_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/player/titleHistory":
            return httpx.Response(200, json=_title_history(titles))
        title_id = request.url.path.rsplit("/", 1)[-1]
        stats_calls.append(title_id)
        # já no limite de seguranca a partir da primeira chamada de stats
        return httpx.Response(
            200, json=_stats_response(100), headers={"x-ratelimit-remaining": "1"}
        )

    _patch_client(monkeypatch, handler)

    games = XboxCollector().fetch(_settings())

    assert len(stats_calls) == 1
    playtimes = {g.external_id: g.playtime_minutes for g in games}
    known = [pt for pt in playtimes.values() if pt is not None]
    assert len(known) == 1
    assert sum(1 for pt in playtimes.values() if pt is None) == 2


def test_xbox_collector_retorna_vazio_se_resposta_sem_content(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0})

    _patch_client(monkeypatch, handler)

    assert XboxCollector().fetch(_settings()) == []


def test_xbox_collector_levanta_collector_error_em_http_nao_200(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    _patch_client(monkeypatch, handler)

    with pytest.raises(CollectorError, match="401"):
        XboxCollector().fetch(_settings())
