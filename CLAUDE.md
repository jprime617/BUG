# CLAUDE.MD - ROTEADOR DE CONTEXTO

Você está operando em uma arquitetura modular. Não assuma regras de negócio genéricas: leia o arquivo de contexto específico em `.claude/` conforme o tipo de arquivo que estiver editando, além destas diretrizes gerais.

## 🧭 Gatilhos de Contexto (Context Routing)
| Se estiver editando... | Leia obrigatoriamente |
|---|---|
| **Qualquer código (baseline)** | `.claude/rules/code-architecture.md` |
| Python, pipelines de dados, Pandas (`*.py`) | `.claude/rules/python-data-rules.md` |
| UI / Frontend (`*.css`, `*.html`, `*.tsx`, `*.jsx`, `*.vue`) | `.claude/rules/frontend-design-rules.md` |
| Terminal, scripts, automações de CLI (`*.sh`) | `.claude/rules/bash-scripts.md` |
| Banco de dados e consultas (`*.sql`) | `.claude/rules/sql-architecture.md` |
| Testes (`tests/`, `test_*.py`) | `.claude/rules/testing-rules.md` |
| Commits, branches, pull requests | `.claude/rules/git-pr-rules.md` |
| Código que usa a API Claude/Anthropic (LLM, agentes, MCP) | `.claude/rules/llm-api-rules.md` |

> Os hooks em `.claude/settings.json` já injetam a regra do domínio automaticamente ao editar o arquivo; a tabela é o fallback e serve de índice.

## 🪙 Economia de Tokens e Agilidade
- Zero verbosidade: proibido usar frases de preenchimento. Vá direto ao ponto técnico ou ao código.
- Estilo telegráfico: frases técnicas curtas e densas; não explique *por que* o código funciona salvo se pedido.
- Modificações cirúrgicas: ao alterar código existente, forneça apenas o trecho exato alterado (diff-style), a menos que solicitado o contrário.
- Operações direcionadas: busque funções/símbolos/linhas específicas; não despeje arquivos inteiros no contexto.
- Compactação dinâmica: alerte o usuário para rodar `/compact` se a sessão atingir logs longos.
- Uso de mapas: sempre consulte `repomix-map.txt` antes de navegar cegamente pelo código.

## ⚙️ Execução de Tarefas
- Nunca invente sequências de comandos. Use os alvos padronizados (lógica em fonte única `tasks.py`):
  - **bash / WSL / macOS / Linux**: `make <alvo>`
  - **Windows / PowerShell**: `.\tasks.ps1 <alvo>` ou `python tasks.py <alvo>`
  - Alvos: `setup`, `clean`, `test`, `run-pipeline`, `lint`, `format`, `map`.
- Plan Mode primeiro: use Plan Mode (`Shift+Tab`) para tarefas que tocam >2 arquivos ou refactors arquiteturais.
- Verificação antes de concluir: rode `test`/`lint` e corrija erros antes de declarar a tarefa pronta — sem post-mortem longo.

## 🤖 Automação nativa (`.claude/`)
- `settings.json`: allowlist de permissões (menos prompts), `env` e hooks. Config local não-versionada em `settings.local.json`.
- `commands/`: slash commands reutilizáveis (`/novo-agente`, `/adr`, `/refresh-map`).
- `agents/`: subagentes especializados (ex.: revisor de pipeline de dados).

## 🧠 Memória e Decisões de Arquitetura
- Sempre que criar uma nova tabela, configurar uma nova pipeline de automação ou criar um novo agente, documente um resumo técnico de até 3 linhas em `.claude/memory/architecture-decisions.md`.
- Antes de propor grandes refatorações, leia esse arquivo para entender o histórico do projeto.
