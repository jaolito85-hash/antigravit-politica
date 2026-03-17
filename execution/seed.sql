-- Node Data Política — Seed SQL
-- Execute this in your Supabase SQL editor

-- Drop tables if they exist (clean slate)
drop table if exists feedbacks cascade;
drop table if exists config cascade;

-- FEEDBACKS TABLE
create table feedbacks (
    id bigint generated always as identity primary key,
    sender text,
    name text,
    message text,
    timestamp text,
    category text,
    region text,
    urgency text,
    sentiment text,
    topic text,
    status text default 'aberto',
    resolved_at text,
    created_at timestamp with time zone default now()
);

-- CONFIG TABLE (categories and regions)
create table config (
    id bigint generated always as identity primary key,
    type text not null,  -- 'category' or 'region'
    name text not null,
    color text,
    created_at timestamp with time zone default now()
);

-- Enable Row Level Security
alter table feedbacks enable row level security;
alter table config enable row level security;

-- Public policies (demo mode - adjust for production)
create policy "Public read feedbacks" on feedbacks for select using (true);
create policy "Public insert feedbacks" on feedbacks for insert with check (true);
create policy "Public update feedbacks" on feedbacks for update using (true);
create policy "Public delete feedbacks" on feedbacks for delete using (true);

create policy "Public read config" on config for select using (true);
create policy "Public insert config" on config for insert with check (true);
create policy "Public update config" on config for update using (true);
create policy "Public delete config" on config for delete using (true);

-- SEED CATEGORIES (political focus)
insert into config (type, name, color) values
    ('category', 'Propostas & Projetos', '#1a3a6b'),
    ('category', 'Infraestrutura & Obras', '#f59e0b'),
    ('category', 'Saúde & Educação', '#ec4899'),
    ('category', 'Segurança Pública', '#ef4444'),
    ('category', 'Transporte & Mobilidade', '#3b82f6'),
    ('category', 'Meio Ambiente', '#22c55e'),
    ('category', 'Desenvolvimento Econômico', '#84cc16'),
    ('category', 'Assistência Social', '#f97316');

-- SEED REGIONS
insert into config (type, name, color) values
    ('region', 'Centro', null),
    ('region', 'Zona Norte', null),
    ('region', 'Zona Sul', null),
    ('region', 'Zona Leste', null),
    ('region', 'Zona Oeste', null),
    ('region', 'Distrito Industrial', null),
    ('region', 'Zona Rural', null);
