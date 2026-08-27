# DIRETRIZES: CLAUDE / ANTHROPIC API E AGENTES LLM

## Antes de codificar
- Ao mexer em qualquer código que use a API da Anthropic/Claude (SDK, agentes, MCP, tool-use, RAG, LLM-as-judge), invoque a skill `claude-api` **antes**. Não responda de memória sobre model IDs, limites ou preços — eles mudam.

## Modelos (referência jul/2026 — confirme na skill `claude-api`)
- Família mais recente: **Opus 4.8** (`claude-opus-4-8`), **Sonnet 5** (`claude-sonnet-5`), **Haiku 4.5** (`claude-haiku-4-5-20251001`), **Fable 5** (`claude-fable-5`).
- Default: o modelo mais capaz e recente adequado à tarefa. Haiku para tarefas baratas/mecânicas; Opus para raciocínio difícil.

## Credenciais e configuração
- `ANTHROPIC_API_KEY` sempre em variável de ambiente (ver `env.example`) — nunca hardcoded nem versionada.

## Boas práticas de chamada
- Prompt caching para prefixos grandes e repetidos (system prompt, contexto fixo).
- Streaming para respostas longas.
- Tool-use/agentes: schemas de ferramentas claros e desacoplados (alinhado a `.claude/rules/python-data-rules.md`); trate refusals, cutoffs e limites de token com fallback explícito.
- Isole a chamada ao LLM atrás de uma função/adapter para trocar de modelo sem espalhar mudanças.
