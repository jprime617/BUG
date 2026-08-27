"""Entrypoint ASGI pro runtime Python da Vercel — reexporta o app FastAPI de
verdade. Ver `vercel.json` (roteia tudo pra cá) e `CHECKLIST-DEPLOY.md`.
"""

from gamelib.web.app import app

__all__ = ["app"]
