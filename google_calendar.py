"""Integracao com Google Calendar API via OAuth 2.0.

Gerencia o fluxo de autorizacao, persistencia de refresh_token
(Supabase com fallback JSON) e criacao de eventos. O token nunca
sai do backend.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleAuthRequest


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "execution", "google_calendar_token.json")


def _client_config(redirect_uri: str) -> dict:
    """Monta o client_config no formato esperado pelo google_auth_oauthlib."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET nao configurados")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


def build_flow(redirect_uri: str, state: Optional[str] = None) -> Flow:
    """Constroi o Flow OAuth para iniciar ou completar a autorizacao."""
    flow = Flow.from_client_config(
        _client_config(redirect_uri),
        scopes=SCOPES,
        state=state,
    )
    flow.redirect_uri = redirect_uri
    return flow


def _salvar_token_supabase(supabase_admin, registro: dict) -> bool:
    if not supabase_admin:
        return False
    try:
        existentes = supabase_admin.table("integracao_google_tokens").select("id").eq("escopo", "calendar").limit(1).execute()
        if existentes.data:
            supabase_admin.table("integracao_google_tokens").update(registro).eq("id", existentes.data[0]["id"]).execute()
        else:
            supabase_admin.table("integracao_google_tokens").insert(registro).execute()
        return True
    except Exception as e:
        print(f"[calendar] Falha ao salvar token no Supabase: {e}")
        return False


def _carregar_token_supabase(supabase_admin) -> Optional[dict]:
    if not supabase_admin:
        return None
    try:
        res = supabase_admin.table("integracao_google_tokens").select("*").eq("escopo", "calendar").limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        print(f"[calendar] Falha ao ler token no Supabase: {e}")
    return None


def _salvar_token_local(registro: dict) -> None:
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as fh:
        json.dump(registro, fh, ensure_ascii=False, indent=2)


def _carregar_token_local() -> Optional[dict]:
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def salvar_credentials(supabase_admin, creds: Credentials, email: Optional[str] = None) -> dict:
    """Persiste refresh_token + metadados. Ordem: Supabase primeiro, JSON fallback."""
    registro = {
        "escopo": "calendar",
        "email": email or "",
        "refresh_token": creds.refresh_token,
        "access_token": creds.token,
        "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
        "scopes": " ".join(creds.scopes or SCOPES),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }
    gravou_supabase = _salvar_token_supabase(supabase_admin, registro)
    if not gravou_supabase:
        _salvar_token_local(registro)
    return registro


def carregar_credentials(supabase_admin, redirect_uri: str) -> Optional[Credentials]:
    """Retorna Credentials pronto pra uso (faz refresh automatico se precisar)."""
    registro = _carregar_token_supabase(supabase_admin) or _carregar_token_local()
    if not registro or not registro.get("refresh_token"):
        return None

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    creds = Credentials(
        token=registro.get("access_token"),
        refresh_token=registro["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=(registro.get("scopes") or "").split() or SCOPES,
    )
    if not creds.valid:
        try:
            creds.refresh(GoogleAuthRequest())
            salvar_credentials(supabase_admin, creds, registro.get("email"))
        except Exception as e:
            print(f"[calendar] Falha ao renovar access_token: {e}")
            msg = str(e).lower()
            if "invalid_grant" in msg or "expired" in msg or "revoked" in msg:
                print("[calendar] Token revogado/expirado. Apagando registro para forcar reconexao.")
                desconectar(supabase_admin)
            return None
    return creds


def status_integracao(supabase_admin) -> dict:
    registro = _carregar_token_supabase(supabase_admin) or _carregar_token_local()
    if not registro or not registro.get("refresh_token"):
        return {"conectado": False}

    creds = carregar_credentials(supabase_admin, "")
    if not creds:
        return {"conectado": False, "motivo": "token_invalido"}

    return {
        "conectado": True,
        "email": registro.get("email") or "",
        "atualizado_em": registro.get("atualizado_em"),
    }


def desconectar(supabase_admin) -> None:
    if supabase_admin:
        try:
            supabase_admin.table("integracao_google_tokens").delete().eq("escopo", "calendar").execute()
        except Exception as e:
            print(f"[calendar] Falha ao apagar token no Supabase: {e}")
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
        except Exception:
            pass


def listar_eventos_periodo(
    supabase_admin,
    redirect_uri: str,
    inicio: datetime,
    fim: datetime,
) -> list:
    """Retorna eventos da agenda primaria que tocam o intervalo [inicio, fim)."""
    creds = carregar_credentials(supabase_admin, redirect_uri)
    if not creds:
        raise RuntimeError("google_calendar_desconectado")

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    resp = service.events().list(
        calendarId="primary",
        timeMin=inicio.isoformat(),
        timeMax=fim.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=10,
    ).execute()
    eventos = []
    for ev in resp.get("items", []):
        if ev.get("status") == "cancelled":
            continue
        # pula eventos onde o usuario recusou
        self_resp = None
        for att in ev.get("attendees", []) or []:
            if att.get("self"):
                self_resp = att.get("responseStatus")
                break
        if self_resp == "declined":
            continue
        eventos.append({
            "id": ev.get("id"),
            "titulo": ev.get("summary") or "(sem título)",
            "inicio": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date"),
            "fim": ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date"),
            "html_link": ev.get("htmlLink"),
            "transparencia": ev.get("transparency") or "opaque",  # 'opaque' = ocupado, 'transparent' = livre
        })
    return eventos


def criar_evento(
    supabase_admin,
    redirect_uri: str,
    summary: str,
    inicio: datetime,
    fim: datetime,
    descricao: str = "",
    local: str = "",
    convidados: Optional[list] = None,
    timezone_str: str = "America/Sao_Paulo",
) -> dict:
    """Cria evento na agenda primaria do usuario autenticado."""
    creds = carregar_credentials(supabase_admin, redirect_uri)
    if not creds:
        raise RuntimeError("google_calendar_desconectado")

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    body = {
        "summary": summary[:200],
        "description": descricao[:3000],
        "location": local[:200],
        "start": {"dateTime": inicio.isoformat(), "timeZone": timezone_str},
        "end": {"dateTime": fim.isoformat(), "timeZone": timezone_str},
    }
    if convidados:
        body["attendees"] = [{"email": email} for email in convidados if email]

    evento = service.events().insert(
        calendarId="primary",
        body=body,
        sendUpdates="all" if convidados else "none",
    ).execute()
    return {
        "id": evento.get("id"),
        "html_link": evento.get("htmlLink"),
        "inicio": evento.get("start", {}).get("dateTime"),
        "fim": evento.get("end", {}).get("dateTime"),
        "status": evento.get("status"),
    }
