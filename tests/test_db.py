from __future__ import annotations

from gamelib import db
from gamelib.models import Game


def test_upsert_game_e_idempotente_por_plataforma_e_external_id(db_conn):
    game = Game(platform="steam", external_id="10", name="Half-Life", playtime_minutes=60)

    db.upsert_game(db_conn, game)
    db.upsert_game(
        db_conn, Game(platform="steam", external_id="10", name="Half-Life", playtime_minutes=90)
    )

    rows = db.list_games(db_conn)
    assert len(rows) == 1
    assert rows[0]["playtime_minutes"] == 90


def test_list_games_filtra_por_plataforma_e_busca(db_conn):
    db.upsert_game(db_conn, Game(platform="steam", external_id="1", name="Portal"))
    db.upsert_game(db_conn, Game(platform="psn", external_id="2", name="Bloodborne"))

    assert [r["name"] for r in db.list_games(db_conn, platform="psn")] == ["Bloodborne"]
    assert [r["name"] for r in db.list_games(db_conn, query="port")] == ["Portal"]


def test_get_stats_agrega_totais_por_plataforma_e_status(db_conn):
    db.upsert_game(
        db_conn,
        Game(
            platform="steam",
            external_id="1",
            name="Portal",
            playtime_minutes=100,
            completion_status="completed",
        ),
    )
    db.upsert_game(
        db_conn,
        Game(
            platform="psn",
            external_id="2",
            name="Bloodborne",
            playtime_minutes=50,
            completion_status="playing",
        ),
    )

    stats = db.get_stats(db_conn)

    assert stats["total_games"] == 2
    assert stats["total_playtime_minutes"] == 150
    assert stats["by_platform"] == {"steam": 1, "psn": 1}
    assert stats["by_status"] == {"completed": 1, "playing": 1}
