# DIRETRIZES: SQL E MODELAGEM DE BANCO DE DADOS

- Nomenclatura: utilize `snake_case` para tabelas e colunas. Nomes no plural para tabelas (ex: `usuarios`, `vendas`).
- Performance: sempre adicione índices em colunas utilizadas em cláusulas `WHERE`, `JOIN` ou chaves estrangeiras.
- Idempotência: scripts de criação devem utilizar `CREATE TABLE IF NOT EXISTS` ou `CREATE OR REPLACE VIEW`.
