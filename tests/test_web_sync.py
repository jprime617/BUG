from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from tests.fakes import FakeSupabaseClient

from gamelib.sync import PlatformResult, SyncEvent
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


def test_sync_stream_usuario_anonimo_redireciona_para_login(fake_client, monkeypatch):
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: None)
    app.dependency_overrides[get_conn] = lambda: fake_client
    client = TestClient(app)

    resp = client.get("/sync/stream", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_sync_stream_emite_eventos_na_ordem_com_dados_reais(fake_client, monkeypatch):
    def fake_run_sync_iter(user_id, **kwargs):
        assert user_id == "user-a"
        yield SyncEvent("targets", targets=["steam", "psn"])
        yield SyncEvent(
            "platform_done",
            platform="steam",
            index=1,
            total=2,
            result=PlatformResult("steam", "success", games_found=42),
        )
        yield SyncEvent(
            "platform_done",
            platform="psn",
            index=2,
            total=2,
            result=PlatformResult("psn", "skipped"),
        )

    monkeypatch.setattr("gamelib.web.app.run_sync_iter", fake_run_sync_iter)
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.get("/sync/stream")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert body.index("event: targets") < body.index("event: platform_done")
    assert '"games_found": 42' in body
    assert '"status": "skipped"' in body
    assert body.rstrip().endswith("event: complete\ndata: {}")


def test_sync_stream_de_um_usuario_nao_mistura_dados_do_outro(fake_client, monkeypatch):
    from gamelib import db
    from gamelib.models import Game

    db.upsert_game(fake_client, USER_B.id, Game(platform="steam", external_id="1", name="Portal"))

    def fake_run_sync_iter(user_id, **kwargs):
        assert user_id == "user-a"
        yield SyncEvent("targets", targets=[])

    monkeypatch.setattr("gamelib.web.app.run_sync_iter", fake_run_sync_iter)
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.get("/sync/stream")

    assert resp.status_code == 200
    assert "Portal" not in resp.text


def test_partials_stats_escopado_ao_usuario_logado(fake_client, monkeypatch):
    from gamelib import db
    from gamelib.models import Game

    db.upsert_game(fake_client, USER_B.id, Game(platform="steam", external_id="1", name="Portal"))
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.get("/partials/stats")

    assert resp.status_code == 200
    assert "0 jogos arquivados" in resp.text
