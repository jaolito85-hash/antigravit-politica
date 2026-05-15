-- =====================================================================
-- Migration: videos_analises
-- Aba "Vídeos & Podcasts" — análise estratégica de YouTube e podcasts.
-- =====================================================================
--
-- Como rodar em STAGING (não rodar em produção sem aprovação manual):
--   psql "$SUPABASE_DB_URL" -f execution/videos_analises.sql
--
-- O acesso é feito 100% via supabase_admin (service_role) no backend.
-- RLS fica habilitado sem policies — padrão usado por tarefas_gabinete.
-- =====================================================================

create table if not exists public.videos_analises (
    id bigserial primary key,

    -- Identificação do conteúdo
    url text not null,
    plataforma text default 'youtube',     -- youtube | podcast | outro
    tipo text not null,                    -- adversario | proprio
    candidato text not null,
    contexto_extra text,                   -- texto livre opcional fornecido na submissão

    -- Metadados do vídeo (preenchidos após download)
    titulo text,
    canal text,
    thumbnail_url text,
    duracao_segundos int,
    idioma text default 'pt',

    -- Pipeline de processamento
    status text default 'queued',          -- queued|downloading|transcribing|analyzing|done|error
    progresso int default 0,
    erro text,
    iniciado_em timestamptz,
    finalizado_em timestamptz,

    -- Transcrição (texto integral + segmentos com timestamps)
    transcricao text,
    transcricao_segmentos jsonb,           -- [{start, end, text}] do Whisper verbose_json

    -- Análises IA (5 blocos retornados pelos prompts)
    resumo jsonb,                          -- {tese_central, bullets[], sentimento, tom_emocional, quotes_chave[]}
    pontos_atencao jsonb,                  -- [{id, timestamp, citacao, categoria, severidade, risco, tags[]}]
    promessas jsonb,                       -- [{id, timestamp, texto, prazo, valor_numerico, verificavel, fonte_a_checar}]
    contradicoes jsonb,                    -- [{id, trecho_a, trecho_b, natureza, explorabilidade}]
    respostas_sugeridas jsonb,             -- [{ponto_id, ponto_referencia_timestamp, contra_argumento_curto, contra_argumento_longo, tweet, story_instagram, tom, alerta_uso}]

    -- Metadados derivados (preenchidos junto com as análises)
    quotes jsonb,
    sentimento_geral text,
    tags text[] default '{}',

    -- Custo e uso
    custo_usd numeric(10,4),
    custo_breakdown jsonb,                 -- {whisper_usd, gpt_in_usd, gpt_out_usd, total_brl}
    tokens_consumidos jsonb,               -- {input, output, total}

    -- Auditoria
    criado_por text,
    criado_em timestamptz default now()
);

-- Índices
create unique index if not exists videos_analises_url_uniq
    on public.videos_analises(url);

create index if not exists videos_analises_candidato_idx
    on public.videos_analises(candidato);

create index if not exists videos_analises_status_idx
    on public.videos_analises(status)
    where status in ('queued', 'downloading', 'transcribing', 'analyzing');

create index if not exists videos_analises_criado_em_idx
    on public.videos_analises(criado_em desc);

-- RLS — habilitado sem policies (acesso via service_role apenas).
alter table public.videos_analises enable row level security;

-- =====================================================================
-- Verificação manual após apply:
--   select column_name, data_type from information_schema.columns
--    where table_name = 'videos_analises' order by ordinal_position;
-- =====================================================================
