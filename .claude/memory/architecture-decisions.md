# ARCHITECTURE DECISION RECORDS (ADR)

Este arquivo mantém o histórico das decisões críticas do projeto para que a IA não perca o contexto entre sessões. Antes de propor grandes refatorações, leia este arquivo. Ao criar uma nova tabela, pipeline ou agente, adicione uma entrada com no máximo 3 linhas.

<!-- Novas entradas abaixo, mais recentes no topo:
## [AAAA-MM-DD] Título curto
- resumo em até 3 linhas
-->

## [2026-08-28] Remove Epic/Nintendo; corrige playtime do Xbox
- Epic (`legendary` CLI, só local) e Nintendo (CSV manual) removidos do sistema: `collectors/epic.py`/`nintendo_csv.py` deletados, `Platform`/`PLATFORMS` agora só `steam`/`psn`/`xbox`, `legendary_bin`/`LEGENDARY_BIN` fora de `Settings`/`env.example`, alvo `import-nintendo` removido de `tasks.py`/`Makefile`.
- Bug real corrigido: playtime do Xbox nunca aparecia porque o coletor lia `GET /achievements/stats/{titleId}` (sem `MinutesPlayed` garantido); OpenXBL exige pedir o stat explicitamente via `POST /player/stats` com `xuid` + lista de stats (conforme openapi.yaml oficial em github.com/OpenXBL/Docs) — agora um único POST em lote pra todos os títulos.
- Mesmo com o fix, nem todo jogo Xbox publica `MinutesPlayed` na Xbox Live — quando ausente, o jogo aparece na biblioteca normalmente, só sem tempo jogado (documentado em `docs/CREDENTIALS.md`).

## [2026-08-28] Multi-tenant: biblioteca por usuário (fim da vitrine compartilhada)
- `games`/`sync_runs`/`settings` ganham `user_id` (FK `auth.users`); toda leitura/escrita em `db.py`/`settings_store.py`/`sync.py` passa a exigir `user_id` e RLS troca `using (true)` por `using (auth.uid() = user_id)`.
- Conceito de admin removido (`require_admin`/`ADMIN_EMAIL` fora): `/configuracoes` (Steam/PSN/Xbox) e `/sync` abrem pra qualquer usuário autenticado, escopados ao próprio id. `RAWG_API_KEY` continua a única credencial global, só via `.env`.
- `get_game` passa a filtrar por dono (fecha IDOR de `/games/{id}`); CLI `sync`/`import-nintendo` ganham `<user_id>` posicional obrigatório.

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
