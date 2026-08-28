-- Schema do dashboard de biblioteca de jogos no Supabase (Postgres).
-- Rode manualmente no SQL editor do Supabase (Project > SQL Editor > New
-- query). Idempotente (CREATE TABLE IF NOT EXISTS), pode rodar mais de uma
-- vez sem efeito colateral — mesmo espírito do schema SQLite anterior
-- (ver .claude/rules/sql-architecture.md).
--
-- Biblioteca por usuário: games/sync_runs/settings carregam user_id,
-- referenciando auth.users. O servidor sempre lê/escreve com a
-- service_role key (que ignora RLS) filtrando por user_id na aplicação;
-- as políticas abaixo definem o que aconteceria se a anon key algum dia
-- for usada direto (nunca é, neste desenho) — defesa em profundidade.
--
-- Migração de instalação anterior (sem user_id, vitrine compartilhada):
-- os blocos `do $$ ... $$` abaixo só disparam se a tabela já existir sem a
-- coluna `user_id` — nesse caso as linhas antigas não têm dono válido e são
-- descartadas (TRUNCATE) antes da coluna virar NOT NULL. Em instalação nova
-- (CREATE TABLE cria a tabela já com user_id) os blocos são no-op.

create table if not exists games (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    platform text not null,
    external_id text not null,
    name text not null,
    name_sort text generated always as (lower(name)) stored,
    cover_url text,
    playtime_minutes integer,
    last_played_at timestamptz,
    achievements_unlocked integer,
    achievements_total integer,
    completion_status text not null default 'unknown',
    added_at date,
    raw_json jsonb not null default '{}'::jsonb,
    first_synced_at timestamptz not null default now(),
    last_synced_at timestamptz not null default now(),
    unique (user_id, platform, external_id)
);

do $$
begin
    if not exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'games' and column_name = 'user_id'
    ) then
        truncate table games cascade;
        alter table games add column user_id uuid references auth.users(id) on delete cascade;
        alter table games alter column user_id set not null;
        alter table games drop constraint if exists games_platform_external_id_key;
        alter table games
            add constraint games_user_id_platform_external_id_key
            unique (user_id, platform, external_id);
    end if;
end $$;

create index if not exists idx_games_user_id on games(user_id);
create index if not exists idx_games_platform on games(platform);
create index if not exists idx_games_completion_status on games(completion_status);
create index if not exists idx_games_name_sort on games(name_sort);

create table if not exists game_metadata (
    game_id bigint primary key references games(id) on delete cascade,
    release_date text,
    genres jsonb not null default '[]'::jsonb,
    rating real,
    metacritic integer,
    description text,
    screenshots jsonb not null default '[]'::jsonb,
    fetched_at timestamptz not null default now()
);

create table if not exists sync_runs (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    platform text not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    status text not null,
    games_found integer,
    error_message text
);

do $$
begin
    if not exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'sync_runs' and column_name = 'user_id'
    ) then
        truncate table sync_runs;
        alter table sync_runs add column user_id uuid references auth.users(id) on delete cascade;
        alter table sync_runs alter column user_id set not null;
    end if;
end $$;

create index if not exists idx_sync_runs_user_id on sync_runs(user_id);
create index if not exists idx_sync_runs_platform on sync_runs(platform);

-- Configurações dinâmicas (substitui parte do .env): credenciais de
-- plataforma (Steam/PSN/Xbox) por usuário. `value` é o texto cifrado
-- (Fernet) quando `encrypted = true`, guardado como está.
create table if not exists settings (
    user_id uuid not null references auth.users(id) on delete cascade,
    key text not null,
    value text,
    encrypted boolean not null default false,
    updated_at timestamptz not null default now(),
    updated_by text,
    primary key (user_id, key)
);

do $$
begin
    if not exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'settings' and column_name = 'user_id'
    ) then
        truncate table settings;
        alter table settings drop constraint if exists settings_pkey;
        alter table settings add column user_id uuid references auth.users(id) on delete cascade;
        alter table settings alter column user_id set not null;
        alter table settings add constraint settings_pkey primary key (user_id, key);
    end if;
end $$;

alter table games enable row level security;
alter table game_metadata enable row level security;
alter table sync_runs enable row level security;
alter table settings enable row level security;

-- Leitura restrita ao dono da linha; escrita nunca via anon/authenticated —
-- só a service_role (usada exclusivamente pelo servidor) grava, e ela
-- ignora RLS por padrão.
drop policy if exists authenticated_select_games on games;
create policy authenticated_select_games on games
    for select to authenticated using (auth.uid() = user_id);

-- game_metadata não tem user_id próprio: a posse é a do game_id que ela
-- descreve.
drop policy if exists authenticated_select_game_metadata on game_metadata;
create policy authenticated_select_game_metadata on game_metadata
    for select to authenticated using (
        exists (
            select 1 from games
            where games.id = game_metadata.game_id
            and games.user_id = auth.uid()
        )
    );

drop policy if exists authenticated_select_sync_runs on sync_runs;
create policy authenticated_select_sync_runs on sync_runs
    for select to authenticated using (auth.uid() = user_id);

-- `settings` não tem nenhuma política (nem select): só service_role toca
-- nela, mesmo com valores já cifrados dentro.
