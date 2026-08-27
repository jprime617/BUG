# ARCHITECTURE DECISION RECORDS (ADR)

Este arquivo mantém o histórico das decisões críticas do projeto para que a IA não perca o contexto entre sessões. Antes de propor grandes refatorações, leia este arquivo. Ao criar uma nova tabela, pipeline ou agente, adicione uma entrada com no máximo 3 linhas.

<!-- Novas entradas abaixo, mais recentes no topo:
## [AAAA-MM-DD] Título curto
- resumo em até 3 linhas
-->

## [2026-08-25] Dashboard unificado de bibliotecas de jogos
- Novo pacote `src/gamelib/`: modelo `Game` (models.py), SQLite stdlib sem ORM (db.py, tabelas `games`+`sync_runs`), coletores por plataforma em `collectors/` (steam via API oficial, psn via PSNAWP, xbox via OpenXBL, epic via subprocess do `legendary`, nintendo via CSV manual) orquestrados por `sync.py` com isolamento de falha por plataforma.
- Dashboard web em `web/` (FastAPI + Jinja2 + HTMX vendorizado localmente, sem framework JS). Novos alvos em `tasks.py`: `sync`, `import-nintendo`, `serve`.
- PSN usa `PSNAWP` (não `psn-api`, que é lib JS/TS); Xbox usa OpenXBL em vez de `xbox-webapi` pra evitar OAuth completo da Microsoft.
