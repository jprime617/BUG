"""Rotas de autenticação: login, registro, esqueci-senha, logout. Fluxo
inteiramente server-side (ver `gamelib.web.auth`) — sem SDK client-side.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from gamelib.config import load_settings
from gamelib.web.auth import (
    AuthActionError,
    clear_session_cookies,
    request_password_reset,
    set_session_cookies,
    sign_in,
    sign_up,
)
from gamelib.web.templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    settings = load_settings()
    try:
        auth_response = sign_in(settings, email, password)
    except AuthActionError as exc:
        return templates.TemplateResponse(
            request, "login.html", {"error": str(exc)}, status_code=400
        )

    response = RedirectResponse(url="/", status_code=303)
    set_session_cookies(response, auth_response.session)
    return response


@router.get("/registro")
def registro_form(request: Request):
    return templates.TemplateResponse(request, "registro.html", {"error": None})


@router.post("/registro")
def registro_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    settings = load_settings()
    try:
        auth_response = sign_up(settings, email, password)
    except AuthActionError as exc:
        return templates.TemplateResponse(
            request, "registro.html", {"error": str(exc)}, status_code=400
        )

    if auth_response.session is None:
        # Confirmação de email ativada no projeto Supabase — ainda sem sessão.
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": None, "info": "Conta criada — confirme seu email antes de entrar."},
        )

    response = RedirectResponse(url="/", status_code=303)
    set_session_cookies(response, auth_response.session)
    return response


@router.get("/esqueci-senha")
def esqueci_senha_form(request: Request):
    return templates.TemplateResponse(request, "esqueci_senha.html", {"error": None, "sent": False})


@router.post("/esqueci-senha")
def esqueci_senha_submit(request: Request, email: str = Form(...)):
    settings = load_settings()
    try:
        request_password_reset(settings, email)
    except AuthActionError as exc:
        return templates.TemplateResponse(
            request, "esqueci_senha.html", {"error": str(exc), "sent": False}, status_code=400
        )

    return templates.TemplateResponse(request, "esqueci_senha.html", {"error": None, "sent": True})


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookies(response)
    return response
