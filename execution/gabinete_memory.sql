-- Memória de conversa do Chefe de Gabinete Digital — um registro por JID.
-- TTL lógico de 30 minutos é aplicado pelo gabinete_agent.py, não pelo Postgres.
-- Instalar: abra o SQL Editor do Supabase, cole este conteúdo e execute.

create table if not exists public.gabinete_memory (
    jid         text primary key,
    messages    jsonb       not null default '[]'::jsonb,
    updated_at  timestamptz not null default now()
);

create index if not exists gabinete_memory_updated_idx
    on public.gabinete_memory (updated_at);

-- Somente a service_role (usada pelo backend) lê/escreve.
-- Sem policies: anon/authenticated ficam bloqueados pela RLS por padrão.
alter table public.gabinete_memory enable row level security;
