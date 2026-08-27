# Credenciais por plataforma

**No sistema publicado (Vercel), as credenciais abaixo se preenchem pela
tela `/configuracoes` (restrita ao admin) — não em `.env`.** O `.env` real
só existe pra rodar localmente (`python tasks.py serve`); veja `env.example`
pros nomes exatos, marcados como "fallback local". Independente de onde a
credencial foi configurada, cada plataforma continua opcional — sem ela, a
sincronização pula aquela plataforma automaticamente (não é erro).

**Epic Games não tem versão hospedada.** A sincronização depende do CLI
`legendary` instalado e autenticado interativamente na máquina — isso não
roda em função serverless (sem filesystem persistente, sem sessão de
terminal). Na Vercel a plataforma Epic sempre aparece como "pulado" no
relatório de sync; pra sincronizar Epic, rode `python tasks.py sync`
localmente.

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

## Epic Games (via `legendary`)

1. Instale o `legendary` separadamente (não é dependência deste projeto):
   `pipx install legendary-gl` (ou veja
   https://github.com/derrod/legendary para outras formas de instalação).
2. Autentique uma única vez, interativamente: `legendary auth`.
3. Se o binário não estiver no PATH como `legendary`, aponte o caminho em
   `LEGENDARY_BIN`.
4. Sem playtime nem conquistas: a Epic não expõe esses dados nem para o
   próprio launcher oficial.

## Nintendo (sem API — importação manual)

Não há API pública nem não-oficial confiável para eShop/Switch. Preencha um
CSV com o formato de `templates/nintendo_import_example.csv`:

```csv
name,playtime_minutes,completion_status,added_at,cover_url
The Legend of Zelda: Tears of the Kingdom,4200,playing,2023-05-12,
```

- `name`: obrigatório.
- `playtime_minutes`, `added_at`: opcionais, deixe em branco se não souber.
- `completion_status`: um de `not_started`, `playing`, `completed`,
  `abandoned`, `unknown` (padrão se vazio).
- `cover_url`: opcional. Se vazio, o importador tenta buscar a capa
  automaticamente (só aceita se o nome bater com confiança alta):
  1. eShop americana — sem credencial, mas índice legado, sem cobertura de
     lançamentos recentes/Switch 2.
  2. RAWG (se `RAWG_API_KEY` configurada, ver abaixo) — só quando a eShop não
     achou nada.
  Pra fechar manualmente os que nenhuma das duas resolve: abra a página do
  jogo em https://www.nintendo.com/us/store/products/ e cole a URL aqui —
  `cover_url` preenchida tem prioridade sobre as duas buscas automáticas.

### RAWG (opcional, fallback de capa)

1. Cadastro grátis em https://rawg.io/signup (sem cartão).
2. Pegue a chave em https://rawg.io/apidocs.
3. Cole em `RAWG_API_KEY`. Sem ela, o importador usa só a busca da eShop.

Importe com:

```bash
python tasks.py import-nintendo caminho/para/seus_jogos.csv
```

Rodar de novo com o mesmo CSV atualiza os jogos existentes (chave é o nome
"slugificado"), não duplica.
