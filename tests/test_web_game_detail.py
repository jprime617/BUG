from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from tests.fakes import FakeSupabaseClient

from gamelib.db import list_games, upsert_game
from gamelib.models import Game
from gamelib.web.app import app
from gamelib.web.deps import get_conn

_FAKE_USER = SimpleNamespace(id="user-a", email="a@example.com")
_OTHER_USER = SimpleNamespace(id="user-b", email="b@example.com")


@pytest.fixture
def fake_client() -> FakeSupabaseClient:
    return FakeSupabaseClient()


@pytest.fixture
def client(fake_client: FakeSupabaseClient, monkeypatch) -> TestClient:
    # Estas rotas exigem sessão (middleware de auth) — este arquivo testa
    # renderização de detalhe de jogo, não autenticação, então simula um
    # usuário já logado direto no middleware (não passa por Depends).
    monkeypatch.setenv("RAWG_API_KEY", "fake-key")
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: _FAKE_USER)
    app.dependency_overrides[get_conn] = lambda: fake_client
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_game(fake_client: FakeSupabaseClient, user_id: str = _FAKE_USER.id) -> int:
    upsert_game(fake_client, user_id, Game(platform="steam", external_id="1", name="Hades"))
    return list_games(fake_client, user_id)[0]["id"]


def _patch_rawg(
    monkeypatch, search_results: list[dict], detail_by_id: dict[int, dict] | None = None
) -> None:
    detail_by_id = detail_by_id or {}
    real_client_cls = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        tail = request.url.path.rsplit("/", 1)[-1]
        if tail.isdigit():
            return httpx.Response(200, json=detail_by_id.get(int(tail), {}))
        return httpx.Response(200, json={"results": search_results})

    def fake_httpx_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_httpx_client)


def test_pagina_de_detalhe_renderiza_com_metadados(client, fake_client, monkeypatch):
    game_id = _seed_game(fake_client)
    _patch_rawg(
        monkeypatch,
        search_results=[
            {
                "id": 42,
                "released": "2020-09-17",
                "genres": [{"name": "Indie"}, {"name": "Action"}],
                "rating": 4.5,
                "metacritic": 93,
            }
        ],
        detail_by_id={42: {"description_raw": "Uma jornada pelo submundo."}},
    )

    resp = client.get(f"/games/{game_id}")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<html" in resp.text
    assert "<title>Hades" in resp.text
    assert "setembro de 2020" in resp.text
    assert "Indie, Action" in resp.text
    assert "93" in resp.text
    assert "Uma jornada pelo submundo." in resp.text


def test_pagina_de_detalhe_usa_cache_na_segunda_chamada(client, fake_client, monkeypatch):
    game_id = _seed_game(fake_client)
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        tail = request.url.path.rsplit("/", 1)[-1]
        if tail.isdigit():
            return httpx.Response(200, json={"description_raw": "Sinopse."})
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
    assert call_count == 2  # busca + detalhe na 1a; nenhuma na 2a (cache)


def test_pagina_de_detalhe_jogo_inexistente_retorna_404(client):
    resp = client.get("/games/999")

    assert resp.status_code == 404
    assert "não encontrado" in resp.text.lower()


def test_pagina_de_detalhe_jogo_de_outro_usuario_retorna_404(client, fake_client):
    game_id = _seed_game(fake_client, user_id=_OTHER_USER.id)

    resp = client.get(f"/games/{game_id}")

    assert resp.status_code == 404
    assert "não encontrado" in resp.text.lower()


def test_pagina_de_detalhe_api_externa_fora_do_ar_mostra_erro_amigavel(
    client, fake_client, monkeypatch
):
    game_id = _seed_game(fake_client)

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


def test_pagina_de_detalhe_sem_rawg_api_key_mostra_erro_amigavel(fake_client, monkeypatch):
    monkeypatch.setenv("RAWG_API_KEY", "")
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: _FAKE_USER)
    game_id = _seed_game(fake_client)
    app.dependency_overrides[get_conn] = lambda: fake_client
    client = TestClient(app)

    try:
        resp = client.get(f"/games/{game_id}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "rawg_api_key" in resp.text.lower()
