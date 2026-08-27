# DIRETRIZES: ARQUITETURA E ENGENHARIA (BASELINE CROSS-LINGUAGEM)

Piso de qualidade para qualquer código, independente da linguagem. Regras específicas de domínio (Python/dados, SQL, frontend) complementam este baseline.

## Princípios
- DRY, SOLID, YAGNI: prefira composição clara a camadas de abstração pesadas ou herança profunda. Não abstraia antes de haver duplicação real.
- Tipagem estrita: anotações de tipo obrigatórias (Python type hints, TypeScript strict, tipos explícitos em Rust/Go). Nada de `any` gratuito.
- Error handling defensivo: `try/except` explícito nos limites (I/O, rede, parsing). Nunca engula exceção (`pass`/`catch {}` vazio) — logue e propague ou trate.

## Performance e contexto
- Dependências mínimas: prefira a stdlib da linguagem a dependências externas pesadas para tarefas simples.
- Navegação por símbolo: localize funções/símbolos/trechos por índice (`repomix-map.txt`, grep, símbolos) antes de ler arquivos inteiros.
- Fail fast: valide entradas e limites (tamanho, quota de API, nulos) na fronteira, cedo.

## Verificação (antes de declarar concluído)
- Toda mudança de código vem com teste correspondente (unitário/integração) — ver `.claude/rules/testing-rules.md`.
- Rode testes e lint (`make test` / `make lint` ou `python tasks.py test|lint`) antes de dizer que terminou; corrija falhas sem post-mortem longo.
- Mantenha logs de terminal/teste compactos: inspecione backtraces de falha, não a saída inteira.
