# DIRETRIZES: BASH, CLI E NAVEGAÇÃO DE DIRETÓRIOS

## Navegação de Caminhos (Paths)
- Caminhos relativos obrigatórios: ao estruturar sequências de comandos no terminal (especialmente `cd`) ou ao executar scripts bash/executáveis, utilize caminhos relativos em vez de caminhos absolutos do Windows ou Linux.
- Por quê: garante que scripts, pipelines de automação e o terminal funcionem de forma fluida entre Windows, WSL ou bash nativo, evitando quebras por letras de unidade (`C:\`) ou barras incompatíveis.
- Estruture sempre as chamadas assumindo a raiz do projeto como ponto de partida (ex: `./src/utils/script.sh` ou `cd ../agents`).

## Limpeza
- Após compilações ou execuções geradoras de cache, use `make clean` para não poluir o contexto de tokens da IDE.
