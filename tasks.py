#!/usr/bin/env python3
"""Runner de tarefas cross-platform (Windows/PowerShell, WSL, macOS, Linux).

Fonte ÚNICA da lógica dos alvos padronizados. `Makefile` e `tasks.ps1` são
wrappers finos que chamam este arquivo. Uso:

    python tasks.py <alvo>

Alvos: setup | clean | test | run-pipeline | lint | format | map | help |
       sync <user_id> | import-nintendo <user_id> <csv> | serve

`sync`/`import-nintendo` escrevem na biblioteca de um usuário específico —
`user_id` é o UUID do usuário no Supabase Auth (Authentication > Users no
painel). Útil pra depuração/importação manual fora da tela /configuracoes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable  # mesmo interpretador, evita depender de "python" no PATH


def _run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT).returncode


def _has(exe: str) -> bool:
    return shutil.which(exe) is not None


def _repomix_cmd() -> list[str] | None:
    if _has("repomix"):
        return ["repomix"]
    if _has("npx"):
        return ["npx", "--yes", "repomix"]
    return None


# --- alvos -------------------------------------------------------------------
def setup(argv: list[str]) -> int:
    for d in ("src/utils", "src/agents", "tests"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    print("Diretorios garantidos: src/utils, src/agents, tests")
    return _map(argv)


def clean(argv: list[str]) -> int:
    removed = 0
    for pyc in ROOT.rglob("__pycache__"):
        if ".git" not in pyc.parts:
            shutil.rmtree(pyc, ignore_errors=True)
            removed += 1
    for name in (".pytest_cache", ".ruff_cache"):
        p = ROOT / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    for name in ("repomix-map.txt", "repomix-output.txt"):
        p = ROOT / name
        if p.exists():
            p.unlink()
            removed += 1
    print(f"Limpeza concluida ({removed} item(ns) removido(s)).")
    return 0


def test(argv: list[str]) -> int:
    tests_dir = ROOT / "tests"
    has_tests = tests_dir.is_dir() and (
        any(tests_dir.rglob("test_*.py")) or any(tests_dir.rglob("*_test.py"))
    )
    if not has_tests:
        print("Nenhum teste encontrado em tests/.")
        return 0
    try:
        import pytest  # noqa: F401
    except ImportError:
        print('pytest nao instalado. Rode: pip install -e ".[dev]"')
        return 1
    return _run([PY, "-m", "pytest", "tests/"])


def run_pipeline(argv: list[str]) -> int:
    print("Executando pipeline de exemplo...")
    return _run([PY, "templates/advanced_agent_core.py"])


def lint(argv: list[str]) -> int:
    if not _has("ruff"):
        print('ruff nao instalado. Rode: pip install -e ".[dev]"')
        return 1
    return _run(["ruff", "check", "."])


def format_(argv: list[str]) -> int:
    if not _has("ruff"):
        print('ruff nao instalado. Rode: pip install -e ".[dev]"')
        return 1
    rc = _run(["ruff", "check", ".", "--fix"])
    return _run(["ruff", "format", "."]) or rc


def sync(argv: list[str]) -> int:
    if not argv:
        print("Uso: python tasks.py sync <user_id>")
        return 2

    from gamelib.sync import run_sync

    report = run_sync(argv[0])
    for result in report.results:
        detail = (
            f"{result.games_found} jogo(s)" if result.status == "success" else (result.error or "")
        )
        print(f"  {result.platform:<10} {result.status:<9} {detail}")
    return 0 if report.ok else 1


def import_nintendo(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: python tasks.py import-nintendo <user_id> <caminho.csv>")
        return 2

    from gamelib import db
    from gamelib.collectors.base import CollectorError
    from gamelib.collectors.nintendo_csv import import_csv
    from gamelib.config import load_settings

    user_id, csv_path = argv[0], argv[1]
    settings = load_settings(user_id)
    try:
        games = import_csv(Path(csv_path), settings)
    except CollectorError as exc:
        print(f"Falha na importacao: {exc}")
        return 1

    conn = db.connect(settings)
    for game in games:
        db.upsert_game(conn, user_id, game)
    print(f"Importados {len(games)} jogo(s) da Nintendo a partir de {csv_path}.")
    return 0


def serve(argv: list[str]) -> int:
    host = "127.0.0.1"
    port = "8000"
    print(f"Servindo dashboard em http://{host}:{port} (Ctrl+C para parar)...")
    return _run([PY, "-m", "uvicorn", "gamelib.web.app:app", "--host", host, "--port", port])


def _map(argv: list[str]) -> int:
    cmd = _repomix_cmd()
    if cmd is None:
        print("repomix/npx nao encontrado; pulei o mapa. Instale Node.js + repomix.")
        return 0
    print("Gerando mapa de arquitetura (repomix-map.txt)...")
    return _run(
        [
            *cmd,
            "--output",
            "repomix-map.txt",
            "--include",
            "**/*.py,**/*.js,**/*.ts,**/*.html,**/*.css",
        ]
    )


def help_(argv: list[str]) -> int:
    print(__doc__)
    return 0


TARGETS = {
    "setup": setup,
    "clean": clean,
    "test": test,
    "run-pipeline": run_pipeline,
    "lint": lint,
    "format": format_,
    "map": _map,
    "sync": sync,
    "import-nintendo": import_nintendo,
    "serve": serve,
    "help": help_,
}


def main(argv: list[str]) -> int:
    target = argv[0] if argv else "help"
    fn = TARGETS.get(target)
    if fn is None:
        print(f"Alvo desconhecido: {target}\nDisponiveis: {', '.join(TARGETS)}")
        return 2
    return fn(argv[1:]) or 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
