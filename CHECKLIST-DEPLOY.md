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
| `ADMIN_EMAIL` | o email com que você vai se cadastrar no passo 6 |

Nenhuma outra variável é necessária pra publicar — Steam/PSN/Xbox/RAWG se
configuram depois, pela tela `/configuracoes`.

## 5. Conectar o repositório e fazer deploy

1. Importe o repositório na Vercel (New Project > escolha o repo).
2. A Vercel detecta `vercel.json`/`requirements.txt` automaticamente — não
   precisa configurar build command.
3. Deploy.

## 6. Primeiro acesso

1. Abra a URL publicada, vá em `/registro` e crie sua conta com o mesmo
   email de `ADMIN_EMAIL` (passo 4).
2. Faça login — você deve ver `/configuracoes` acessível (ícone/rota
   restrita ao admin).
3. **No painel do Supabase, em Authentication > Settings, desative "Allow
   new users to sign up".** Sem isso, `/registro` continua público e
   qualquer pessoa que o encontrar ganha acesso de leitura à sua biblioteca
   inteira (não há biblioteca por usuário — é uma vitrine compartilhada).

## 7. Testar

- [ ] `/configuracoes` → preencher `RAWG_API_KEY` → "Testar conexão" → OK.
- [ ] Salvar e reabrir `/configuracoes` — o campo aparece como "configurado"
      (mascarado), não em texto puro.
- [ ] Abrir um jogo qualquer e confirmar que sinopse/nota Metacritic/galeria
      carregam (prova que a chave salva está sendo lida de volta).
- [ ] Clicar "Sincronizar" — Steam/PSN/Xbox (se configurados em
      `/configuracoes`) rodam normalmente; Epic aparece como "pulado", sem
      erro (esperado — ver `docs/CREDENTIALS.md`).
- [ ] Deslogar e confirmar que qualquer página redireciona pra `/login`.
- [ ] Confirmar que `/registro` está bloqueado (passo 6.3) — tentar criar uma
      segunda conta deve falhar.
