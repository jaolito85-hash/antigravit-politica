-- ============================================================
-- Migration: adiciona campos de prioridade do operador
-- Tabela: operadores_campo
-- Contexto: Operação Local — score de prioridade do operador
-- Fórmula: score = (influencia × 10) + (peso_funcao × 10) + (votos_cidade ÷ 1000)
-- Faixas:  ≥100 máxima · 60-99 alta · 30-59 média · <30 normal
-- ============================================================

-- 1) Novas colunas (idempotente)
ALTER TABLE operadores_campo
    ADD COLUMN IF NOT EXISTS funcao_chave  TEXT,
    ADD COLUMN IF NOT EXISTS especificacao TEXT,
    ADD COLUMN IF NOT EXISTS influencia    SMALLINT DEFAULT 1,
    ADD COLUMN IF NOT EXISTS votos_cidade  INTEGER  DEFAULT 0,
    ADD COLUMN IF NOT EXISTS score         NUMERIC(8,2) DEFAULT 0;

-- 2) Constraints de sanidade
ALTER TABLE operadores_campo
    DROP CONSTRAINT IF EXISTS operadores_campo_influencia_check;
ALTER TABLE operadores_campo
    ADD CONSTRAINT operadores_campo_influencia_check
    CHECK (influencia BETWEEN 1 AND 10);

ALTER TABLE operadores_campo
    DROP CONSTRAINT IF EXISTS operadores_campo_votos_cidade_check;
ALTER TABLE operadores_campo
    ADD CONSTRAINT operadores_campo_votos_cidade_check
    CHECK (votos_cidade >= 0);

ALTER TABLE operadores_campo
    DROP CONSTRAINT IF EXISTS operadores_campo_funcao_chave_check;
ALTER TABLE operadores_campo
    ADD CONSTRAINT operadores_campo_funcao_chave_check
    CHECK (
        funcao_chave IS NULL OR funcao_chave IN (
            'prefeito', 'vice-prefeito', 'vereador', 'secretario',
            'lideranca-comunitaria', 'cabo-eleitoral', 'influenciador', 'voluntario'
        )
    );

-- 3) Backfill: inferir funcao_chave a partir do campo livre `funcao`
UPDATE operadores_campo
SET funcao_chave = CASE
    WHEN LOWER(funcao) LIKE '%vice%'         THEN 'vice-prefeito'
    WHEN LOWER(funcao) LIKE '%prefeit%'      THEN 'prefeito'
    WHEN LOWER(funcao) LIKE '%vereador%'     THEN 'vereador'
    WHEN LOWER(funcao) LIKE '%secret%'       THEN 'secretario'
    WHEN LOWER(funcao) LIKE '%lideran%'      THEN 'lideranca-comunitaria'
    WHEN LOWER(funcao) LIKE '%cabo%'         THEN 'cabo-eleitoral'
    WHEN LOWER(funcao) LIKE '%influenc%'     THEN 'influenciador'
    WHEN LOWER(funcao) LIKE '%volunt%'       THEN 'voluntario'
    ELSE 'voluntario'
END
WHERE funcao_chave IS NULL;

-- 4) Recalcula score para registros legados
UPDATE operadores_campo
SET score = ROUND(
    (
        COALESCE(influencia, 1) * 10
      + CASE funcao_chave
            WHEN 'prefeito'              THEN 100
            WHEN 'vice-prefeito'         THEN  90
            WHEN 'vereador'              THEN  80
            WHEN 'secretario'            THEN  70
            WHEN 'lideranca-comunitaria' THEN  60
            WHEN 'cabo-eleitoral'        THEN  50
            WHEN 'influenciador'         THEN  40
            ELSE                              30
        END
      + COALESCE(votos_cidade, 0) / 1000.0
    )::numeric, 2
);

-- 5) Índice para ordenação por prioridade
CREATE INDEX IF NOT EXISTS operadores_campo_score_idx
    ON operadores_campo (score DESC);

-- 6) Verificação (opcional, remova antes de aplicar em produção)
-- SELECT nome, funcao, funcao_chave, influencia, votos_cidade, score
-- FROM operadores_campo
-- ORDER BY score DESC NULLS LAST
-- LIMIT 20;
