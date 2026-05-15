-- =============================================================================
-- Migration: usuarios_painel
-- Tabela de credenciais do painel administrativo (login + 2FA TOTP).
-- Senhas armazenadas como hash bcrypt (cost 12). Segredo TOTP em base32.
--
-- Acesso: somente via service_role (backend Flask). RLS bloqueia tudo
-- por padrão para impedir leitura via anon key, mesmo se exposta.
-- =============================================================================

CREATE TABLE IF NOT EXISTS usuarios_painel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operador' CHECK (role IN ('admin', 'operador')),
    totp_secret TEXT,
    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_painel_username ON usuarios_painel (lower(username));

-- RLS: bloqueia acesso via chaves anon/authenticated.
-- Service_role bypassa RLS automaticamente — backend continua funcionando.
ALTER TABLE usuarios_painel ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "deny_all_anon_access" ON usuarios_painel;
CREATE POLICY "deny_all_anon_access" ON usuarios_painel
    FOR ALL
    TO anon, authenticated
    USING (false)
    WITH CHECK (false);

-- Trigger para manter updated_at atualizado
CREATE OR REPLACE FUNCTION usuarios_painel_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_usuarios_painel_updated_at ON usuarios_painel;
CREATE TRIGGER trg_usuarios_painel_updated_at
    BEFORE UPDATE ON usuarios_painel
    FOR EACH ROW
    EXECUTE FUNCTION usuarios_painel_set_updated_at();
