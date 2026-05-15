"""
Cria ou reseta um usuário do painel administrativo.

Uso:
    python execution/criar_usuario_painel.py --username admin --role admin
    python execution/criar_usuario_painel.py --username maria --role operador --senha MinhaSenha123
    python execution/criar_usuario_painel.py --username admin --reset-2fa

Se --senha não for passada, gera uma senha aleatória forte (24 chars) e mostra UMA vez.
Salve essa senha imediatamente em um gerenciador de senhas — não é possível recuperar depois.

A senha é armazenada como hash bcrypt (cost 12). 2FA não vem ativado — o usuário
ativa no primeiro login acessando /setup-2fa automaticamente.
"""

import argparse
import os
import secrets
import string
import sys
from datetime import datetime, timezone

import bcrypt
from dotenv import load_dotenv

# Carrega .env do diretório raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ SUPABASE_URL e SUPABASE_SERVICE_KEY precisam estar no .env")
    sys.exit(1)

from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def gerar_senha_forte(tamanho: int = 24) -> str:
    """Senha com letras maiúsculas, minúsculas, dígitos e símbolos seguros."""
    alfabeto = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


def hash_bcrypt(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def buscar_usuario(username: str):
    resp = (
        supabase.table("usuarios_painel")
        .select("id, username, role, totp_enabled")
        .ilike("username", username)
        .limit(1)
        .execute()
    )
    rows = getattr(resp, "data", None) or []
    return rows[0] if rows else None


def main():
    parser = argparse.ArgumentParser(description="Cria/reseta usuário do painel.")
    parser.add_argument("--username", required=True, help="Nome de usuário (único, case-insensitive)")
    parser.add_argument("--role", choices=["admin", "operador"], default="operador")
    parser.add_argument("--senha", default=None, help="Senha em claro (se omitido, gera uma forte)")
    parser.add_argument("--reset-2fa", action="store_true", help="Apaga o segredo TOTP — usuário precisará reconfigurar no próximo login")
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        print("❌ Username vazio.")
        sys.exit(1)

    existente = buscar_usuario(username)

    # Caso especial: --reset-2fa sozinho (mantém senha)
    if args.reset_2fa and not args.senha and existente:
        supabase.table("usuarios_painel").update({
            "totp_secret": None,
            "totp_enabled": False,
        }).eq("id", existente["id"]).execute()
        print(f"✅ 2FA resetado para '{username}'. No próximo login ele precisará reconfigurar.")
        return

    senha = args.senha or gerar_senha_forte()
    senha_gerada = args.senha is None
    password_hash = hash_bcrypt(senha)

    payload = {
        "username": username,
        "password_hash": password_hash,
        "role": args.role,
        "failed_attempts": 0,
        "locked_until": None,
    }
    if args.reset_2fa:
        payload["totp_secret"] = None
        payload["totp_enabled"] = False

    if existente:
        supabase.table("usuarios_painel").update(payload).eq("id", existente["id"]).execute()
        acao = "atualizado"
    else:
        payload["totp_enabled"] = False
        supabase.table("usuarios_painel").insert(payload).execute()
        acao = "criado"

    print(f"✅ Usuário '{username}' {acao} com sucesso (role={args.role}).")
    if senha_gerada:
        print()
        print("=" * 60)
        print("  SENHA GERADA — copie agora, não será mostrada de novo:")
        print()
        print(f"  {senha}")
        print()
        print("=" * 60)
        print()
    print("Próximo passo: faça login em /login — o sistema vai te pedir para")
    print("configurar o 2FA com Google Authenticator/Authy antes de liberar o painel.")


if __name__ == "__main__":
    main()
