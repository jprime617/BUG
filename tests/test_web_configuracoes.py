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


def test_configuracoes_usuario_logado_renderiza_formulario(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.get("/configuracoes")

    assert resp.status_code == 200
    assert "Steam API Key" in resp.text
    assert "não configurado" in resp.text.lower()


def test_configuracoes_salvar_grava_via_settings_store(fake_client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gamelib.web.routes_settings.settings_store.set_setting",
        lambda key, value, user_id, **kw: calls.append((key, value, user_id, kw)),
    )
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.post("/configuracoes", data={"steam_api_key": "nova-chave"})

    assert resp.status_code == 200
    assert "Configurações salvas" in resp.text
    assert calls == [
        (
            "steam_api_key",
            "nova-chave",
            "user-a",
            {"encrypted": True, "updated_by": "a@example.com", "client": fake_client},
        )
    ]


def test_configuracoes_salvar_ignora_campos_vazios(fake_client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gamelib.web.routes_settings.settings_store.set_setting",
        lambda key, value, user_id, **kw: calls.append(key),
    )
    client = _client(fake_client, monkeypatch, USER_A)

    client.post("/configuracoes", data={"steam_api_key": "", "steam_id64": "  "})

    assert calls == []


def test_configuracoes_usuario_nao_ve_credencial_configurada_por_outro(fake_client, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", Fernet.generate_key().decode())

    client_b = _client(fake_client, monkeypatch, USER_B)
    client_b.post("/configuracoes", data={"steam_api_key": "chave-da-usuaria-b"})

    client_a = _client(fake_client, monkeypatch, USER_A)
    resp = client_a.get("/configuracoes")

    assert "não configurado" in resp.text.lower()


def test_testar_conexao_steam_sem_credenciais_mostra_erro(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.post("/configuracoes/testar/steam")

    assert resp.status_code == 200
    assert "settings-test-result__badge--erro" in resp.text


def test_testar_conexao_integracao_desconhecida(fake_client, monkeypatch):
    client = _client(fake_client, monkeypatch, USER_A)

    resp = client.post("/configuracoes/testar/inexistente")

    assert "Integração desconhecida" in resp.text
