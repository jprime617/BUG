from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from tests.fakes import FakeSupabaseClient

from gamelib import settings_store

FAKE_KEY = Fernet.generate_key().decode()


def test_get_setting_le_valor_nao_cifrado_do_banco(monkeypatch):
    client = FakeSupabaseClient()
    client.table("settings").insert(
        {"key": "rawg_api_key", "value": "abc123", "encrypted": False}
    ).execute()

    value = settings_store.get_setting("rawg_api_key", client=client)

    assert value == "abc123"


def test_get_setting_descriptografa_valor_cifrado(monkeypatch):
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", FAKE_KEY)
    client = FakeSupabaseClient()
    settings_store.set_setting("steam_api_key", "segredo", encrypted=True, client=client)

    value = settings_store.get_setting("steam_api_key", client=client)

    assert value == "segredo"
    stored = client.table("settings").select("*").eq("key", "steam_api_key").execute().data[0]
    assert stored["value"] != "segredo"  # ciphertext no banco, não o valor puro


def test_get_setting_banco_vence_env_quando_os_dois_existem(monkeypatch):
    monkeypatch.setenv("RAWG_API_KEY", "valor-do-env")
    client = FakeSupabaseClient()
    client.table("settings").insert(
        {"key": "rawg_api_key", "value": "valor-do-banco", "encrypted": False}
    ).execute()

    value = settings_store.get_setting("rawg_api_key", env_fallback="RAWG_API_KEY", client=client)

    assert value == "valor-do-banco"


def test_get_setting_cai_pro_env_quando_supabase_nao_configurado(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("RAWG_API_KEY", "valor-do-env")

    value = settings_store.get_setting("rawg_api_key", env_fallback="RAWG_API_KEY")

    assert value == "valor-do-env"


def test_get_setting_sem_banco_nem_env_devolve_none(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("RAWG_API_KEY", raising=False)

    assert settings_store.get_setting("rawg_api_key", env_fallback="RAWG_API_KEY") is None


def test_get_setting_chave_de_criptografia_ausente_levanta_erro_claro(monkeypatch):
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    client = FakeSupabaseClient()
    client.table("settings").insert(
        {"key": "steam_api_key", "value": "cifrado-qualquer", "encrypted": True}
    ).execute()

    with pytest.raises(RuntimeError, match="SETTINGS_ENCRYPTION_KEY"):
        settings_store.get_setting("steam_api_key", client=client)


def test_mask_mostra_so_os_ultimos_4_caracteres():
    assert settings_store.mask("abcdefgh1234") == "••••••••1234"


def test_mask_valor_curto_fica_todo_oculto():
    assert settings_store.mask("ab") == "••"
