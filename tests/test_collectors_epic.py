from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from gamelib.collectors.base import CollectorError
from gamelib.collectors.epic import EpicCollector
from gamelib.config import Settings

LEGENDARY_LIST_OUTPUT = [
    {
        "app_name": "portal2",
        "app_title": "Portal 2",
        "metadata": {
            "categories": [{"path": "applications"}, {"path": "games"}],
            "keyImages": [
                {"type": "DieselGameBox", "url": "https://cdn.epicgames.com/box.png"},
                {"type": "DieselGameBoxTall", "url": "https://cdn.epicgames.com/tall.png"},
            ],
        },
    },
    {
        "app_name": "sem_titulo",
        "metadata": {"categories": [{"path": "applications"}, {"path": "games"}]},
    },
    {
        "app_name": "asset_marketplace",
        "app_title": "Crowd Simulation System Pro",
        "metadata": {"categories": [{"path": "plugins"}, {"path": "asset-format"}]},
    },
]


def _settings() -> Settings:
    return Settings(
        steam_api_key=None,
        steam_id64=None,
        psn_npsso=None,
        xbox_openxbl_key=None,
        legendary_bin="legendary",
        database_path="/tmp/unused.db",  # type: ignore[arg-type]
    )


def test_epic_collector_mapeia_saida_json_do_legendary(monkeypatch):
    fake_result = MagicMock(returncode=0, stdout=json.dumps(LEGENDARY_LIST_OUTPUT), stderr="")
    monkeypatch.setattr("gamelib.collectors.epic.subprocess.run", lambda *a, **k: fake_result)

    games = EpicCollector().fetch(_settings())

    assert [g.name for g in games] == ["Portal 2", "sem_titulo"]
    assert games[0].external_id == "portal2"
    assert games[0].cover_url == "https://cdn.epicgames.com/tall.png"
    assert games[1].cover_url is None


def test_epic_collector_ignora_itens_sem_categoria_games(monkeypatch):
    entries = [e for e in LEGENDARY_LIST_OUTPUT if e["app_name"] == "asset_marketplace"]
    fake_result = MagicMock(returncode=0, stdout=json.dumps(entries), stderr="")
    monkeypatch.setattr("gamelib.collectors.epic.subprocess.run", lambda *a, **k: fake_result)

    games = EpicCollector().fetch(_settings())

    assert games == []


def test_epic_collector_levanta_collector_error_se_binario_falha(monkeypatch):
    fake_result = MagicMock(returncode=1, stdout="", stderr="auth expirada")
    monkeypatch.setattr("gamelib.collectors.epic.subprocess.run", lambda *a, **k: fake_result)

    with pytest.raises(CollectorError, match="auth expirada"):
        EpicCollector().fetch(_settings())
