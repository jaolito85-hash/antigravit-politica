-- Operacao Local — cabos eleitorais e coordenadores via WhatsApp.
-- Instalar: SQL Editor do Supabase, cola e roda. Idempotente.

create table if not exists public.operadores_campo (
    id             bigserial primary key,
    nome           text not null,
    telefone       text not null,
    jid            text,
    funcao         text not null default 'Operador de campo',
    cidade_base    text,
    regiao         text,
    status         text not null default 'ativo', -- 'ativo' | 'pausado'
    notas          text,
    criado_em      timestamptz not null default now(),
    atualizado_em  timestamptz not null default now()
);

create unique index if not exists operadores_campo_telefone_uidx
    on public.operadores_campo (telefone);

create index if not exists operadores_campo_status_idx
    on public.operadores_campo (status, cidade_base);

alter table public.operadores_campo enable row level security;
-- Sem policies publicas — service_role le/escreve pelo backend.


create table if not exists public.operacao_local_atualizacoes (
    id                  bigserial primary key,
    operador_id          bigint references public.operadores_campo(id) on delete set null,
    operador_nome        text,
    operador_jid         text,
    cidade               text not null,
    regiao               text,
    tipo                 text not null default 'relato',
    tema_principal       text,
    resumo               text,
    quantidade_pessoas   integer,
    liderancas           text,
    sentimento           text not null default 'neutro', -- 'positivo' | 'neutro' | 'atencao'
    proxima_acao         text,
    mensagem_original    text,
    origem               text not null default 'whatsapp', -- 'whatsapp' | 'manual'
    criada_em            timestamptz not null default now()
);

create index if not exists operacao_local_cidade_idx
    on public.operacao_local_atualizacoes (cidade, criada_em desc);

create index if not exists operacao_local_operador_idx
    on public.operacao_local_atualizacoes (operador_id, criada_em desc);

create index if not exists operacao_local_sentimento_idx
    on public.operacao_local_atualizacoes (sentimento, criada_em desc);

alter table public.operacao_local_atualizacoes enable row level security;
-- Sem policies publicas — service_role le/escreve pelo backend.


create table if not exists public.operacao_local_mensagens (
    id                bigserial primary key,
    atualizacao_id    bigint references public.operacao_local_atualizacoes(id) on delete set null,
    destinatario_jid  text not null,
    destinatario_nome text,
    cidade            text,
    direcao           text not null default 'enviada', -- 'enviada' | 'recebida'
    canal             text not null default 'whatsapp',
    texto             text not null,
    autor             text,
    enviada_em        timestamptz not null default now()
);

create index if not exists operacao_local_mensagens_atualizacao_idx
    on public.operacao_local_mensagens (atualizacao_id, enviada_em desc);

create index if not exists operacao_local_mensagens_data_idx
    on public.operacao_local_mensagens (enviada_em desc);

alter table public.operacao_local_mensagens enable row level security;
-- Sem policies publicas — service_role le/escreve pelo backend.
