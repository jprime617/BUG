# Credenciais por plataforma

**No sistema publicado (Vercel), Steam/PSN/Xbox são credenciais por
usuário: cada cliente preenche as suas em `/configuracoes` (logado com sua
própria conta) — nunca em `.env`.** `RAWG_API_KEY` é a exceção: é uma
credencial global, configurada só na Vercel (Project Settings > Environment
Variables), não pela tela. O `.env` real só existe pra rodar localmente
(`python tasks.py serve`); veja `env.example` pros nomes exatos. Independente
de onde a credencial foi configurada, cada plataforma continua opcional —
sem ela, a sincronização pula aquela plataforma automaticamente (não é erro).

## Steam (API oficial)

1. `STEAM_API_KEY`: gere em https://steamcommunity.com/dev/apikey (precisa de
   um perfil Steam com nível de proteção familiar configurado; use o domínio
   do seu site pessoal ou `localhost` se não tiver um).
2. `STEAM_ID64`: seu SteamID de 64 bits. Descubra em https://steamid.io
   colando a URL do seu perfil.
3. O perfil (ou pelo menos "detalhes do jogo") precisa estar público, ou a
   API retorna biblioteca vazia.

## PlayStation Network (não-oficial, via `PSNAWP`)

1. Faça login em https://www.playstation.com no navegador.
2. Acesse https://ca.account.sony.com/api/v1/ssocookie (mesma sessão logada)
   e copie o valor do campo `npsso`.
3. Cole em `PSN_NPSSO`. O token expira em ~2 meses — repita o processo quando
   a sincronização começar a falhar com erro de autenticação.
4. Seu perfil de troféus precisa estar público (Configurações > Privacidade),
   senão `trophy_titles` retorna vazio/erro.

## Xbox (não-oficial, via OpenXBL/xbl.io)

1. Acesse https://xbl.io e faça login com sua conta Microsoft/Xbox Live.
2. Gere uma API key no painel (tier grátis: 150 requisições/hora).
3. Cole em `XBOX_OPENXBL_KEY`.
4. Tempo jogado (`MinutesPlayed`) nem todo jogo publica na Xbox Live — jogos
   mais antigos ou de terceiros costumam não ter esse stat, mesmo com a
   conta e a chave certas. Quando isso acontece, o jogo aparece na
   biblioteca normalmente, só sem o tempo jogado (mostrado como "—").

## RAWG (sinopse, nota Metacritic e galeria no detalhe do jogo)

1. Cadastro grátis em https://rawg.io/signup (sem cartão).
2. Pegue a chave em https://rawg.io/apidocs.
3. Cole em `RAWG_API_KEY` (variável de ambiente global, ver acima). Sem ela,
   a página de detalhe do jogo mostra um erro amigável no lugar da sinopse —
   a biblioteca em si funciona normalmente.
