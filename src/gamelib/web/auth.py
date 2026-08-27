"""Autenticação via Supabase Auth — sessão em cookie httpOnly, verificada a
cada request. Sem SDK client-side: login/registro/reset rodam inteiramente
no servidor (FastAPI + supabase-py), consistente com o resto do app
(server-rendered, sem framework JS/build step).

Vitrine compartilhada: não há biblioteca por usuário — "admin" é só quem
loga com o email em `ADMIN_EMAIL`, comparação feita aqui, nunca no Postgres
(RLS não sabe nada sobre admin, só sobre autenticado-ou-não).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from supabase_auth.errors import AuthError
from supabase_auth.types import AuthResponse, Session, User

from gamelib.config import Settings, load_settings
from gamelib.supabase_client import get_anon_client

COOKIE_ACCESS = "sb-access-token"
COOKIE_REFRESH = "sb-refresh-token"

# Prefixo, não path exato, pra cobrir todo asset em /static/*.
PUBLIC_PATHS = ("/login", "/registro", "/esqueci-senha")
PUBLIC_PREFIXES = ("/static/",)


class AuthActionError(RuntimeError):
    """Falha em login/registro/reset de senha — mensagem já pronta pra exibir."""


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _anon_client_or_raise(settings: Settings):
    try:
        return get_anon_client(settings)
    except RuntimeError as exc:
        # Supabase não configurado (setup incompleto) — mesma mensagem de
        # erro pro usuário que uma falha de autenticação, nunca um 500 cru.
        raise AuthActionError(str(exc)) from exc


def sign_in(settings: Settings, email: str, password: str) -> AuthResponse:
    client = _anon_client_or_raise(settings)
    try:
        return client.auth.sign_in_with_password({"email": email, "password": password})
    except AuthError as exc:
        raise AuthActionError(str(exc)) from exc


def sign_up(settings: Settings, email: str, password: str) -> AuthResponse:
    client = _anon_client_or_raise(settings)
    try:
        return client.auth.sign_up({"email": email, "password": password})
    except AuthError as exc:
        raise AuthActionError(str(exc)) from exc


def request_password_reset(settings: Settings, email: str) -> None:
    client = _anon_client_or_raise(settings)
    try:
        client.auth.reset_password_for_email(email)
    except AuthError as exc:
        raise AuthActionError(str(exc)) from exc


def verify_session(request: Request, *, client=None) -> User | None:
    """Lê o cookie de sessão e confirma com o Supabase. `client` é ponto de
    injeção pros testes — em produção sempre usa o anon client de verdade.
    """
    token = request.cookies.get(COOKIE_ACCESS)
    if not token:
        return None

    resolved_client = client
    if resolved_client is None:
        settings = load_settings()
        if not settings.supabase_url or not settings.supabase_anon_key:
            return None
        resolved_client = get_anon_client(settings)

    try:
        response = resolved_client.auth.get_user(token)
    except AuthError:
        return None
    return response.user if response else None


def get_current_user(request: Request) -> User | None:
    """Dependency padrão do FastAPI (mesmo idioma de `Conn`/`get_conn` em
    `app.py`). Reaproveita o resultado já verificado pelo middleware de
    autenticação quando existe, pra não bater duas vezes no Supabase por
    request.
    """
    cached = getattr(request.state, "user", None)
    if cached is not None:
        return cached
    return verify_session(request)


CurrentUser = Annotated[User | None, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    settings = load_settings()
    is_admin = (
        user is not None
        and settings.admin_email
        and (user.email or "").lower() == settings.admin_email.lower()
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador.")
    return user


Admin = Annotated[User, Depends(require_admin)]


def set_session_cookies(response: Response, session: Session) -> None:
    response.set_cookie(
        COOKIE_ACCESS,
        session.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        COOKIE_REFRESH,
        session.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/")
