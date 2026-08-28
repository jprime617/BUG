"""Entrypoint ASGI pro runtime Python da Vercel — reexporta o app FastAPI de
verdade. Ver `vercel.json` (roteia tudo pra cá) e `CHECKLIST-DEPLOY.md`.

O runtime da Vercel só instala `requirements.txt`; não roda `pip install -e .`
nem nada que coloque `src/` (layout src do projeto) no sys.path — sem o
insert abaixo, `import gamelib` falha com ModuleNotFoundError e a function
crasha na inicialização (tela branca / FUNCTION_INVOCATION_FAILED).
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gamelib.web.app import app  # noqa: E402

__all__ = ["app"]
