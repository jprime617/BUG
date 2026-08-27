from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from tests.fakes import FakeSupabaseClient

from gamelib.web.app import app
from gamelib.web.deps import get_conn

ADMIN = SimpleNamespace(email="dono@example.com")
VISITOR = SimpleNamespace(email="visitante@example.com")


@pytest.fixture
def fake_client() -> FakeSupabaseClient:
    return FakeSupabaseClient()


@pytest.fixture(autouse=True)
def _admin_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "dono@example.com")


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


def test_sync_usuario_nao_admin_recebe_403(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, VISITOR)

    resp = client.post("/sync")

    assert resp.status_code == 403


def test_sync_admin_roda_run_sync(fake_client, monkeypatch):
    called_with = {}

    def fake_run_sync(*, client):
        called_with["client"] = client
        return SimpleNamespace(results=[], ok=True)

    monkeypatch.setattr("gamelib.web.app.run_sync", fake_run_sync)
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.post("/sync")

    assert resp.status_code == 200
    assert called_with["client"] is fake_client
