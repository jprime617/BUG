# Checklist de deploy — Vercel + Supabase

Passo a passo pra publicar o sistema. Os passos 1–3 são manuais, fora do
alcance de qualquer automação — precisam da sua conta no Supabase/Vercel.

## 1. Criar o projeto no Supabase

1. Crie um projeto em https://supabase.com (grátis).
2. Em **Project Settings > API**, anote:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_ANON_KEY`
   - **service_role key** (⚠️ secreta) → `SUPABASE_SERVICE_ROLE_KEY`

## 2. Rodar o schema

1. No painel do Supabase, abra **SQL Editor > New query**.
2. Cole o conteúdo de `supabase/schema.sql` e rode.
   - Projeto novo: cria as tabelas do zero.
   - Projeto que já rodou uma versão anterior do schema (sem `user_id`,
     modelo de vitrine compartilhada): o script detecta isso e migra
     sozinho — **apaga as linhas existentes de `games`/`sync_runs`/
     `settings`** (não têm dono válido pra atribuir) antes de tornar
     `user_id` obrigatório. Se tinha chaves de Steam/PSN/Xbox configuradas,
     recadastre em `/configuracoes` depois do deploy.
3. Confirme em **Table Editor** que `games`, `game_metadata`, `sync_runs` e
   `settings` existem, com RLS marcado como ativo (ícone de cadeado).

## 3. Gerar a chave de criptografia

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guarde o valor — vai em `SETTINGS_ENCRYPTION_KEY` no passo 4. Se essa chave
se perder depois, qualquer valor já cifrado na tabela `settings` fica
irrecuperável (seria preciso reconfigurar tudo em `/configuracoes`).

## 4. Configurar variáveis de ambiente na Vercel

Em **Project Settings > Environment Variables**, adicione:

| Variável | Valor |
|---|---|
| `SUPABASE_URL` | do passo 1 |
| `SUPABASE_ANON_KEY` | do passo 1 |
| `SUPABASE_SERVICE_ROLE_KEY` | do passo 1 (secreta) |
| `SETTINGS_ENCRYPTION_KEY` | do passo 3 |
| `RAWG_API_KEY` | opcional — só habilita sinopse/nota/galeria dos jogos (ver `docs/CREDENTIALS.md`) |

Nenhuma outra variável é necessária pra publicar — cada cliente configura
Steam/PSN/Xbox da própria conta depois, pela tela `/configuracoes`.

## 5. Conectar o repositório e fazer deploy

1. Importe o repositório na Vercel (New Project > escolha o repo).
2. A Vercel detecta `vercel.json`/`requirements.txt` automaticamente — não
   precisa configurar build command.
3. Deploy.

## 6. Primeiro acesso

1. Abra a URL publicada, vá em `/registro` e crie sua conta. `/registro`
   fica público de propósito — é assim que cada cliente entra e ganha sua
   própria biblioteca (isolada por `user_id`, ver `supabase/schema.sql`).
2. Faça login e vá em `/configuracoes` para inserir suas credenciais de
   Steam/PSN/Xbox (opcional, uma por vez).

## 7. Testar

- [ ] Criar uma segunda conta em `/registro` (email diferente) e confirmar
      que ela começa com biblioteca vazia — não vê os jogos da primeira.
- [ ] `/configuracoes` → preencher `STEAM_API_KEY`/`STEAM_ID64` (ou
      PSN/Xbox) → "Testar conexão" → OK.
- [ ] Salvar e reabrir `/configuracoes` — o campo aparece como "configurado"
      (mascarado), não em texto puro.
- [ ] Clicar "Sincronizar" na home — a plataforma configurada roda
      normalmente.
- [ ] Se `RAWG_API_KEY` estiver configurada na Vercel, abrir um jogo
      qualquer e confirmar que sinopse/nota Metacritic/galeria carregam.
- [ ] Deslogar (botão "Sair" na barra superior) e confirmar que qualquer
      página redireciona pra `/login`.
