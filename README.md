# Biblioteca de Jogos — dashboard unificado

Painel local que agrega jogos possuídos em Steam, PlayStation e Xbox em uma
base SQLite única, com um dashboard web para visualizar, buscar e filtrar.

Disponibilidade de dados varia por plataforma (Steam tem API oficial
completa; PSN/Xbox usam wrappers não-oficiais) — campos sem dado disponível
aparecem como "—" na UI, nunca como zero inventado.

## Setup

```bash
python tasks.py setup          # garante diretórios do boilerplate
pip install -e ".[dev]"        # dependências (fastapi, httpx, PSNAWP, pytest, ruff...)
cp env.example .env            # preencha as credenciais que for usar
```

Veja [`docs/CREDENTIALS.md`](docs/CREDENTIALS.md) para como obter o token de
cada plataforma. Nenhuma é obrigatória — plataformas sem credencial são
puladas na sincronização.

## Uso

```bash
python tasks.py sync   # sincroniza Steam/PSN/Xbox configurados
python tasks.py serve  # sobe o dashboard em http://127.0.0.1:8000
```

(equivalentes via `make sync`, `make serve`, ou `.\tasks.ps1 sync` /
`.\tasks.ps1 serve` no Windows)

Sincronização é sempre sob demanda — para automatizar, agende
`python tasks.py sync` via cron (Linux/macOS) ou Agendador de Tarefas
(Windows); não há scheduler embutido no processo.

## Verificação

```bash
python tasks.py test    # pytest — coletores testados com HTTP/subprocess mockado, sem rede real
python tasks.py lint    # ruff
```

## Arquitetura

- `src/gamelib/models.py` — modelo unificado de jogo (`Game`).
- `src/gamelib/db.py` — SQLite (stdlib), tabelas `games` e `sync_runs`.
- `src/gamelib/collectors/` — um coletor por plataforma (`steam`, `psn`,
  `xbox`), protocolo comum em `base.py`.
- `src/gamelib/sync.py` — orquestra os coletores; falha de uma plataforma
  não derruba as outras (circuit breaker por plataforma).
- `src/gamelib/web/` — dashboard FastAPI + Jinja2 + HTMX (sem CDN — HTMX
  vendorizado em `web/static/`).

Decisões de arquitetura registradas em
[`.claude/memory/architecture-decisions.md`](.claude/memory/architecture-decisions.md).
