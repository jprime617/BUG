from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from supabase_auth.errors import AuthApiError

from gamelib.web.auth import get_current_user, require_admin, verify_session


def _request(cookie: str | None = None) -> Request:
    headers = [(b"cookie", f"sb-access-token={cookie}".encode())] if cookie else []
    return Request({"type": "http", "headers": headers, "state": {}})


class _FakeAuth:
    def __init__(self, user=None, raise_error: bool = False) -> None:
        self._user = user
        self._raise_error = raise_error

    def get_user(self, token: str):
        if self._raise_error:
            raise AuthApiError("token inválido", 401, None)
        if self._user is None:
            return None
        return SimpleNamespace(user=self._user)


class _FakeAuthClient:
    def __init__(self, user=None, raise_error: bool = False) -> None:
        self.auth = _FakeAuth(user=user, raise_error=raise_error)


def test_verify_session_sem_cookie_devolve_none():
    assert verify_session(_request()) is None


def test_verify_session_cookie_valido_devolve_usuario():
    user = SimpleNamespace(email="dono@example.com")
    client = _FakeAuthClient(user=user)

    result = verify_session(_request("token-valido"), client=client)

    assert result is user


def test_verify_session_token_invalido_devolve_none():
    client = _FakeAuthClient(raise_error=True)

    assert verify_session(_request("token-expirado"), client=client) is None


def test_get_current_user_reaproveita_request_state_do_middleware():
    user = SimpleNamespace(email="dono@example.com")
    request = _request()
    request.state.user = user

    assert get_current_user(request) is user


def test_require_admin_usuario_anonimo_levanta_403(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "dono@example.com")

    with pytest.raises(HTTPException) as exc_info:
        require_admin(None)

    assert exc_info.value.status_code == 403


def test_require_admin_usuario_nao_admin_levanta_403(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "dono@example.com")
    user = SimpleNamespace(email="visitante@example.com")

    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)

    assert exc_info.value.status_code == 403


def test_require_admin_email_bate_devolve_usuario(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "Dono@Example.com")
    user = SimpleNamespace(email="dono@example.com")

    assert require_admin(user) is user


def test_require_admin_sem_admin_email_configurado_levanta_403(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    user = SimpleNamespace(email="qualquer@example.com")

    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)

    assert exc_info.value.status_code == 403
