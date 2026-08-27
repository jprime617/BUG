-- Schema do dashboard de biblioteca de jogos no Supabase (Postgres).
-- Rode manualmente no SQL editor do Supabase (Project > SQL Editor > New
-- query). Idempotente (CREATE TABLE IF NOT EXISTS), pode rodar mais de uma
-- vez sem efeito colateral — mesmo espírito do schema SQLite anterior
-- (ver .claude/rules/sql-architecture.md).
--
-- Vitrine compartilhada: não há biblioteca por usuário, então games/
-- game_metadata/sync_runs não têm user_id. RLS é ativado mesmo assim como
-- defesa em profundidade — o servidor sempre lê/escreve com a service_role
-- key (que ignora RLS); as políticas abaixo só definem o que aconteceria
-- se a anon key algum dia for usada direto (nunca é, neste desenho).

create table if not exists games (
    id bigint generated always as identity primary key,
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
    unique (platform, external_id)
);
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
    platform text not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    status text not null,
    games_found integer,
    error_message text
);
create index if not exists idx_sync_runs_platform on sync_runs(platform);

-- Configurações dinâmicas (substitui parte do .env): chaves de API de
-- terceiros usadas pela aplicação. `value` é o texto cifrado (Fernet) quando
-- `encrypted = true`, guardado como está.
create table if not exists settings (
    key text primary key,
    value text,
    encrypted boolean not null default false,
    updated_at timestamptz not null default now(),
    updated_by text
);

alter table games enable row level security;
alter table game_metadata enable row level security;
alter table sync_runs enable row level security;
alter table settings enable row level security;

-- Leitura liberada pra qualquer usuário autenticado (é uma vitrine
-- compartilhada); escrita nunca via anon/authenticated — só a service_role
-- (usada exclusivamente pelo servidor) grava, e ela ignora RLS por padrão.
drop policy if exists authenticated_select_games on games;
create policy authenticated_select_games on games
    for select to authenticated using (true);

drop policy if exists authenticated_select_game_metadata on game_metadata;
create policy authenticated_select_game_metadata on game_metadata
    for select to authenticated using (true);

drop policy if exists authenticated_select_sync_runs on sync_runs;
create policy authenticated_select_sync_runs on sync_runs
    for select to authenticated using (true);

-- `settings` não tem nenhuma política (nem select): só service_role toca
-- nela, mesmo com valores já cifrados dentro.
