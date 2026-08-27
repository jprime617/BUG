from __future__ import annotations

from types import SimpleNamespace

import httpx
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
def _clean_platform_env(monkeypatch):
    # `load_settings()` sempre chama `load_dotenv()`, que preenche variáveis
    # ausentes a partir de um `.env` local real — zera explicitamente pra
    # isolar os testes do que estiver configurado na máquina de quem roda.
    for var in ("RAWG_API_KEY", "STEAM_API_KEY", "STEAM_ID64", "PSN_NPSSO", "XBOX_OPENXBL_KEY"):
        monkeypatch.setenv(var, "")


def _client(fake_client, monkeypatch, user) -> TestClient:
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: user)
    app.dependency_overrides[get_conn] = lambda: fake_client
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_configuracoes_usuario_anonimo_redireciona_para_login(fake_client, monkeypatch):
    monkeypatch.setattr("gamelib.web.app.verify_session", lambda request: None)
    app.dependency_overrides[get_conn] = lambda: fake_client
    client = TestClient(app)

    resp = client.get("/configuracoes", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_configuracoes_usuario_nao_admin_recebe_403(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, VISITOR)

    resp = client.get("/configuracoes")

    assert resp.status_code == 403


def test_configuracoes_admin_renderiza_formulario(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.get("/configuracoes")

    assert resp.status_code == 200
    assert "RAWG API Key" in resp.text
    assert "não configurado" in resp.text.lower()


def test_configuracoes_admin_configurado_via_env_mostra_status_ok(fake_client, monkeypatch):
    monkeypatch.setenv("RAWG_API_KEY", "chave-de-teste-1234")
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.get("/configuracoes")

    assert "configurado" in resp.text.lower()
    assert "1234" in resp.text  # últimos 4 caracteres mascarados


def test_configuracoes_salvar_grava_via_settings_store(fake_client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gamelib.web.routes_settings.settings_store.set_setting",
        lambda key, value, **kw: calls.append((key, value, kw)),
    )
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.post("/configuracoes", data={"rawg_api_key": "nova-chave"})

    assert resp.status_code == 200
    assert "Configurações salvas" in resp.text
    assert calls == [
        (
            "rawg_api_key",
            "nova-chave",
            {"encrypted": True, "updated_by": "dono@example.com", "client": fake_client},
        )
    ]


def test_configuracoes_salvar_ignora_campos_vazios(fake_client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gamelib.web.routes_settings.settings_store.set_setting",
        lambda key, value, **kw: calls.append(key),
    )
    client = _client(fake_client, monkeypatch, ADMIN)

    client.post("/configuracoes", data={"rawg_api_key": "", "steam_api_key": "  "})

    assert calls == []


def test_testar_conexao_rawg_sucesso(fake_client, monkeypatch):
    monkeypatch.setenv("RAWG_API_KEY", "chave-valida")

    def fake_get(*args, **kwargs):
        return httpx.Response(200, json={"results": []})

    monkeypatch.setattr(httpx, "get", fake_get)
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.post("/configuracoes/testar/rawg")

    assert resp.status_code == 200
    assert "settings-test-result__badge--ok" in resp.text


def test_testar_conexao_rawg_sem_chave_mostra_erro(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.post("/configuracoes/testar/rawg")

    assert resp.status_code == 200
    assert "settings-test-result__badge--erro" in resp.text


def test_testar_conexao_integracao_desconhecida(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, ADMIN)

    resp = client.post("/configuracoes/testar/inexistente")

    assert "Integração desconhecida" in resp.text
