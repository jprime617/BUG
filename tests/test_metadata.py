from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from gamelib import db
from gamelib.metadata import MetadataError, get_or_fetch_metadata
from gamelib.models import Game

RAWG_KEY = "fake-key"


def _patch_client(monkeypatch, handler) -> None:
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def _patch_rawg(
    monkeypatch, search_results: list[dict], movies_by_id: dict[int, list[dict]] | None = None
):
    movies_by_id = movies_by_id or {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/movies"):
            game_id = int(request.url.path.split("/")[-2])
            return httpx.Response(200, json={"results": movies_by_id.get(game_id, [])})
        return httpx.Response(200, json={"results": search_results})

    _patch_client(monkeypatch, handler)


def test_busca_e_persiste_metadados_na_primeira_chamada(monkeypatch, db_conn):
    db.upsert_game(db_conn, Game(platform="steam", external_id="1", name="Hades"))
    game_id = db_conn.execute("SELECT id FROM games").fetchone()["id"]

    _patch_rawg(
        monkeypatch,
        search_results=[
            {
                "id": 42,
                "released": "2020-09-17",
                "genres": [{"name": "Indie"}, {"name": "Action"}],
                "rating": 4.5,
            }
        ],
        movies_by_id={42: [{"data": {"max": "https://example.com/trailer.mp4"}}]},
    )

    metadata = get_or_fetch_metadata(db_conn, game_id, "Hades", RAWG_KEY)

    assert metadata.release_date == "2020-09-17"
    assert metadata.genres == ["Indie", "Action"]
    assert metadata.rating == 4.5
    assert metadata.video_url == "https://example.com/trailer.mp4"

    row = db.get_game_metadata(db_conn, game_id)
    assert row is not None
    assert row["release_date"] == "2020-09-17"


def test_segunda_chamada_usa_cache_sem_bater_na_api(monkeypatch, db_conn):
    game_id = 1
    db.upsert_game_metadata(
        db_conn, game_id, release_date="2019-01-01", genres=["RPG"], rating=4.0, video_url=None
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria bater na API externa com cache fresco")

    _patch_client(monkeypatch, handler)

    metadata = get_or_fetch_metadata(db_conn, game_id, "Qualquer Jogo", RAWG_KEY)

    assert metadata.release_date == "2019-01-01"
    assert metadata.genres == ["RPG"]


def test_cache_expirado_busca_de_novo(monkeypatch, db_conn):
    game_id = 1
    db.upsert_game_metadata(
        db_conn, game_id, release_date="2019-01-01", genres=["RPG"], rating=4.0, video_url=None
    )
    old = (datetime.now(UTC) - timedelta(days=31)).isoformat()
    db_conn.execute("UPDATE game_metadata SET fetched_at = ? WHERE game_id = ?", (old, game_id))
    db_conn.commit()

    _patch_rawg(
        monkeypatch,
        search_results=[{"id": 99, "released": "2024-05-01", "genres": [], "rating": 3.0}],
    )

    metadata = get_or_fetch_metadata(db_conn, game_id, "Qualquer Jogo", RAWG_KEY)

    assert metadata.release_date == "2024-05-01"


def test_sem_chave_rawg_levanta_metadata_error(db_conn):
    with pytest.raises(MetadataError, match="RAWG_API_KEY"):
        get_or_fetch_metadata(db_conn, 1, "Hades", None)


def test_api_externa_fora_do_ar_levanta_metadata_error(monkeypatch, db_conn):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada", request=request)

    _patch_client(monkeypatch, handler)

    with pytest.raises(MetadataError, match="falha ao contatar"):
        get_or_fetch_metadata(db_conn, 1, "Hades", RAWG_KEY)


def test_jogo_nao_encontrado_na_rawg_levanta_metadata_error(monkeypatch, db_conn):
    _patch_rawg(monkeypatch, search_results=[])

    with pytest.raises(MetadataError, match="não encontrado"):
        get_or_fetch_metadata(db_conn, 1, "Jogo Inexistente XYZ", RAWG_KEY)
