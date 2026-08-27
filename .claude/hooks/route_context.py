#!/usr/bin/env python3
"""Hook PreToolUse: injeta a regra de domínio de `.claude/` ao editar um arquivo.

Torna o roteamento de contexto confiável (não depende de o modelo ler a tabela).
Nunca bloqueia: em qualquer erro, sai 0 sem efeito.
"""

import json
import sys

# arquivo de regra -> foco de 1 linha
RULES = {
    "python-data-rules.md": "vetorização Pandas, circuit breaker por etapa, logs estruturados",
    "frontend-design-rules.md": "invocar skill frontend-design; evitar clichês de 'cara de IA'",
    "bash-scripts.md": "caminhos relativos; limpeza via `python tasks.py clean`",
    "sql-architecture.md": "snake_case plural, índices em WHERE/JOIN/FK, CREATE ... IF NOT EXISTS",
    "testing-rules.md": "pytest, AAA, testar erro além do caminho feliz, sem rede/DB real",
}


def rule_for(path: str) -> str | None:
    p = path.replace("\\", "/").lower()
    base = p.rsplit("/", 1)[-1]
    if p.endswith(".py"):
        if base.startswith("test_") or base.endswith("_test.py") or "/tests/" in p:
            return "testing-rules.md"
        return "python-data-rules.md"
    if p.endswith((".css", ".html", ".tsx", ".jsx", ".vue")):
        return "frontend-design-rules.md"
    if p.endswith(".sh"):
        return "bash-scripts.md"
    if p.endswith(".sql"):
        return "sql-architecture.md"
    return None


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tool_input = data.get("tool_input", {}) or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path:
        return

    msgs = []
    rule = rule_for(path)
    if rule:
        msgs.append(f"Contexto de domínio: leia `.claude/rules/{rule}` antes de editar (foco: {RULES[rule]}).")

    p = path.replace("\\", "/").lower()
    if "/src/agents/" in p or p.startswith("src/agents/") or p.endswith(".sql"):
        msgs.append(
            "Se isto cria/altera um agente, tabela ou pipeline, registre 3 linhas em "
            "`.claude/memory/architecture-decisions.md`."
        )

    if not msgs:
        return
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": " ".join(msgs),
        }
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
