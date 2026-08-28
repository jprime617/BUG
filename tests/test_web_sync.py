from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from tests.fakes import FakeSupabaseClient

from gamelib.web.app import app
from gamelib.web.deps import get_conn

USER_A = SimpleNamespace(id="user-a", email="a@example.com")
USER_B = SimpleNamespace(id="user-b", email="b@example.com")


@pytest.fixture
def fake_client() -> FakeSupabaseClient:
    return FakeSupabaseClient()


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _client(fake_client, monkeypatch, user) -> TestClient:
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: user)
    app.dependency_overrides[get_conn] = lambda: fake_client
    return TestClient(app)


def test_sync_usuario_anonimo_redireciona_para_login(fake_client, monkeypatch):
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: None)
    app.dependency_overrides[get_conn] = lambda: fake_client
    client = TestClient(app)

    resp = client.post("/sync", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_sync_usuario_logado_roda_run_sync_escopado_ao_proprio_id(fake_client, monkeypatch):
    called_with = {}

    def fake_run_sync(user_id, *, client):
        called_with["user_id"] = user_id
        called_with["client"] = client
        return SimpleNamespace(results=[], ok=True)

    monkeypatch.setattr("gamelib.web.app.run_sync", fake_run_sync)
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.post("/sync")

    assert resp.status_code == 200
    assert called_with["user_id"] == "user-a"
    assert called_with["client"] is fake_client


def test_sync_de_um_usuario_nao_conta_jogos_do_outro_nas_estatisticas(fake_client, monkeypatch):
    from gamelib import db
    from gamelib.models import Game

    db.upsert_game(fake_client, USER_B.id, Game(platform="steam", external_id="1", name="Portal"))

    def fake_run_sync(user_id, *, client):
        return SimpleNamespace(results=[], ok=True)

    monkeypatch.setattr("gamelib.web.app.run_sync", fake_run_sync)
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.post("/sync")

    assert resp.status_code == 200
    assert "0 jogos arquivados" in resp.text
