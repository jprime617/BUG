---
description: Cria um novo agente em src/agents/ a partir do template (tools registráveis, circuit breaker, logs) e registra um ADR.
argument-hint: [nome-do-agente]
allowed-tools: Read, Write, Edit
---
Crie um novo agente chamado "$ARGUMENTS" em `src/agents/`, seguindo `.claude/rules/python-data-rules.md` e o padrão de `templates/advanced_agent_core.py`:
- Habilidades como tools registráveis e desacopladas.
- Pipeline com try/except por etapa (circuit breaker) que loga exatamente onde falhou.
- Logs estruturados (nível/timestamp/etapa), nunca `print()` solto.

Depois adicione uma entrada de até 3 linhas em `.claude/memory/architecture-decisions.md` descrevendo o agente.
