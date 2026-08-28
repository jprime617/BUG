from __future__ import annotations

from gamelib import db
from gamelib.models import Game

USER_A = "user-a"
USER_B = "user-b"


def test_upsert_game_e_idempotente_por_usuario_plataforma_e_external_id(db_conn):
    game = Game(platform="steam", external_id="10", name="Half-Life", playtime_minutes=60)

    db.upsert_game(db_conn, USER_A, game)
    db.upsert_game(
        db_conn,
        USER_A,
        Game(platform="steam", external_id="10", name="Half-Life", playtime_minutes=90),
    )

    rows = db.list_games(db_conn, USER_A)
    assert len(rows) == 1
    assert rows[0]["playtime_minutes"] == 90


def test_list_games_filtra_por_plataforma_e_busca(db_conn):
    db.upsert_game(db_conn, USER_A, Game(platform="steam", external_id="1", name="Portal"))
    db.upsert_game(db_conn, USER_A, Game(platform="psn", external_id="2", name="Bloodborne"))

    assert [r["name"] for r in db.list_games(db_conn, USER_A, platform="psn")] == ["Bloodborne"]
    assert [r["name"] for r in db.list_games(db_conn, USER_A, query="port")] == ["Portal"]


def test_list_games_nao_ve_jogos_de_outro_usuario(db_conn):
    db.upsert_game(db_conn, USER_A, Game(platform="steam", external_id="1", name="Portal"))
    db.upsert_game(db_conn, USER_B, Game(platform="steam", external_id="2", name="Bloodborne"))

    assert [r["name"] for r in db.list_games(db_conn, USER_A)] == ["Portal"]
    assert [r["name"] for r in db.list_games(db_conn, USER_B)] == ["Bloodborne"]


def test_get_game_nao_acha_jogo_de_outro_usuario(db_conn):
    db.upsert_game(db_conn, USER_A, Game(platform="steam", external_id="1", name="Portal"))
    game_id = db.list_games(db_conn, USER_A)[0]["id"]

    assert db.get_game(db_conn, USER_A, game_id) is not None
    assert db.get_game(db_conn, USER_B, game_id) is None


def test_get_stats_agrega_totais_por_plataforma_e_status(db_conn):
    db.upsert_game(
        db_conn,
        USER_A,
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
        USER_A,
        Game(
            platform="psn",
            external_id="2",
            name="Bloodborne",
            playtime_minutes=50,
            completion_status="playing",
        ),
    )

    stats = db.get_stats(db_conn, USER_A)

    assert stats["total_games"] == 2
    assert stats["total_playtime_minutes"] == 150
    assert stats["by_platform"] == {"steam": 1, "psn": 1}
    assert stats["by_status"] == {"completed": 1, "playing": 1}


def test_get_stats_nao_inclui_jogos_de_outro_usuario(db_conn):
    db.upsert_game(db_conn, USER_A, Game(platform="steam", external_id="1", name="Portal"))
    db.upsert_game(db_conn, USER_B, Game(platform="steam", external_id="2", name="Bloodborne"))

    assert db.get_stats(db_conn, USER_A)["total_games"] == 1
