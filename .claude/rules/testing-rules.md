# DIRETRIZES: TESTES (PYTEST)

## Estrutura
- Ferramenta padrão: `pytest`. Rode via `python tasks.py test` (ou `make test`) — nunca invente o comando.
- Arquivos em `tests/`, nomeados `test_*.py`. Um teste = um comportamento; nome descreve o comportamento, não a função (ex.: `test_circuit_breaker_aponta_etapa_que_falhou`).
- Padrão Arrange-Act-Assert; um `assert` conceitual por teste.

## O que testar
- Caminho feliz **e** pelo menos um caminho de erro (o circuit breaker de `.claude/rules/python-data-rules.md` precisa ter teste de falha).
- Teste comportamento observável (entrada → saída/efeito), não detalhes internos de implementação.

## Isolamento
- Testes unitários não tocam rede, disco real, planilhas remotas ou banco de produção. Use fixtures, dados sintéticos ou mocks.
- Sem estado compartilhado entre testes: cada um monta e derruba o que precisa (fixtures do pytest).
- Nada de credenciais reais em teste — use valores fake e variáveis de ambiente de teste.

## Antes de dar um caso por concluído
- Rode a suíte e confirme verde. Não marque tarefa como pronta com teste vermelho ou implementação parcial.
