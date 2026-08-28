from __future__ import annotations

import json

import httpx
import pytest

from gamelib.collectors.base import CollectorError
from gamelib.collectors.xbox import XboxCollector
from gamelib.config import Settings


def _title_history(titles: list[dict], xuid: str = "1") -> dict:
    return {"content": {"xuid": xuid, "titles": titles}, "code": 0}


def _stats_response(minutes_by_title: dict[str, int]) -> dict:
    return {
        "content": {
            "statlistscollection": [
                {
                    "stats": [
                        {"name": "MinutesPlayed", "titleid": title_id, "value": str(minutes)}
                        for title_id, minutes in minutes_by_title.items()
                    ]
                }
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
    )


def _patch_client(monkeypatch, handler) -> None:
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def test_xbox_collector_mapeia_payload_e_busca_playtime_em_lote(monkeypatch):
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
    stats_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-authorization"] == "OPENXBL_KEY"
        if request.url.path == "/api/v2/player/titleHistory":
            return httpx.Response(200, json=_title_history(titles))
        assert request.url.path == "/api/v2/player/stats"
        stats_requests.append(request)
        return httpx.Response(200, json=_stats_response({"abc123": 300}))

    _patch_client(monkeypatch, handler)

    games = XboxCollector().fetch(_settings())

    assert len(games) == 1
    game = games[0]
    assert game.external_id == "abc123"
    assert game.name == "Forza Horizon 5"
    assert game.playtime_minutes == 300
    assert game.achievements_unlocked == 10
    assert game.achievements_total == 50

    assert len(stats_requests) == 1
    body = stats_requests[0].content

    payload = json.loads(body)
    assert payload["xuids"] == ["1"]
    assert payload["stats"] == [{"name": "MinutesPlayed", "titleId": "abc123"}]


def test_xbox_collector_sem_stat_minutesplayed_fica_sem_playtime(monkeypatch):
    titles = [{"titleId": "old1", "name": "Jogo antigo sem stat"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/player/titleHistory":
            return httpx.Response(200, json=_title_history(titles))
        return httpx.Response(200, json=_stats_response({}))

    _patch_client(monkeypatch, handler)

    games = XboxCollector().fetch(_settings())

    assert games[0].playtime_minutes is None


def test_xbox_collector_falha_ao_buscar_playtime_nao_derruba_a_sync(monkeypatch):
    titles = [{"titleId": "t1", "name": "Jogo 1"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/player/titleHistory":
            return httpx.Response(200, json=_title_history(titles))
        return httpx.Response(500)

    _patch_client(monkeypatch, handler)

    games = XboxCollector().fetch(_settings())

    assert len(games) == 1
    assert games[0].playtime_minutes is None


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
