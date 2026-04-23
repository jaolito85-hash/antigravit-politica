-- Tokens OAuth do Google Calendar.
-- Guardados apenas pelo backend via service_role.
-- Instalar: SQL Editor do Supabase.

create table if not exists public.integracao_google_tokens (
    id             bigserial primary key,
    escopo         text not null default 'calendar', -- 'calendar' | 'gmail' | ...
    email          text,
    refresh_token  text not null,
    access_token   text,
    token_expiry   timestamptz,
    scopes         text,
    atualizado_em  timestamptz not null default now(),
    criado_em      timestamptz not null default now()
);

create unique index if not exists integracao_google_tokens_escopo_uidx
    on public.integracao_google_tokens (escopo);

alter table public.integracao_google_tokens enable row level security;
-- Sem policies publicas — apenas service_role le/escreve pelo backend.
