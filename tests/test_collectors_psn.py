from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from gamelib.collectors.psn import PsnCollector
from gamelib.config import Settings

TrophySet = SimpleNamespace


def _settings() -> Settings:
    return Settings(
        steam_api_key=None,
        steam_id64=None,
        psn_npsso="NPSSO_TOKEN",
        xbox_openxbl_key=None,
        legendary_bin="legendary",
        database_path="/tmp/unused.db",  # type: ignore[arg-type]
    )


def test_psn_collector_mapeia_titulo_e_casa_trofeus_por_nome(monkeypatch):
    title = SimpleNamespace(
        title_id="NPWR12345",
        name="Bloodborne",
        image_url="https://example.com/bloodborne.jpg",
        play_duration=timedelta(hours=10),
        last_played_date_time=None,
        category="ps4_game",
    )
    trophy = SimpleNamespace(
        title_name="Bloodborne",
        earned_trophies=TrophySet(bronze=5, silver=2, gold=1, platinum=0),
        defined_trophies=TrophySet(bronze=10, silver=5, gold=2, platinum=1),
    )
    fake_client = SimpleNamespace(
        title_stats=lambda limit=None: [title],
        trophy_titles=lambda limit=None: [trophy],
    )

    class FakePSNAWP:
        def __init__(self, npsso_cookie: str) -> None:
            assert npsso_cookie == "NPSSO_TOKEN"

        def me(self):
            return fake_client

    monkeypatch.setattr("psnawp_api.PSNAWP", FakePSNAWP)

    games = PsnCollector().fetch(_settings())

    assert len(games) == 1
    game = games[0]
    assert game.name == "Bloodborne"
    assert game.playtime_minutes == 600
    assert game.achievements_unlocked == 8
    assert game.achievements_total == 18


def test_psn_collector_sem_correspondencia_de_trofeus_fica_sem_conquistas(monkeypatch):
    title = SimpleNamespace(
        title_id="NPWR999",
        name="Jogo Sem Troféus Mapeados",
        image_url=None,
        play_duration=None,
        last_played_date_time=None,
        category="ps5_native_game",
    )
    fake_client = SimpleNamespace(
        title_stats=lambda limit=None: [title],
        trophy_titles=lambda limit=None: [],
    )

    class FakePSNAWP:
        def __init__(self, npsso_cookie: str) -> None:
            pass

        def me(self):
            return fake_client

    monkeypatch.setattr("psnawp_api.PSNAWP", FakePSNAWP)

    games = PsnCollector().fetch(_settings())

    assert games[0].achievements_unlocked is None
    assert games[0].playtime_minutes is None
