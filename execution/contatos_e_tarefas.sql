-- Gabinete Digital — Killer Scene
-- Duas tabelas que alimentam o fluxo "Deputado manda áudio -> bot envia email + cria tarefa".
-- Instalar: SQL Editor do Supabase, cola e roda. Idempotente.

-- =============================================================================
-- 1. CONTATOS — a "agenda" que o bot consulta pra saber pra quem mandar email.
-- =============================================================================
create table if not exists public.contatos_gabinete (
    id          bigserial primary key,
    nome        text not null,
    email       text,
    papel       text,            -- ex.: "Assessor", "Secretário de Saúde"
    telefone    text,
    notas       text,
    criado_em   timestamptz not null default now()
);

-- Busca case-insensitive por nome.
create index if not exists contatos_gabinete_nome_lower_idx
    on public.contatos_gabinete (lower(nome));

alter table public.contatos_gabinete enable row level security;
-- Sem policies públicas — só service_role lê/escreve (usado pelo backend).


-- =============================================================================
-- 2. TAREFAS — backlog do gabinete. Aparece no dashboard e recebe updates.
-- =============================================================================
create table if not exists public.tarefas_gabinete (
    id                      bigserial primary key,
    titulo                  text not null,
    responsavel             text,                                       -- snapshot do nome no momento da criação
    responsavel_contato_id  bigint references public.contatos_gabinete(id) on delete set null,
    deadline                date,
    detalhes                text,
    status                  text not null default 'aberta',             -- 'aberta' | 'em_andamento' | 'concluida'
    origem                  text not null default 'gabinete_digital',   -- quem criou (voz, manual, api)
    criada_por_jid          text,                                       -- JID do deputado/autor
    criada_em               timestamptz not null default now(),
    atualizada_em           timestamptz not null default now()
);

create index if not exists tarefas_gabinete_status_idx on public.tarefas_gabinete (status, deadline);
create index if not exists tarefas_gabinete_criada_em_idx on public.tarefas_gabinete (criada_em desc);

alter table public.tarefas_gabinete enable row level security;
-- Sem policies públicas — service_role manda.


-- =============================================================================
-- 3. SEED — contatos mínimos pra demo funcionar no primeiro teste.
-- Troque os emails pelos reais antes da apresentação se quiser disparos de verdade.
-- =============================================================================
insert into public.contatos_gabinete (nome, email, papel, notas)
values
    ('Pedro Machado',    'pedro@gabinete.exemplo.com',     'Chefe de Assessoria',           'Coordena agenda de visitas do Deputado em cidades-chave.'),
    ('Maria Gomes',      'maria.saude@gabinete.exemplo.com','Secretária de Saúde (MG)',     'Interlocutora oficial para pautas de saúde.'),
    ('Carlos Andrade',   'carlos@gabinete.exemplo.com',    'Assessor de Imprensa',          'Responsável por notas oficiais e respostas de mídia.')
on conflict do nothing;
