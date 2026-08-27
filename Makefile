# Alvos padronizados do agente IA. Logica em tasks.py (fonte unica, cross-platform).
# Windows/PowerShell: use `.\tasks.ps1 <alvo>` ou `python tasks.py <alvo>`.
# NAO edite alvos sem atualizar o ADR em .claude/memory/architecture-decisions.md

PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python)

.PHONY: setup clean test run-pipeline lint format map help sync import-nintendo serve

setup:
	@$(PYTHON) tasks.py setup

clean:
	@$(PYTHON) tasks.py clean

test:
	@$(PYTHON) tasks.py test

run-pipeline:
	@$(PYTHON) tasks.py run-pipeline

lint:
	@$(PYTHON) tasks.py lint

format:
	@$(PYTHON) tasks.py format

map:
	@$(PYTHON) tasks.py map

sync:
	@$(PYTHON) tasks.py sync

import-nintendo:
	@$(PYTHON) tasks.py import-nintendo $(CSV)

serve:
	@$(PYTHON) tasks.py serve

help:
	@$(PYTHON) tasks.py help
