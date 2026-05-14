-- ============================================================
-- Migration: classificação RELATIVA ao candidato (alinhamento)
-- ============================================================
-- Adiciona colunas para classificar comentários considerando o contexto
-- adversário. Exemplo: "FLAVIO BOLSONARO PRESIDENTE!" no perfil do Pedro
-- Rousseff agora será pro_adversario / Negativo (antes era Positivo).
--
-- Idempotente (IF NOT EXISTS). Pode rodar várias vezes sem efeito colateral.
-- ============================================================

ALTER TABLE comentarios_politicos
    ADD COLUMN IF NOT EXISTS alinhamento TEXT DEFAULT 'neutro',
    ADD COLUMN IF NOT EXISTS adversario_mencionado TEXT,
    ADD COLUMN IF NOT EXISTS nivel_hostilidade SMALLINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sentimento_absoluto TEXT;

-- Valores válidos para alinhamento (documentação — não enforce):
--   pro_candidato     — apoia o candidato-cliente
--   anti_candidato    — critica o candidato-cliente
--   pro_adversario    — promove adversário no perfil do cliente (RISCO)
--   anti_adversario   — critica adversário (aliado tático do cliente)
--   neutro            — sem alinhamento político claro
--   spam              — propaganda, scam, off-topic não-político
--   off_topic         — assunto não relacionado à política

-- Índice opcional para acelerar agregação por alinhamento
CREATE INDEX IF NOT EXISTS idx_comentarios_alinhamento
    ON comentarios_politicos(alinhamento);

CREATE INDEX IF NOT EXISTS idx_comentarios_adversario_mencionado
    ON comentarios_politicos(adversario_mencionado)
    WHERE adversario_mencionado IS NOT NULL;

-- Verificação rápida (rode após o ALTER):
-- SELECT alinhamento, COUNT(*) FROM comentarios_politicos GROUP BY alinhamento;
