from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from gamelib.db import connect, upsert_game
from gamelib.models import Game
from gamelib.web.app import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("RAWG_API_KEY", "fake-key")
    return TestClient(app)


def _seed_game(tmp_path: Path) -> int:
    conn = connect(tmp_path / "test.db")
    upsert_game(conn, Game(platform="steam", external_id="1", name="Hades"))
    game_id = conn.execute("SELECT id FROM games").fetchone()["id"]
    conn.close()
    return game_id


def _patch_rawg(monkeypatch, search_results: list[dict]) -> None:
    real_client_cls = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/movies"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json={"results": search_results})

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def test_pagina_de_detalhe_renderiza_com_metadados(client, tmp_path, monkeypatch):
    game_id = _seed_game(tmp_path)
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
    )

    resp = client.get(f"/games/{game_id}")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<html" in resp.text
    assert "<title>Hades" in resp.text
    assert "setembro de 2020" in resp.text
    assert "Indie, Action" in resp.text


def test_pagina_de_detalhe_usa_cache_na_segunda_chamada(client, tmp_path, monkeypatch):
    game_id = _seed_game(tmp_path)
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if request.url.path.endswith("/movies"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(
            200,
            json={"results": [{"id": 1, "released": "2020-01-01", "genres": [], "rating": 3.0}]},
        )

    real_client_cls = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *a, **kw: real_client_cls(*a, **{**kw, "transport": httpx.MockTransport(handler)}),
    )

    first = client.get(f"/games/{game_id}")
    second = client.get(f"/games/{game_id}")

    assert first.status_code == second.status_code == 200
    assert call_count == 2  # busca (1 chamada de search) na 1a; nenhuma na 2a (cache)


def test_pagina_de_detalhe_jogo_inexistente_retorna_404(client):
    resp = client.get("/games/999")

    assert resp.status_code == 404
    assert "não encontrado" in resp.text.lower()


def test_pagina_de_detalhe_api_externa_fora_do_ar_mostra_erro_amigavel(
    client, tmp_path, monkeypatch
):
    game_id = _seed_game(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada", request=request)

    real_client_cls = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *a, **kw: real_client_cls(*a, **{**kw, "transport": httpx.MockTransport(handler)}),
    )

    resp = client.get(f"/games/{game_id}")

    assert resp.status_code == 200
    assert "hades" in resp.text.lower()
    assert "falha ao contatar" in resp.text.lower()


def test_pagina_de_detalhe_sem_rawg_api_key_mostra_erro_amigavel(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("RAWG_API_KEY", "")
    game_id = _seed_game(tmp_path)
    client = TestClient(app)

    resp = client.get(f"/games/{game_id}")

    assert resp.status_code == 200
    assert "rawg_api_key" in resp.text.lower()
