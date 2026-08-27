# DIRETRIZES: PYTHON, PANDAS E AGENTES DE DADOS

## Manipulação de Dados (Pandas)
- Vetorização sempre: é estritamente proibido iterar sobre linhas de DataFrames usando `for` ou `.iterrows()`. Utilize operações vetorizadas nativas do Pandas ou `.apply()`.
- Indexação limpa: mantenha os índices organizados e elimine colunas vazias ou linhas em branco antes de processamentos pesados.

## Integrações Externas
- Ao sincronizar dados de APIs ou planilhas remotas (ex: `gspread`), minimize requisições enviando pacotes em lote (batch processing).
- Isole credenciais estritamente em variáveis de ambiente — nunca em código ou arquivos versionados.

## Arquitetura de Agentes
- Desacoplamento de funções: divida as habilidades do agente em ferramentas (tools) separadas e registráveis (veja `templates/advanced_agent_core.py`).
- Tratamento de exceções: implemente paradas seguras (circuit breaker) — todo script de pipeline deve ter um bloco `try/except` que gere logs claros informando exatamente em qual etapa do fluxo a falha ocorreu.
- Logs estruturados: forneça telemetria clara (nível, timestamp, etapa) em vez de `print()` solto.
