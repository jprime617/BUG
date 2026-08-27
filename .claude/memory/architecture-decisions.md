# ARCHITECTURE DECISION RECORDS (ADR)

Este arquivo mantém o histórico das decisões críticas do projeto para que a IA não perca o contexto entre sessões. Antes de propor grandes refatorações, leia este arquivo. Ao criar uma nova tabela, pipeline ou agente, adicione uma entrada com no máximo 3 linhas.

<!-- Novas entradas abaixo, mais recentes no topo:
## [AAAA-MM-DD] Título curto
- resumo em até 3 linhas
-->

## [2026-08-27] Migração pra Supabase (Auth + Postgres) + deploy na Vercel
- `games`/`game_metadata`/`sync_runs` saem de SQLite local pra Postgres do Supabase (supabase-py/PostgREST) — vitrine compartilhada sem biblioteca por usuário; RLS ativo em todas as tabelas como defesa em profundidade (servidor sempre usa `service_role`).
- Auth via Supabase Auth (cookie httpOnly, middleware fail-closed com allow-list); admin = comparação de email com `ADMIN_EMAIL`, não tabela de roles. Credenciais de plataforma (Steam/PSN/Xbox/RAWG) viram configurações dinâmicas cifradas (Fernet) em `settings`, editáveis via `/configuracoes` (admin-only), com fallback pro `.env` em dev local.
- Epic Games não tem versão hospedada (CLI local com login interativo, inviável em serverless) — autodesliga na Vercel sem código especial. Deploy via `vercel.json` + `api/index.py` (ASGI).

## [2026-08-27] Modal do jogo: trailer → sinopse + Metacritic + galeria
- `game_metadata` ganha `metacritic`/`description`/`screenshots` (migração aditiva idempotente em `connect()`); `video_url` mantido sem uso.
- Trailer (`/movies`) trocado por sinopse via endpoint de detalhe da RAWG (mesmo custo: 1 chamada extra); `metacritic`/screenshots vêm de graça do endpoint de busca já usado.
- Modal abre em `htmx:beforeRequest` (instantâneo, com skeleton) em vez de `htmx:afterSwap`.

## [2026-08-25] Dashboard unificado de bibliotecas de jogos
- Novo pacote `src/gamelib/`: modelo `Game` (models.py), SQLite stdlib sem ORM (db.py, tabelas `games`+`sync_runs`), coletores por plataforma em `collectors/` (steam via API oficial, psn via PSNAWP, xbox via OpenXBL, epic via subprocess do `legendary`, nintendo via CSV manual) orquestrados por `sync.py` com isolamento de falha por plataforma.
- Dashboard web em `web/` (FastAPI + Jinja2 + HTMX vendorizado localmente, sem framework JS). Novos alvos em `tasks.py`: `sync`, `import-nintendo`, `serve`.
- PSN usa `PSNAWP` (não `psn-api`, que é lib JS/TS); Xbox usa OpenXBL em vez de `xbox-webapi` pra evitar OAuth completo da Microsoft.
