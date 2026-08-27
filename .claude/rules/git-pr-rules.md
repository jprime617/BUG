# DIRETRIZES: GIT, COMMITS E PULL REQUESTS

## Commits
- Conventional Commits (padrão já usado no histórico deste repo): `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`.
- Assunto no imperativo e curto (≤ ~72 chars): "adiciona runner cross-platform", não "adicionado" nem "adicionando".
- Um commit = uma mudança coerente. Não misture refactor + feature + formatação no mesmo commit.
- Só faça commit/push quando o usuário pedir. Se estiver na `main`, crie um branch antes.

## Segurança
- Nunca versione segredos: `.env`, chaves, tokens, credenciais. Confira o diff antes de commitar (`git diff --staged`).
- `.env` é ignorado; o versionado é `env.example` (sem valores reais).

## Pull Requests
- Título = resumo da mudança no mesmo estilo do commit.
- Corpo responde **o quê** mudou e **por quê** (contexto/decisão), não só o "como".
- Referencie a entrada de ADR (`.claude/memory/architecture-decisions.md`) quando a mudança for arquitetural.
