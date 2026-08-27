from __future__ import annotations

import pytest

from gamelib.models import Game


def test_game_aceita_campos_minimos_e_usa_status_padrao():
    game = Game(platform="steam", external_id="10", name="Half-Life")

    assert game.completion_status == "unknown"
    assert game.playtime_minutes is None
    assert game.raw == {}


def test_game_rejeita_plataforma_invalida():
    with pytest.raises(ValueError, match="plataforma inválida"):
        Game(platform="bogus", external_id="10", name="Half-Life")  # type: ignore[arg-type]


def test_game_rejeita_nome_vazio():
    with pytest.raises(ValueError, match="name"):
        Game(platform="steam", external_id="10", name="")
