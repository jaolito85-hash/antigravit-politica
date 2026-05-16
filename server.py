import sys
import secrets
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import os
import requests
import json
import hashlib
import csv
import re
import unicodedata
from io import StringIO, BytesIO
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from functools import wraps
import feedparser
import bcrypt
import pyotp
import qrcode
import qrcode.image.svg
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from time import time as time_now

# Absolute path based on this file's location — prevents loading wrong .env
# when server is started from a different working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# SECRET_KEY: lê do .env ou gera aleatória (sessões caem a cada restart se não setada).
_secret_from_env = os.getenv("SECRET_KEY", "").strip()
if _secret_from_env and _secret_from_env != "politica-nodedata-secret-2024":
    app.secret_key = _secret_from_env
else:
    app.secret_key = secrets.token_hex(32)
    print("⚠️ SECRET_KEY não configurada no .env — usando chave aleatória (sessões caem em restart).")

# Hardening de cookie de sessão
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    SESSION_REFRESH_EACH_REQUEST=True,
)

# Política de lockout: N tentativas falhas → conta travada por X minutos.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

def _csrf_token():
    """Devolve o CSRF token da sessão atual, criando se ainda não existe."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token

def _csrf_valid(submitted: str) -> bool:
    expected = session.get("csrf_token")
    if not expected or not submitted:
        return False
    return secrets.compare_digest(str(expected), str(submitted))

# Disponibiliza csrf_token() nos templates Jinja
app.jinja_env.globals['csrf_token'] = _csrf_token

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Não autorizado"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

@app.before_request
def require_login():
    public_routes = {
        "login_page", "verify_2fa", "setup_2fa", "logout",
        "static", "service_worker", "manifest", "webhook",
    }
    if request.endpoint in public_routes:
        return
    if not session.get("logged_in"):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Não autorizado"}), 401
        return redirect(url_for("login_page"))

# Config
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME")

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Initialize Supabase client (if configured)
supabase = None
supabase_admin = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected!")
    except Exception as e:
        print(f"⚠️ Supabase connection failed: {e}")
        supabase = None

# Cliente admin com service_role key — bypassa RLS para operações de escrita do servidor
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        from supabase import create_client, Client
        supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase admin (service_role) connected!")
    except Exception as e:
        print(f"⚠️ Supabase admin connection failed: {e}")
        supabase_admin = None
else:
    # Fallback: usa o cliente padrão se não houver service key
    supabase_admin = supabase
    if supabase_admin:
        print("⚠️ SUPABASE_SERVICE_KEY não configurada — usando anon key para writes (pode falhar por RLS)")

# Fallback to local JSON if Supabase not configured
EVENTS_FILE        = os.path.join(BASE_DIR, 'execution', 'events.json')
CONFIG_FILE        = os.path.join(BASE_DIR, 'execution', 'config.json')
LAST_COMMENTS_FILE = os.path.join(BASE_DIR, 'execution', 'last_ig_comments.json')
OPERADORES_FILE    = os.path.join(BASE_DIR, 'execution', 'operadores_campo.json')
OPERACAO_FILE      = os.path.join(BASE_DIR, 'execution', 'operacao_local.json')
OPERACAO_MSGS_FILE = os.path.join(BASE_DIR, 'execution', 'operacao_mensagens.json')

# =============================================================================
# MOCK DATA — Radar de Comentários
# TODO: Substituir por chamada real à API quando disponível.
# Opções de integração:
#   - Apify (Instagram/YouTube scraping): https://docs.apify.com/api/v2
#     Actor para Instagram: apify/instagram-comment-scraper
#     Actor para YouTube: streamers/youtube-comment-scraper
#   - SerpAPI (Google, YouTube): https://serpapi.com/youtube-search-api
#   - Apify Twitter/X scraper: apify/twitter-scraper
# Para integrar: substituir MOCK_COMENTARIOS pelo retorno da API filtrado por
#   periodo (24h/7d/30d) e nome do político (cliente ou adversário).
# =============================================================================
MOCK_COMENTARIOS = [
    {
        "id": 1,
        "fonte": "Instagram",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "O vereador Carlos Mendes votou a favor do aumento da iluminação pública no bairro! Finalmente alguém que ouve o povo.",
        "sentimento": "Positivo",
        "data": "2026-02-25T14:30:00"
    },
    {
        "id": 2,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Esse vereador Carlos Mendes só aparece em época de eleição. Cadê as promessas de pavimentação da Rua das Flores?",
        "sentimento": "Negativo",
        "data": "2026-02-25T10:15:00"
    },
    {
        "id": 3,
        "fonte": "YouTube",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "A vereadora Ana Paula Rocha está indo muito bem! Projeto de creche aprovado, isso é o que a cidade precisa.",
        "sentimento": "Positivo",
        "data": "2026-02-24T18:00:00"
    },
    {
        "id": 4,
        "fonte": "Instagram",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "Voto contra ao projeto de saúde da Ana Paula foi uma decepção. Esperava mais dessa vereadora.",
        "sentimento": "Negativo",
        "data": "2026-02-24T11:45:00"
    },
    {
        "id": 5,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Participei da audiência pública do Dr. Carlos Mendes ontem. Ele ouviu as demandas do bairro com atenção. Bom sinal!",
        "sentimento": "Positivo",
        "data": "2026-02-23T20:00:00"
    },
    {
        "id": 6,
        "fonte": "YouTube",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "A proposta de parceria com empresas para gerar empregos foi uma boa ideia. Aguardando os resultados.",
        "sentimento": "Neutro",
        "data": "2026-02-23T15:30:00"
    },
    {
        "id": 7,
        "fonte": "Instagram",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "A Ana Paula continua sem dar respostas sobre o caso do aterro sanitário. Transparência zero.",
        "sentimento": "Negativo",
        "data": "2026-02-22T09:00:00"
    },
    {
        "id": 8,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Reunião do Dr. Carlos com moradores da Zona Norte foi produtiva. Comprometeu-se com as demandas de transporte.",
        "sentimento": "Positivo",
        "data": "2026-02-22T16:20:00"
    },
    {
        "id": 9,
        "fonte": "Instagram",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Mais uma semana sem resposta do gabinete do vereador Carlos. Péssima assessoria.",
        "sentimento": "Negativo",
        "data": "2026-02-21T08:00:00"
    },
    {
        "id": 10,
        "fonte": "YouTube",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "Debate entre candidatos foi equilibrado. Ana Paula apresentou propostas concretas para saúde.",
        "sentimento": "Neutro",
        "data": "2026-02-21T22:00:00"
    },
    {
        "id": 11,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "O projeto de lei do Carlos Mendes para iluminação das praças foi aprovado hoje! Excelente notícia para a cidade.",
        "sentimento": "Positivo",
        "data": "2026-02-20T13:00:00"
    },
    {
        "id": 12,
        "fonte": "Instagram",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "A vereadora Ana Paula Rocha esteve no evento de inauguração da UBS nova. Presença importante.",
        "sentimento": "Neutro",
        "data": "2026-02-20T10:30:00"
    },
    {
        "id": 13,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Esse Carlos Mendes gastou a verba de gabinete em viagens. Onde estão as prestações de contas?",
        "sentimento": "Negativo",
        "data": "2026-02-19T07:45:00"
    },
    {
        "id": 14,
        "fonte": "YouTube",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Vídeo do vereador explicando o orçamento participativo foi bem didático. Mais iniciativas assim!",
        "sentimento": "Positivo",
        "data": "2026-02-18T19:00:00"
    },
    {
        "id": 15,
        "fonte": "Instagram",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "Ana Paula prometeu a creche há dois anos. Até hoje nada. Decepção total com a política local.",
        "sentimento": "Negativo",
        "data": "2026-02-18T11:00:00"
    },
    {
        "id": 16,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Presença do vereador na audiência de mobilidade urbana foi fundamental. Bom representante.",
        "sentimento": "Positivo",
        "data": "2026-02-17T14:00:00"
    },
    {
        "id": 17,
        "fonte": "YouTube",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "Live da vereadora sobre transparência na câmara. Não respondeu as perguntas difíceis.",
        "sentimento": "Neutro",
        "data": "2026-02-17T21:30:00"
    },
    {
        "id": 18,
        "fonte": "Instagram",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Dr. Carlos está de parabéns pelo trabalho no Conselho de Saúde. A cidade precisa de políticos assim.",
        "sentimento": "Positivo",
        "data": "2026-02-16T09:30:00"
    },
    {
        "id": 19,
        "fonte": "Twitter/X",
        "perfil_monitorado": "Ana Paula Rocha",
        "tipo": "adversario",
        "trecho": "A oposição não apresentou nenhuma alternativa concreta ao projeto do prefeito. Política vazia.",
        "sentimento": "Negativo",
        "data": "2026-02-16T16:00:00"
    },
    {
        "id": 20,
        "fonte": "Instagram",
        "perfil_monitorado": "Dr. Carlos Mendes",
        "tipo": "cliente",
        "trecho": "Acompanhei a sessão de hoje na câmara. O vereador Carlos votou em linha com o que prometeu na campanha.",
        "sentimento": "Positivo",
        "data": "2026-02-15T18:00:00"
    }
]

# =============================================================================
# MOCK DATA — Radar de Notícias
# TODO: Substituir por chamada real à API de notícias quando disponível.
# Opções de integração:
#   - NewsAPI: https://newsapi.org/docs/endpoints/everything
#     GET https://newsapi.org/v2/everything?q={nome_politico}&language=pt&apiKey={API_KEY}
#   - Google News RSS: https://news.google.com/rss/search?q={nome_politico}&hl=pt-BR&gl=BR&ceid=BR:pt
#   - SerpAPI Google News: https://serpapi.com/google-news-results
#     GET https://serpapi.com/search?engine=google_news&q={nome_politico}&gl=br&hl=pt
# Para integrar: substituir MOCK_NOTICIAS pelo retorno da API, mapeando campos
#   para o formato: { id, titulo, veiculo, sentimento, resumo, url, data, politico }
# =============================================================================
MOCK_NOTICIAS = [
    {
        "id": 1,
        "titulo": "Vereador Carlos Mendes aprova projeto de iluminação nas praças da cidade",
        "veiculo": "G1",
        "sentimento": "Positivo",
        "resumo": "O projeto de lei de autoria do vereador Carlos Mendes foi aprovado por unanimidade na câmara municipal. A iniciativa prevê a instalação de 150 postes de LED em praças e parques da cidade nos próximos 6 meses.",
        "url": "#",
        "data": "2026-02-25",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 2,
        "titulo": "Câmara Municipal debate orçamento participativo para 2026",
        "veiculo": "UOL",
        "sentimento": "Neutro",
        "resumo": "Sessão extraordinária discutiu as demandas prioritárias da população para o próximo ciclo orçamentário. Vereadores de diferentes bancadas apresentaram propostas para as áreas de saúde, educação e infraestrutura.",
        "url": "#",
        "data": "2026-02-24",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 3,
        "titulo": "Vereadora Ana Paula Rocha lidera votação favorável à nova creche no bairro Sul",
        "veiculo": "Folha",
        "sentimento": "Positivo",
        "resumo": "A proposta da vereadora Ana Paula Rocha para construção de uma creche na Zona Sul foi aprovada com 15 votos a favor e 3 contra. A obra está prevista para começar no segundo semestre.",
        "url": "#",
        "data": "2026-02-23",
        "politico": "Ana Paula Rocha"
    },
    {
        "id": 4,
        "titulo": "Câmara rejeita proposta de aumento do transporte público",
        "veiculo": "Estadão",
        "sentimento": "Negativo",
        "resumo": "Projeto que visava aumentar o número de linhas de ônibus na periferia foi rejeitado por 10 votos contra. A oposição afirmou que a proposta não apresentava fonte de recursos suficiente para sua implementação.",
        "url": "#",
        "data": "2026-02-22",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 5,
        "titulo": "Vereador Carlos Mendes participa de audiência pública sobre mobilidade urbana",
        "veiculo": "G1",
        "sentimento": "Neutro",
        "resumo": "Audiência reuniu moradores, representantes do poder público e especialistas para discutir as principais demandas de transporte da cidade. O vereador apresentou três emendas ao projeto de mobilidade urbana.",
        "url": "#",
        "data": "2026-02-21",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 6,
        "titulo": "Escândalo: desvio de verbas investigado na câmara municipal",
        "veiculo": "R7",
        "sentimento": "Negativo",
        "resumo": "O Ministério Público abriu investigação sobre possível desvio de verbas de gabinetes na câmara. Dois assessores parlamentares foram ouvidos como testemunhas. O caso ainda está em fase inicial de apuração.",
        "url": "#",
        "data": "2026-02-20",
        "politico": "Ana Paula Rocha"
    },
    {
        "id": 7,
        "titulo": "Vereador propõe parceria público-privada para geração de empregos",
        "veiculo": "UOL",
        "sentimento": "Positivo",
        "resumo": "Carlos Mendes apresentou projeto de parceria com empresas do setor de tecnologia para instalação de polo de inovação na cidade. A estimativa é gerar 500 empregos diretos nos próximos dois anos.",
        "url": "#",
        "data": "2026-02-19",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 8,
        "titulo": "Vereadora Ana Paula Rocha critica cortes na saúde municipal",
        "veiculo": "Folha",
        "sentimento": "Negativo",
        "resumo": "Em sessão ordinária, a vereadora Ana Paula Rocha questionou os cortes anunciados no orçamento da saúde para o próximo exercício. Ela afirmou que os cortes comprometerão o atendimento nas UBSs da periferia.",
        "url": "#",
        "data": "2026-02-18",
        "politico": "Ana Paula Rocha"
    },
    {
        "id": 9,
        "titulo": "Carlos Mendes é eleito vice-presidente da Comissão de Infraestrutura",
        "veiculo": "G1",
        "sentimento": "Positivo",
        "resumo": "O vereador Carlos Mendes assumiu a vice-presidência da Comissão de Infraestrutura e Obras na câmara municipal. O parlamentar afirmou que irá priorizar a fiscalização das obras em andamento na cidade.",
        "url": "#",
        "data": "2026-02-17",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 10,
        "titulo": "Câmara aprova reajuste do salário dos servidores municipais",
        "veiculo": "Estadão",
        "sentimento": "Neutro",
        "resumo": "A proposta de reajuste de 6% para os servidores municipais foi aprovada por maioria na sessão de ontem. O reajuste será implementado em duas parcelas ao longo do ano.",
        "url": "#",
        "data": "2026-02-16",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 11,
        "titulo": "Ana Paula Rocha lança programa de alfabetização digital para idosos",
        "veiculo": "UOL",
        "sentimento": "Positivo",
        "resumo": "A vereadora apresentou projeto que prevê cursos gratuitos de informática e uso de smartphones para cidadãos acima de 60 anos. As aulas serão realizadas nos centros comunitários da cidade.",
        "url": "#",
        "data": "2026-02-15",
        "politico": "Ana Paula Rocha"
    },
    {
        "id": 12,
        "titulo": "Investigação apura irregularidades em licitação de obras",
        "veiculo": "R7",
        "sentimento": "Negativo",
        "resumo": "A Controladoria Municipal identificou possíveis irregularidades em processo licitatório para pavimentação de ruas. O caso foi encaminhado ao TCE para auditoria. Todos os envolvidos negam qualquer irregularidade.",
        "url": "#",
        "data": "2026-02-14",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 13,
        "titulo": "Vereadores aprovam criação do Conselho Municipal de Segurança",
        "veiculo": "G1",
        "sentimento": "Positivo",
        "resumo": "O projeto de criação do Conselho Municipal de Segurança Pública foi aprovado por unanimidade. O conselho terá representantes da sociedade civil, PM e câmara para monitorar índices de criminalidade.",
        "url": "#",
        "data": "2026-02-13",
        "politico": "Ana Paula Rocha"
    },
    {
        "id": 14,
        "titulo": "Sessão da câmara termina sem votação de projetos prioritários",
        "veiculo": "Folha",
        "sentimento": "Negativo",
        "resumo": "A falta de quórum impediu a votação de três projetos considerados prioritários para a cidade. A oposição criticou a ausência de vereadores governistas e pediu que a sessão fosse remarcada com urgência.",
        "url": "#",
        "data": "2026-02-12",
        "politico": "Dr. Carlos Mendes"
    },
    {
        "id": 15,
        "titulo": "Carlos Mendes defende revisão do plano diretor da cidade",
        "veiculo": "Estadão",
        "sentimento": "Neutro",
        "resumo": "O vereador apresentou requerimento solicitando a revisão do Plano Diretor Municipal, que está desatualizado desde 2015. A proposta prevê ampla participação da sociedade civil no processo de revisão.",
        "url": "#",
        "data": "2026-02-11",
        "politico": "Dr. Carlos Mendes"
    }
]


# --- MEDIA & TRANSCRIPTION ---

def download_evolution_media(remote_jid, message_id):
    """Downloads media from Evolution API and returns binary content."""
    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY or not EVOLUTION_INSTANCE_NAME:
        return None

    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMessage/{EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"message": {"key": {"id": message_id, "remoteJid": remote_jid, "fromMe": False}}}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            import base64
            data = response.json()
            if "base64" in data:
                return base64.b64decode(data["base64"])
        return None
    except Exception as e:
        print(f"❌ Error downloading media: {e}")
        return None


def transcribe_audio(audio_content):
    """Transcribes audio content using OpenAI Whisper API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not audio_content:
        return None

    try:
        from openai import OpenAI
        from io import BytesIO
        client = OpenAI(api_key=api_key)

        audio_file = BytesIO(audio_content)
        audio_file.name = "audio.ogg"

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return transcript.text
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return None


# =============================================================================
# VÍDEOS & PODCASTS — análise estratégica longa (YouTube/Spotify/Apple Podcasts)
# Pipeline: queued → downloading (yt-dlp) → transcribing (Whisper c/ chunking)
#         → analyzing (5 prompts GPT-4o em paralelo) → done | error
# =============================================================================

VIDEOS_TMP_DIR = os.getenv("VIDEOS_TMP_DIR", "/tmp/nodedata_videos")
VIDEOS_BUDGET_USD_MONTH = float(os.getenv("VIDEOS_BUDGET_USD_MONTH", "200") or "200")
_VIDEOS_WHITELIST = (
    "youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com",
    "open.spotify.com", "podcasts.apple.com",
)

try:
    os.makedirs(VIDEOS_TMP_DIR, exist_ok=True)
except Exception as _e:
    print(f"⚠️ Não consegui criar VIDEOS_TMP_DIR={VIDEOS_TMP_DIR}: {_e}")


def validar_url_video(url: str) -> tuple[bool, str]:
    """Valida URL de vídeo/podcast: só https + host na whitelist (anti-SSRF)."""
    if not url or not isinstance(url, str):
        return False, "URL vazia"
    url = url.strip()
    if not url.startswith("https://"):
        return False, "Apenas https:// é aceito"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except Exception:
        return False, "URL malformada"
    if not host:
        return False, "Host ausente"
    # match exato OU subdomínio de algum host conhecido (libsyn/megaphone usam subdomínios)
    if host in _VIDEOS_WHITELIST:
        return True, ""
    if host.endswith(".libsyn.com") or host.endswith(".megaphone.fm"):
        return True, ""
    return False, f"Host não permitido: {host}"


def baixar_audio_youtube(url: str, video_id: int) -> dict | None:
    """Baixa áudio com yt-dlp em opus mono 16kHz (~1MB/min). Retorna metadados + path local."""
    try:
        import yt_dlp
    except ImportError:
        print("❌ yt-dlp não instalado (pip install yt-dlp)")
        return None

    out_template = os.path.join(VIDEOS_TMP_DIR, f"video_{video_id}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
            "preferredquality": "32",
        }],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
        "noplaylist": True,
        "socket_timeout": 30,
    }
    cookies_file = os.getenv("YT_DLP_COOKIES_FILE", "").strip()
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        print(f"❌ yt-dlp falhou para {url}: {e}")
        return None

    audio_path = os.path.join(VIDEOS_TMP_DIR, f"video_{video_id}.opus")
    if not os.path.exists(audio_path):
        # yt-dlp pode escolher outra extensão se o pós-processor falhar
        for ext in ("m4a", "mp3", "ogg", "webm"):
            alt = os.path.join(VIDEOS_TMP_DIR, f"video_{video_id}.{ext}")
            if os.path.exists(alt):
                audio_path = alt
                break
        else:
            print(f"❌ Arquivo de áudio não encontrado após download id={video_id}")
            return None

    return {
        "path": audio_path,
        "titulo": info.get("title") or "",
        "canal": info.get("uploader") or info.get("channel") or "",
        "thumbnail_url": info.get("thumbnail") or "",
        "duracao_segundos": int(info.get("duration") or 0),
    }


def _chunk_audio(path: str, chunk_seconds: int = 600) -> list[tuple[str, float]]:
    """Quebra áudio em blocos de N segundos via ffmpeg. Retorna [(path_chunk, offset_inicial), ...]."""
    import subprocess
    base = os.path.splitext(path)[0]
    ext = os.path.splitext(path)[1] or ".opus"
    pattern = f"{base}_chunk_%03d{ext}"

    # ffprobe para duração
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        duration = float(probe.stdout.strip() or "0")
    except Exception as e:
        print(f"⚠️ ffprobe falhou: {e}")
        return [(path, 0.0)]

    if duration <= chunk_seconds:
        return [(path, 0.0)]

    # Split sem re-encode (rápido, mantém qualidade)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-f", "segment",
             "-segment_time", str(chunk_seconds), "-c", "copy", pattern],
            capture_output=True, timeout=300, check=True,
        )
    except Exception as e:
        print(f"❌ ffmpeg chunk falhou: {e}")
        return [(path, 0.0)]

    chunks = []
    i = 0
    while True:
        candidate = f"{base}_chunk_{i:03d}{ext}"
        if not os.path.exists(candidate):
            break
        chunks.append((candidate, float(i * chunk_seconds)))
        i += 1
    return chunks if chunks else [(path, 0.0)]


def transcrever_whisper_longo(audio_path: str) -> dict | None:
    """Transcreve áudio longo com chunking automático. Retorna {texto, segmentos, idioma}."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY ausente")
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"❌ OpenAI client falhou: {e}")
        return None

    chunks = _chunk_audio(audio_path, chunk_seconds=600)
    texto_total = []
    segmentos_total = []
    idioma = "pt"

    for chunk_path, offset in chunks:
        try:
            # Whisper aceita ogg/oga mas não opus (mesmo container). Renomeia o
            # filename enviado pra API sem precisar reencodar o arquivo no disco.
            with open(chunk_path, "rb") as f:
                audio_bytes = f.read()
            nome_para_api = os.path.basename(chunk_path)
            if nome_para_api.lower().endswith(".opus"):
                nome_para_api = nome_para_api[:-5] + ".ogg"
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=(nome_para_api, audio_bytes, "audio/ogg"),
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        except Exception as e:
            print(f"❌ Whisper falhou em chunk {chunk_path}: {e}")
            # Limpa chunks parciais antes de sair
            for cpath, _ in chunks:
                if cpath != audio_path:
                    try: os.remove(cpath)
                    except: pass
            return None

        texto_chunk = getattr(resp, "text", "") or ""
        if texto_chunk:
            texto_total.append(texto_chunk)
        idioma = getattr(resp, "language", "pt") or "pt"

        for seg in (getattr(resp, "segments", None) or []):
            # Normaliza para dict (SDK retorna objetos)
            d = seg if isinstance(seg, dict) else {
                "start": getattr(seg, "start", 0),
                "end": getattr(seg, "end", 0),
                "text": getattr(seg, "text", ""),
            }
            segmentos_total.append({
                "start": float(d.get("start", 0)) + offset,
                "end": float(d.get("end", 0)) + offset,
                "text": (d.get("text") or "").strip(),
            })

        # Remove chunk após processar (libera disco)
        if chunk_path != audio_path:
            try: os.remove(chunk_path)
            except: pass

    return {
        "texto": "\n".join(texto_total).strip(),
        "segmentos": segmentos_total,
        "idioma": idioma,
    }


def calcular_custo_processamento(duracao_segundos: int, tokens_in: int, tokens_out: int) -> dict:
    """Calcula custo (Whisper $0.006/min + GPT-4o $2.50/$10.00 por 1M tokens)."""
    minutos = max(0.0, duracao_segundos / 60.0)
    whisper_usd = round(minutos * 0.006, 4)
    gpt_in_usd = round((tokens_in / 1_000_000.0) * 2.50, 4)
    gpt_out_usd = round((tokens_out / 1_000_000.0) * 10.00, 4)
    total = round(whisper_usd + gpt_in_usd + gpt_out_usd, 4)
    return {
        "whisper_usd": whisper_usd,
        "gpt_in_usd": gpt_in_usd,
        "gpt_out_usd": gpt_out_usd,
        "total_usd": total,
        "total_brl": round(total * 5.0, 2),
    }


def _formatar_timeline(segmentos: list, max_chars: int = 30000) -> str:
    """Monta uma timeline compacta com timestamps mm:ss → texto. Trunca se necessário."""
    if not segmentos:
        return ""
    linhas = []
    total_chars = 0
    for seg in segmentos:
        start = int(seg.get("start") or 0)
        mm = start // 60
        ss = start % 60
        texto = (seg.get("text") or "").strip().replace("\n", " ")
        linha = f"[{mm:02d}:{ss:02d}] {texto}"
        if total_chars + len(linha) > max_chars:
            linhas.append("[…truncado…]")
            break
        linhas.append(linha)
        total_chars += len(linha) + 1
    return "\n".join(linhas)


def _papel_estrategico(tipo: str, candidato: str) -> str:
    """Retorna a frase de papel que abre cada prompt, baseada no tipo (adversario|proprio)."""
    if tipo == "adversario":
        return (
            f"Você é um estrategista político trabalhando CONTRA {candidato}. "
            f"Sua missão é extrair munição utilizável em campanha: gaffes, contradições, "
            f"declarações controversas, dados imprecisos. Seja preciso e direto."
        )
    return (
        f"Você é um assessor sênior do candidato {candidato}. "
        f"Sua missão é identificar riscos ANTES que virem crise: falas que podem ser "
        f"recortadas fora de contexto, promessas arriscadas, contradições com o histórico. "
        f"Tom protetivo e franco."
    )


def _chat_json(client, system: str, user: str, max_tokens: int = 1500) -> tuple[dict, int, int]:
    """Wrapper para chat completion com response_format=json_object. Retorna (json, tokens_in, tokens_out)."""
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"raw": raw, "_parse_error": True}
    usage = getattr(resp, "usage", None)
    t_in = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    t_out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    return parsed, t_in, t_out


# Prompts: cada função monta (system, user) — todas devolvem JSON estruturado.
_REGRAS_COMUNS = (
    "Regras estritas:\n"
    "1. Cite trechos EXATOS entre aspas (não parafraseie quando citar).\n"
    "2. Use timestamps no formato mm:ss extraídos da TIMELINE fornecida.\n"
    "3. NUNCA invente — se não está na transcrição, descarte.\n"
    "4. Resposta APENAS em JSON válido, sem markdown ou comentários."
)


def _prompt_resumo_executivo(tipo, candidato, ctx_extra, transcricao, timeline):
    papel = _papel_estrategico(tipo, candidato)
    system = (
        f"{papel}\n\n{_REGRAS_COMUNS}\n\n"
        "Retorne JSON com esta estrutura:\n"
        '{"tese_central": "...", "bullets": ["...", ...10 items],'
        ' "sentimento_geral": "positivo|negativo|neutro|misto",'
        ' "tom_emocional": "calmo|exaltado|defensivo|conciliador|agressivo",'
        ' "quotes_chave": [{"timestamp":"mm:ss","texto":"..."}]}'
    )
    user = (
        f"Contexto extra do assessor: {ctx_extra or '(nenhum)'}\n\n"
        f"TIMELINE:\n{timeline}\n\n"
        f"Gere o resumo executivo conforme estrutura."
    )
    return system, user


def _prompt_pontos_atencao(tipo, candidato, ctx_extra, transcricao, timeline):
    papel = _papel_estrategico(tipo, candidato)
    instrucao_tipo = ("Foco: encontre gaffes, ataques, posições polêmicas e dados imprecisos UTILIZÁVEIS contra o candidato."
                      if tipo == "adversario" else
                      "Foco: identifique falas que possam virar crise — recortes possíveis, promessas exageradas, posições inflamáveis.")
    system = (
        f"{papel}\n\n{instrucao_tipo}\n\n{_REGRAS_COMUNS}\n\n"
        "Retorne JSON: "
        '{"itens": [{"id": 1, "timestamp": "mm:ss", "citacao": "...", '
        '"categoria": "ataque|gaffe|posicao_polemica|dado_impreciso", '
        '"severidade": 1, "risco": "...", "tags": ["..."]}]}\n'
        "Severidade: 1=baixa, 2=média, 3=alta. Liste 5 a 15 itens. Lista vazia se nada relevante."
    )
    user = f"Contexto: {ctx_extra or '(nenhum)'}\n\nTIMELINE:\n{timeline}"
    return system, user


def _prompt_promessas(tipo, candidato, ctx_extra, transcricao, timeline):
    papel = _papel_estrategico(tipo, candidato)
    system = (
        f"{papel}\n\n"
        "Extraia TODAS as promessas, compromissos e dados numéricos verificáveis.\n\n"
        f"{_REGRAS_COMUNS}\n\n"
        "Retorne JSON: "
        '{"itens": [{"id": 1, "timestamp": "mm:ss", "texto": "citação exata", '
        '"parafrase_curta": "...", "prazo": "ate_2027|sem_prazo|...", '
        '"valor_numerico": "R$ 50mi|10%|null", "verificavel": true, '
        '"fonte_a_checar": "TSE|IBGE|portal transparência|null"}]}\n'
        "Lista vazia se não houver promessas/dados verificáveis."
    )
    user = f"Contexto: {ctx_extra or '(nenhum)'}\n\nTIMELINE:\n{timeline}"
    return system, user


def _prompt_contradicoes(tipo, candidato, ctx_extra, transcricao, timeline):
    papel = _papel_estrategico(tipo, candidato)
    system = (
        f"{papel}\n\n"
        "Identifique contradições INTERNAS no próprio vídeo (mesma fala se contradiz em momentos diferentes). "
        "Nunca compare com falas externas. Se não houver contradição clara, retorne lista vazia — NÃO FORCE.\n\n"
        f"{_REGRAS_COMUNS}\n\n"
        "Retorne JSON: "
        '{"itens": [{"id": 1, '
        '"trecho_a": {"timestamp": "mm:ss", "citacao": "..."}, '
        '"trecho_b": {"timestamp": "mm:ss", "citacao": "..."}, '
        '"natureza": "factual|posicional|temporal|...", '
        '"explorabilidade": "alta|media|baixa"}]}'
    )
    user = f"Contexto: {ctx_extra or '(nenhum)'}\n\nTIMELINE:\n{timeline}"
    return system, user


def _prompt_respostas_sugeridas(tipo, candidato, ctx_extra, transcricao, timeline, pontos_atencao):
    if tipo == "adversario":
        papel = (
            f"Você é estrategista de campanha trabalhando CONTRA {candidato}. "
            f"Gere ataques curtos, eficazes e factualmente ancorados nas falas do próprio candidato. "
            f"Tom: ofensivo mas elegante; usa o que ELE disse contra ele."
        )
    else:
        papel = (
            f"Você é assessor sênior de {candidato}. Gere defesas e contextualizações para uso "
            f"em entrevista ao vivo, redes sociais e contra-ataque. Tom: firme, conciliador quando possível, "
            f"sempre protegendo a imagem do candidato."
        )
    system = (
        f"{papel}\n\n{_REGRAS_COMUNS}\n\n"
        "Para CADA ponto de atenção fornecido, gere uma resposta. Retorne JSON: "
        '{"itens": [{"ponto_id": 1, "ponto_referencia_timestamp": "mm:ss", '
        '"contra_argumento_curto": "frase para entrevista ao vivo, max 25 palavras", '
        '"contra_argumento_longo": "max 80 palavras, com dados", '
        '"tweet": "max 280 chars, com hashtag relevante", '
        '"story_instagram": "texto curto para story, max 40 palavras", '
        '"tom": "ofensivo|defensivo|conciliador|tecnico", '
        '"alerta_uso": "null ou aviso (ex: \\"verificar dado antes de postar\\")"}]}'
    )
    pontos_resumo = json.dumps(pontos_atencao or [], ensure_ascii=False)[:8000]
    user = (
        f"Contexto: {ctx_extra or '(nenhum)'}\n\n"
        f"PONTOS DE ATENÇÃO já mapeados:\n{pontos_resumo}\n\n"
        f"TIMELINE (referência):\n{timeline}"
    )
    return system, user


def analisar_transcricao_estrategica(transcricao: str, segmentos: list, candidato: str,
                                     tipo: str, contexto_extra: str = "") -> dict:
    """Roda os 5 prompts em paralelo. Retorna dict com análises + tokens consumidos."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"_erro": "OPENAI_API_KEY ausente"}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        return {"_erro": f"client openai: {e}"}

    timeline = _formatar_timeline(segmentos, max_chars=30000)
    # Truncamento defensivo do texto bruto (caso prompts precisem)
    texto = (transcricao or "")[:50000]

    # Etapa 1: rodar 4 prompts independentes em paralelo
    prompts_etapa1 = [
        ("resumo", _prompt_resumo_executivo),
        ("pontos_atencao", _prompt_pontos_atencao),
        ("promessas", _prompt_promessas),
        ("contradicoes", _prompt_contradicoes),
    ]
    resultados = {}
    tokens_in_total = 0
    tokens_out_total = 0

    from concurrent.futures import ThreadPoolExecutor, as_completed
    def _executar(nome, builder):
        system, user = builder(tipo, candidato, contexto_extra, texto, timeline)
        try:
            parsed, t_in, t_out = _chat_json(client, system, user, max_tokens=2000)
            return nome, parsed, t_in, t_out, None
        except Exception as e:
            return nome, {}, 0, 0, str(e)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_executar, nome, builder) for nome, builder in prompts_etapa1]
        for fut in as_completed(futures):
            nome, parsed, t_in, t_out, err = fut.result()
            if err:
                print(f"[videos] prompt {nome} erro: {err}")
                resultados[nome] = {}
            else:
                resultados[nome] = parsed
            tokens_in_total += t_in
            tokens_out_total += t_out

    # Etapa 2: respostas_sugeridas depende dos pontos_atencao (sequencial após etapa 1)
    pontos_lista = (resultados.get("pontos_atencao") or {}).get("itens") or []
    if pontos_lista:
        try:
            system, user = _prompt_respostas_sugeridas(
                tipo, candidato, contexto_extra, texto, timeline, pontos_lista[:15]
            )
            parsed_r, t_in, t_out = _chat_json(client, system, user, max_tokens=3000)
            resultados["respostas_sugeridas"] = parsed_r
            tokens_in_total += t_in
            tokens_out_total += t_out
        except Exception as e:
            print(f"[videos] respostas_sugeridas erro: {e}")
            resultados["respostas_sugeridas"] = {"itens": []}
    else:
        resultados["respostas_sugeridas"] = {"itens": []}

    return {
        "resumo": resultados.get("resumo") or {},
        "pontos_atencao": (resultados.get("pontos_atencao") or {}).get("itens") or [],
        "promessas": (resultados.get("promessas") or {}).get("itens") or [],
        "contradicoes": (resultados.get("contradicoes") or {}).get("itens") or [],
        "respostas_sugeridas": (resultados.get("respostas_sugeridas") or {}).get("itens") or [],
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }


def _custo_mensal_videos_usd() -> float:
    """Soma custo_usd das análises do mês corrente. Retorna 0 em erro."""
    if not supabase_admin:
        return 0.0
    try:
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        resp = supabase_admin.table("videos_analises") \
            .select("custo_usd") \
            .gte("criado_em", inicio_mes) \
            .execute()
        total = 0.0
        for row in (resp.data or []):
            try:
                total += float(row.get("custo_usd") or 0)
            except (TypeError, ValueError):
                continue
        return total
    except Exception as e:
        print(f"[videos] Erro ao calcular custo mensal: {e}")
        return 0.0


def _videos_update_status(video_id: int, status: str, progresso: int = None, **extras):
    """Helper para atualizar status do video no Supabase com try/except."""
    if not supabase_admin:
        return False
    payload = {"status": status}
    if progresso is not None:
        payload["progresso"] = int(progresso)
    for k, v in extras.items():
        payload[k] = v
    try:
        supabase_admin.table("videos_analises").update(payload).eq("id", video_id).execute()
        return True
    except Exception as e:
        print(f"[videos] update status falhou id={video_id}: {e}")
        return False


def _processar_video_pipeline(video_id: int, url: str):
    """Thread background: download → transcrição → (análise IA virá no commit 2)."""
    print(f"[videos] pipeline iniciado id={video_id} url={url[:80]}")
    _videos_update_status(video_id, "downloading", progresso=5,
                          iniciado_em=datetime.utcnow().isoformat())

    meta = baixar_audio_youtube(url, video_id)
    if not meta:
        _videos_update_status(video_id, "error", erro="Falha no download do áudio",
                              finalizado_em=datetime.utcnow().isoformat())
        return

    _videos_update_status(
        video_id, "transcribing", progresso=30,
        titulo=meta["titulo"][:500] if meta.get("titulo") else None,
        canal=meta["canal"][:300] if meta.get("canal") else None,
        thumbnail_url=meta["thumbnail_url"][:1000] if meta.get("thumbnail_url") else None,
        duracao_segundos=meta["duracao_segundos"],
    )

    trans = transcrever_whisper_longo(meta["path"])
    # Remove o arquivo de áudio principal após transcrição
    try:
        if os.path.exists(meta["path"]):
            os.remove(meta["path"])
    except Exception as e:
        print(f"[videos] Falha ao remover áudio id={video_id}: {e}")

    if not trans or not trans.get("texto"):
        _videos_update_status(video_id, "error", erro="Falha na transcrição",
                              finalizado_em=datetime.utcnow().isoformat())
        return

    _videos_update_status(
        video_id, "analyzing", progresso=70,
        transcricao=trans["texto"],
        transcricao_segmentos=trans["segmentos"],
        idioma=trans.get("idioma", "pt"),
    )

    # Busca candidato/tipo/contexto_extra do registro para alimentar prompts
    try:
        meta_db = supabase_admin.table("videos_analises") \
            .select("candidato, tipo, contexto_extra") \
            .eq("id", video_id).limit(1).execute()
        registro = (meta_db.data or [{}])[0]
    except Exception as e:
        print(f"[videos] erro ao buscar metadados id={video_id}: {e}")
        registro = {}

    analise = analisar_transcricao_estrategica(
        transcricao=trans["texto"],
        segmentos=trans["segmentos"],
        candidato=registro.get("candidato") or "Candidato",
        tipo=registro.get("tipo") or "proprio",
        contexto_extra=registro.get("contexto_extra") or "",
    )

    if analise.get("_erro"):
        _videos_update_status(video_id, "error",
                              erro=f"Falha na análise IA: {analise.get('_erro')}",
                              finalizado_em=datetime.utcnow().isoformat())
        return

    tokens_in = int(analise.get("tokens_in") or 0)
    tokens_out = int(analise.get("tokens_out") or 0)
    custo = calcular_custo_processamento(meta["duracao_segundos"], tokens_in, tokens_out)

    resumo = analise.get("resumo") or {}
    sentimento = (resumo.get("sentimento_geral") or "").lower() or None

    _videos_update_status(
        video_id, "done", progresso=100,
        resumo=resumo,
        pontos_atencao=analise.get("pontos_atencao") or [],
        promessas=analise.get("promessas") or [],
        contradicoes=analise.get("contradicoes") or [],
        respostas_sugeridas=analise.get("respostas_sugeridas") or [],
        sentimento_geral=sentimento,
        custo_usd=custo["total_usd"],
        custo_breakdown=custo,
        tokens_consumidos={"input": tokens_in, "output": tokens_out, "total": tokens_in + tokens_out},
        finalizado_em=datetime.utcnow().isoformat(),
    )
    print(f"[videos] pipeline DONE id={video_id} duracao={meta['duracao_segundos']}s "
          f"custo=${custo['total_usd']} tokens={tokens_in}+{tokens_out}")


def _cleanup_videos_tmp():
    """Daemon: remove arquivos em VIDEOS_TMP_DIR com mtime > 24h. Roda a cada 6h."""
    import threading, time as _time
    def loop():
        while True:
            try:
                if os.path.isdir(VIDEOS_TMP_DIR):
                    agora = _time.time()
                    for nome in os.listdir(VIDEOS_TMP_DIR):
                        caminho = os.path.join(VIDEOS_TMP_DIR, nome)
                        try:
                            if os.path.isfile(caminho) and (agora - os.path.getmtime(caminho)) > 24 * 3600:
                                os.remove(caminho)
                                print(f"[videos] cleanup removeu {nome}")
                        except Exception:
                            continue
            except Exception as e:
                print(f"[videos] cleanup loop erro: {e}")
            _time.sleep(6 * 3600)
    t = threading.Thread(target=loop, daemon=True, name="videos-cleanup")
    t.start()
    return t


_cleanup_videos_tmp()


# --- HELPER FUNCTIONS ---

def load_json(filepath, default):
    """Fallback for local JSON files"""
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default


def save_json(filepath, data):
    """Fallback for local JSON files"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_feedbacks():
    """Get feedbacks from Supabase or local JSON"""
    if supabase:
        try:
            response = supabase.table('feedbacks').select('*').order('id', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Supabase error: {e}")
            return load_json(EVENTS_FILE, [])
    return load_json(EVENTS_FILE, [])


def save_feedback(feedback_data):
    """Save feedback to Supabase or local JSON"""
    data = feedback_data.copy()
    if 'pushName' in data:
        data['name'] = data.pop('pushName')
    if 'remoteJid' in data:
        data['sender'] = data.pop('remoteJid')

    if supabase_admin:
        try:
            payload_supabase = data.copy()
            payload_supabase.pop('id', None)
            supabase_admin.table('feedbacks').insert(payload_supabase).execute()
            print("✅ Supabase insert success")
            return True
        except Exception as e:
            print(f"❌ Supabase insert error: {e}")
            feedbacks = load_json(EVENTS_FILE, [])
            feedbacks.insert(0, data)
            save_json(EVENTS_FILE, feedbacks)
            return True
    else:
        feedbacks = load_json(EVENTS_FILE, [])
        feedbacks.insert(0, data)
        save_json(EVENTS_FILE, feedbacks)
        return True


def update_feedback(feedback_id, updates):
    """Update feedback in Supabase or local JSON"""
    if supabase_admin:
        try:
            supabase_admin.table('feedbacks').update(updates).eq('id', feedback_id).execute()
            return True
        except Exception as e:
            print(f"Supabase update error: {e}")
            # Fallback to JSON
            feedbacks = load_json(EVENTS_FILE, [])
            for fb in feedbacks:
                if fb.get('id') == feedback_id:
                    fb.update(updates)
                    break
            save_json(EVENTS_FILE, feedbacks)
            return True
    else:
        feedbacks = load_json(EVENTS_FILE, [])
        for fb in feedbacks:
            if fb.get('id') == feedback_id:
                fb.update(updates)
                break
        save_json(EVENTS_FILE, feedbacks)
        return True


def get_config():
    """Get config from Supabase or local JSON"""
    if supabase:
        try:
            categories_resp = supabase.table('config').select('*').eq('type', 'category').execute()
            regions_resp = supabase.table('config').select('*').eq('type', 'region').execute()
            return {
                "categories": [{"name": c['name'], "color": c.get('color', '#1a3a6b')} for c in categories_resp.data],
                "regions": [{"name": r['name']} for r in regions_resp.data]
            }
        except Exception as e:
            print(f"Supabase config error: {e}")
            return load_json(CONFIG_FILE, {"categories": [], "regions": []})
    return load_json(CONFIG_FILE, {"categories": [], "regions": []})


def get_next_id():
    """Get next ID for new feedback"""
    if supabase:
        try:
            response = supabase.table('feedbacks').select('id').order('id', desc=True).limit(1).execute()
            if response.data:
                return response.data[0]['id'] + 1
            return 1
        except:
            return 1
    else:
        feedbacks = load_json(EVENTS_FILE, [])
        return len(feedbacks) + 1


# --- CLASSIFICATION FUNCTIONS ---

def classificar_sentimento(texto):
    """Classifica sentimento de mensagens sobre política"""
    texto_lower = texto.lower()

    # POSITIVO
    palavras_positivas = [
        'lindo', 'maravilhoso', 'incrivel', 'incrível', 'excelente', 'perfeito',
        'sensacional', 'fantastico', 'fantástico', 'adorei', 'amei', 'recomendo',
        'parabens', 'parabéns', 'obrigado', 'obrigada', 'agradeço',
        'top', 'show', 'bom', 'muito bom', 'demais', 'massa', 'arrasou',
        'curti', 'curtindo', 'gostei', 'gostando', 'amando',
        'aprovado', 'aprovaram', 'votou bem', 'boa proposta', 'ótimo projeto',
        'melhorou', 'resolveram', 'consertaram', 'arrumaram', 'ficou bom',
        'funcionando', 'ta funcionando', 'tá funcionando', 'de parabéns',
        'bom vereador', 'bom prefeito', 'bom político', 'honesto', 'transparente'
    ]
    for palavra in palavras_positivas:
        if palavra in texto_lower:
            return 'Positivo'

    # CRÍTICO - emergências e denúncias graves
    palavras_criticas = [
        'corrupcao', 'corrupção', 'desvio', 'desvio de verba', 'peculato', 'propina',
        'suborno', 'fraude', 'esquema', 'roubando', 'roubou dinheiro público',
        'assalto ao erário', 'improbidade', 'escândalo', 'cpi',
        'emergencia', 'emergência', 'socorro', 'perigo imediato',
        'violencia', 'violência', 'ameaça de morte', 'perseguição',
        'denúncia grave', 'denuncia grave', 'crime eleitoral',
    ]
    for palavra in palavras_criticas:
        if palavra in texto_lower:
            return 'Critico'

    # URGENTE - problemas graves, inação, promessas não cumpridas
    palavras_urgentes = [
        'pessimo', 'péssimo', 'horrivel', 'horrível', 'absurdo', 'vergonha',
        'descaso', 'desrespeito', 'inadmissível', 'inaceitável',
        'mentiu', 'mentira', 'prometeu e não cumpriu', 'promessa vazia',
        'não resolve', 'nao resolve', 'faltou', 'falta', 'cadê', 'cadê as obras',
        'cadê o projeto', 'cadê a creche', 'sumiram', 'sumiu',
        'abandono', 'abandonado', 'esquecido', 'esqueceram',
        'ta osso', 'tá osso', 'uma bosta', 'uma merda', 'um lixo',
        'lamentável', 'deplorável', 'indignado', 'indignação',
        'voto errado', 'votou contra o povo', 'representou mal',
        'quebrou promessa', 'traição política'
    ]
    for palavra in palavras_urgentes:
        if palavra in texto_lower:
            return 'Urgente'

    return 'Neutro'


def classificar_categoria(texto):
    """Classifica categoria de mensagem sobre política"""
    texto_lower = texto.lower()

    # SEGURANÇA PÚBLICA (verificar primeiro - emergências)
    palavras_seguranca = [
        'segurança', 'seguranca', 'policia', 'polícia', 'guarda municipal',
        'ronda', 'viatura', 'crime', 'violência', 'violencia', 'assalto',
        'roubo', 'furto', 'tráfico', 'trafico', 'droga', 'drogas',
        'arma', 'vandalismo', 'pichação', 'pichacao', 'câmera de segurança',
        'iluminação noturna', 'iluminacao noturna', 'zona de risco',
        'homicidio', 'homicídio', 'delegacia', 'boletim de ocorrência'
    ]
    if any(p in texto_lower for p in palavras_seguranca):
        return 'Segurança Pública'

    # PROPOSTAS & PROJETOS (legislativo)
    palavras_propostas = [
        'projeto de lei', 'proposta', 'pl ', 'câmara', 'camara', 'plenário', 'plenario',
        'votação', 'votacao', 'votou', 'voto', 'aprovado', 'aprovação', 'aprovacao',
        'rejeitado', 'rejeição', 'emenda', 'requerimento', 'audiência pública',
        'audiencia publica', 'sessão', 'sessao', 'mandato', 'vereador', 'prefeito',
        'gestão pública', 'gestao publica', 'transparência', 'transparencia',
        'prestação de contas', 'prestacao de contas', 'orçamento', 'orcamento',
        'lei municipal', 'decreto', 'portaria', 'fiscalização', 'fiscalizacao'
    ]
    if any(p in texto_lower for p in palavras_propostas):
        return 'Propostas & Projetos'

    # DESENVOLVIMENTO ECONÔMICO
    palavras_economia = [
        'emprego', 'empregos', 'empresa', 'empresas', 'comércio', 'comercio',
        'indústria', 'industria', 'investimento', 'investimentos', 'polo industrial',
        'parque tecnológico', 'parque tecnologico', 'startup', 'inovação', 'inovacao',
        'geração de renda', 'geracao de renda', 'fomento', 'microempreendedor', 'mei',
        'turismo', 'agronegócio', 'agronegocio', 'exportação', 'exportacao',
        'zona franca', 'distrito comercial', 'feira', 'mercado municipal',
        'financiamento', 'crédito', 'credito', 'sebrae', 'senai'
    ]
    if any(p in texto_lower for p in palavras_economia):
        return 'Desenvolvimento Econômico'

    # SAÚDE & EDUCAÇÃO
    palavras_saude_educacao = [
        'saude', 'saúde', 'hospital', 'ubs', 'posto de saude', 'posto de saúde',
        'medico', 'médico', 'enfermeiro', 'consulta', 'exame', 'remedio', 'remédio',
        'medicamento', 'farmacia', 'farmácia', 'vacina', 'vacinação',
        'escola', 'creche', 'professor', 'professora', 'aluno', 'merenda',
        'matricula', 'matrícula', 'educação', 'educacao', 'ensino', 'alfabetização',
        'alfabetizacao', 'universidade', 'faculdade', 'bolsa de estudo',
        'clinica', 'clínica', 'pronto socorro', 'leito', 'internação'
    ]
    if any(p in texto_lower for p in palavras_saude_educacao):
        return 'Saúde & Educação'

    # TRANSPORTE & MOBILIDADE
    palavras_transporte = [
        'onibus', 'ônibus', 'transporte', 'ponto de onibus', 'ponto de ônibus',
        'semaforo', 'semáforo', 'transito', 'trânsito', 'engarrafamento',
        'ciclovia', 'bicicleta', 'pedestre', 'faixa de pedestres',
        'estacionamento', 'vaga', 'uber', 'taxi', 'táxi',
        'rua interditada', 'desvio', 'lombada', 'radar',
        'passagem', 'tarifa', 'bilhete', 'cartão transporte',
        'mobilidade', 'acessibilidade'
    ]
    if any(p in texto_lower for p in palavras_transporte):
        return 'Transporte & Mobilidade'

    # MEIO AMBIENTE
    palavras_meio_ambiente = [
        'poda', 'árvore', 'arvore', 'galho', 'mato', 'capina',
        'praça', 'praca', 'parque', 'jardim', 'rio sujo', 'córrego', 'corrego',
        'meio ambiente', 'queimada', 'desmatamento', 'poluição', 'poluicao',
        'lixo', 'lixão', 'lixeira', 'coleta de lixo', 'reciclagem',
        'saneamento', 'bueiro', 'enchente', 'alagamento',
        'fauna', 'flora', 'animal silvestre', 'sustentabilidade'
    ]
    if any(p in texto_lower for p in palavras_meio_ambiente):
        return 'Meio Ambiente'

    # ASSISTÊNCIA SOCIAL
    palavras_social = [
        'cras', 'creas', 'assistência social', 'assistencia social',
        'bolsa familia', 'bolsa família', 'cadastro unico', 'cadastro único',
        'bpc', 'beneficio', 'benefício', 'vulnerável', 'vulneravel',
        'morador de rua', 'sem teto', 'família carente', 'familia carente',
        'fome', 'cesta basica', 'cesta básica', 'idoso', 'deficiente', 'pcd',
        'violência doméstica', 'violencia domestica', 'acolhimento',
        'psicólogo', 'psicologo', 'psicossocial', 'criança em situação de risco'
    ]
    if any(p in texto_lower for p in palavras_social):
        return 'Assistência Social'

    # INFRAESTRUTURA & OBRAS (fallback para problemas físicos)
    palavras_infra = [
        'buraco', 'buracos', 'asfalto', 'pavimentação', 'pavimentacao',
        'calçada', 'calcada', 'meio-fio', 'sarjeta',
        'poste', 'iluminação', 'iluminacao', 'luz', 'sem luz', 'lampada', 'lâmpada',
        'vazamento', 'agua', 'água', 'esgoto', 'cano', 'encanamento',
        'alagamento', 'alagado', 'enchente', 'inundação', 'inundacao',
        'obra', 'obras', 'construção', 'construcao', 'reforma',
        'ponte', 'viaduto', 'passarela', 'muro',
        'quebrado', 'quebrou', 'danificado', 'estragado',
        'energia', 'falta de energia'
    ]
    if any(p in texto_lower for p in palavras_infra):
        return 'Infraestrutura & Obras'

    # Fallback: Propostas & Projetos como categoria geral política
    return 'Propostas & Projetos'


def classificar_regiao(texto):
    """Classifica região/bairro mencionado na mensagem"""
    texto_lower = texto.lower()

    if any(p in texto_lower for p in ['centro', 'praça central', 'praca central', 'câmara', 'camara', 'catedral', 'prefeitura']):
        return 'Centro'
    if any(p in texto_lower for p in ['zona norte', 'norte', 'bairro norte']):
        return 'Zona Norte'
    if any(p in texto_lower for p in ['zona sul', 'sul', 'bairro sul']):
        return 'Zona Sul'
    if any(p in texto_lower for p in ['zona leste', 'leste', 'bairro leste']):
        return 'Zona Leste'
    if any(p in texto_lower for p in ['zona oeste', 'oeste', 'bairro oeste']):
        return 'Zona Oeste'
    if any(p in texto_lower for p in ['distrito industrial', 'industrial', 'fábrica', 'fabrica', 'galpão', 'galpao']):
        return 'Distrito Industrial'
    if any(p in texto_lower for p in ['zona rural', 'rural', 'fazenda', 'sítio', 'sitio', 'chácara', 'chacara', 'estrada de terra']):
        return 'Zona Rural'

    return 'N/A'


# --- AI CLASSIFICATION FALLBACK ---
def classificar_com_ia(texto):
    """Usa IA para classificar quando keywords retornam resultado genérico"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = f'''Classifique esta mensagem sobre política/gestão pública no Brasil.
Texto: "{texto}"

Responda APENAS em JSON com este formato exato:
{{
  "categoria": "Propostas & Projetos" | "Infraestrutura & Obras" | "Saúde & Educação" | "Segurança Pública" | "Transporte & Mobilidade" | "Meio Ambiente" | "Desenvolvimento Econômico" | "Assistência Social",
  "sentimento": "Positivo" | "Critico" | "Urgente" | "Neutro",
  "regiao": "Centro" | "Zona Norte" | "Zona Sul" | "Zona Leste" | "Zona Oeste" | "Distrito Industrial" | "Zona Rural" | "N/A",
  "cidade": "nome da cidade mencionada em MG ou N/A se não identificável"
}}

Regras de categoria:
- Propostas & Projetos: votações, projetos de lei, mandatos, gestão pública, transparência
- Desenvolvimento Econômico: emprego, empresa, comércio, investimento, polo industrial
- Saúde & Educação: hospital, UBS, escola, creche, professor, medicamento
- Segurança Pública: crime, violência, polícia, guarda municipal, tráfico
- Critico = corrupção comprovada, emergências, denúncias graves
- Urgente = promessas não cumpridas, descaso, problemas graves sem solução
- Positivo = elogios, projetos aprovados, agradecimentos
- Neutro = perguntas, sugestões, informações neutras

Regras de cidade:
- Identifique a cidade de Minas Gerais mencionada no texto (ex: Belo Horizonte, Uberlândia, Contagem, Betim, Ipatinga, etc.)
- Se não houver cidade identificável, retorne "N/A"'''

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        return json.loads(result_text)
    except Exception as e:
        print(f"Erro IA classificação: {e}")
        return None


# --- AI RESPONSE FUNCTION (PERSONA: MARCOS) ---
def generate_ai_response(text, category, urgency, protocol_num):
    """Gera resposta do Marcos — assistente virtual de inteligência política"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"Olá! Sou o Marcos, assistente de inteligência política. Recebi sua mensagem e registrei com o protocolo #{protocol_num}. Em breve nossa equipe entrará em contato."

    is_critical = urgency in ['Critico', 'Crítico']
    is_urgent = urgency == 'Urgente'
    is_positive = urgency == 'Positivo'
    is_complaint = not is_positive

    urgency_instruction = ''
    if is_critical:
        urgency_instruction = 'PRIORIDADE MÁXIMA: informe que a denúncia foi registrada com urgência e será encaminhada ao responsável político imediatamente.'
    elif is_urgent:
        urgency_instruction = 'Mencione que a solicitação foi marcada como URGENTE e que o gestor político já foi notificado.'
    elif is_positive:
        urgency_instruction = 'É um elogio ou feedback positivo! Agradeça de coração pelo retorno positivo do cidadão.'
    else:
        urgency_instruction = 'Tom tranquilo e acolhedor. Confirme o registro e diga que a equipe irá analisar.'

    emoji_rule = (
        'NÃO use emojis. A situação é séria e o cidadão está insatisfeito.'
        if is_complaint else
        'Pode usar no máximo 1 emoji positivo (ex: 🙏 ou ✅) ao final.'
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        system_prompt = f"""Você é o Marcos, assistente virtual de inteligência política.
Sua missão é acolher o cidadão com empatia, registrar demandas políticas e transmitir ao gestor público monitorado.

REGRAS ABSOLUTAS:
- Escreva SOMENTE UMA resposta coesa. NUNCA divida em duas mensagens.
- MÁXIMO 3 frases curtas.
- Tom: profissional, próximo, empático. Zero linguagem burocrática ou corporativa.
- Mencione o protocolo #{protocol_num} de forma natural (ex: "registrei com o protocolo #...").
- Categoria registrada: {category}.
- {urgency_instruction}
- {emoji_rule}

SOBRE PERGUNTAS DE ACOMPANHAMENTO:
- Se a mensagem menciona um problema em local genérico, pergunte QUAL bairro ou região.
- Se menciona um político sem especificar a demanda, pergunte O QUE exatamente o cidadão espera.
- NUNCA mencione "Categoria classificada é" de forma robótica.
- NUNCA mencione ser robô, IA, sistema ou bot."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=130,
            temperature=0.5
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro ao gerar resposta do Marcos: {e}")
        return f"Olá! Sou o Marcos. Recebi sua mensagem e abrimos o protocolo #{protocol_num}. Nossa equipe de {category} irá analisar. Poderia nos informar o local ou o contexto completo?"


def send_whatsapp_message(remote_jid, message):
    """Sends a text message using Evolution API."""
    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY or not EVOLUTION_INSTANCE_NAME:
        print(f"❌ Evolution API not configured!")
        return

    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"number": remote_jid, "text": message}

    print(f"📤 Sending WhatsApp reply to: {remote_jid}")
    print(f"📤 URL: {url}")
    print(f"📤 Message: {message}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"📤 Response Status: {response.status_code}")
        print(f"📤 Response Body: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error sending message: {e}")


def send_whatsapp_document(remote_jid, filename, file_bytes, caption="", mimetype="application/pdf"):
    """Envia documento (PDF por padrão) via Evolution API /message/sendMedia."""
    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY or not EVOLUTION_INSTANCE_NAME:
        print("❌ Evolution API not configured (sendMedia)")
        return False

    import base64 as _b64
    url = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {
        "number": remote_jid,
        "mediatype": "document",
        "mimetype": mimetype,
        "caption": caption or "",
        "media": _b64.b64encode(file_bytes).decode(),
        "fileName": filename,
    }

    print(f"📎 Sending document to {remote_jid}: {filename} ({len(file_bytes)} bytes)")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"📎 Response Status: {response.status_code}")
        print(f"📎 Response Body: {response.text[:200]}")
        return response.ok
    except Exception as e:
        print(f"❌ Error sending document: {e}")
        return False


# --- AI POLITICAL PULSE ---
def generate_ai_pulse(feedbacks):
    """Gera resumo inteligente do cenário político usando IA"""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or not feedbacks:
        return {"summary": "Aguardando feedbacks dos cidadãos para análise...", "status": "waiting"}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        recent = feedbacks[:50]

        sentimentos = Counter([f.get('urgency', 'Neutro') for f in recent])
        categorias = Counter([f.get('category', 'Geral') for f in recent])

        feedback_list = "\n".join([f"- [{f.get('urgency')}] {f.get('message')[:80]}" for f in recent[:20]])

        prompt = f'''Você é um analista de inteligência política. Analise os feedbacks recentes dos cidadãos sobre gestão pública e gere um resumo MUITO CURTO (máximo 2 frases).

DADOS:
- Total feedbacks recentes: {len(recent)}
- Sentimentos: {dict(sentimentos)}
- Categorias: {dict(categorias)}

Últimos feedbacks:
{feedback_list}

FORMATO DA RESPOSTA:
1. Status geral (🟢 Cenário Favorável / 🟡 Atenção / 🔴 Crise de Imagem)
2. Insight principal (o que mais se destaca nas mensagens dos cidadãos)
3. Sugestão rápida se houver problema

Exemplo: "🟡 Atenção! Alta demanda em Infraestrutura. 3 reclamações sobre obras paradas na Zona Norte precisam de posicionamento público."

Seja MUITO conciso, máximo 150 caracteres.'''

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.7
        )

        summary = response.choices[0].message.content.strip()

        if "🔴" in summary or "crise" in summary.lower():
            status = "critical"
        elif "🟡" in summary or "atenção" in summary.lower():
            status = "warning"
        else:
            status = "good"

        return {"summary": summary, "status": status}

    except Exception as e:
        print(f"Erro AI Pulse: {e}")
        return {"summary": "Não foi possível gerar análise.", "status": "error"}


# --- SPAM PROTECTION ---

rate_limit_store = defaultdict(list)
RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 600


def is_rate_limited(remote_jid):
    """Verifica se o número excedeu o limite de mensagens"""
    now = time_now()
    rate_limit_store[remote_jid] = [t for t in rate_limit_store[remote_jid] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limit_store[remote_jid]) >= RATE_LIMIT_MAX:
        return True
    rate_limit_store[remote_jid].append(now)
    return False


def is_emoji_only(text):
    """Verifica se a mensagem contém apenas emojis (sem texto real)"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "\U00002764"
        "\U0000FE0F"
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', text).strip()
    return len(cleaned) == 0


MIN_MESSAGE_LENGTH = 3

# --- ROUTES ---

# =============================================================================
# AUTENTICAÇÃO — bcrypt + lockout + TOTP (2FA) + CSRF
# Usuários ficam em usuarios_painel (Supabase). Backend usa supabase_admin.
# =============================================================================

def _buscar_usuario(username: str):
    """Busca um usuário pelo username (case-insensitive). Retorna dict ou None."""
    if not supabase_admin or not username:
        return None
    try:
        resp = (
            supabase_admin.table("usuarios_painel")
            .select("*")
            .ilike("username", username.strip())
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"⚠️ Erro ao buscar usuário no Supabase: {e}")
        return None

def _atualizar_usuario(user_id: str, patch: dict) -> bool:
    if not supabase_admin or not user_id or not patch:
        return False
    try:
        supabase_admin.table("usuarios_painel").update(patch).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"⚠️ Erro ao atualizar usuário {user_id}: {e}")
        return False

def _usuario_travado(usuario: dict) -> bool:
    locked_until = usuario.get("locked_until")
    if not locked_until:
        return False
    try:
        # Supabase devolve ISO string com timezone
        dt = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        return dt > datetime.now(timezone.utc)
    except Exception:
        return False

def _registrar_falha_login(usuario: dict):
    """Incrementa failed_attempts e trava conta se atingir o limite."""
    novo_contador = (usuario.get("failed_attempts") or 0) + 1
    patch = {"failed_attempts": novo_contador}
    if novo_contador >= LOGIN_MAX_ATTEMPTS:
        bloqueio_ate = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        patch["locked_until"] = bloqueio_ate.isoformat()
        patch["failed_attempts"] = 0
    _atualizar_usuario(usuario["id"], patch)

def _registrar_login_sucesso(user_id: str):
    _atualizar_usuario(user_id, {
        "failed_attempts": 0,
        "locked_until": None,
        "last_login_at": datetime.now(timezone.utc).isoformat(),
    })

def _verificar_senha(senha_em_claro: str, hash_armazenado: str) -> bool:
    """Comparação constant-time via bcrypt."""
    if not senha_em_claro or not hash_armazenado:
        return False
    try:
        return bcrypt.checkpw(senha_em_claro.encode("utf-8"), hash_armazenado.encode("utf-8"))
    except Exception:
        return False

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    if request.method == "POST":
        if not _csrf_valid(request.form.get("csrf_token", "")):
            error = "Sessão expirou. Recarregue a página e tente de novo."
            return render_template("login.html", error=error), 400

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        usuario = _buscar_usuario(username)
        # Sempre roda bcrypt mesmo se usuário não existe — evita timing oracle
        senha_ok = False
        if usuario:
            if _usuario_travado(usuario):
                error = f"Conta temporariamente bloqueada. Aguarde {LOGIN_LOCKOUT_MINUTES} minutos."
                return render_template("login.html", error=error), 429
            senha_ok = _verificar_senha(password, usuario.get("password_hash", ""))
        else:
            # Hash dummy para gastar tempo equivalente
            bcrypt.checkpw(b"dummy", b"$2b$12$abcdefghijklmnopqrstuuMfYJg6xVUz5aB/V6r7fGNh3QAQk8lRm")

        if not senha_ok:
            if usuario:
                _registrar_falha_login(usuario)
            error = "Usuário ou senha incorretos."
            return render_template("login.html", error=error), 401

        # Senha OK — limpa estado anterior e marca pendência de 2FA
        session.clear()
        session.permanent = True
        session["pending_user_id"] = usuario["id"]
        session["pending_username"] = usuario["username"]
        session["pending_role"] = usuario.get("role") or "operador"

        if usuario.get("totp_enabled"):
            return redirect(url_for("verify_2fa"))
        # Primeiro acesso: força configurar 2FA antes de liberar o painel
        session["must_setup_2fa"] = True
        return redirect(url_for("setup_2fa"))

    return render_template("login.html", error=error)


@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    pending_id = session.get("pending_user_id")
    if not pending_id:
        return redirect(url_for("login_page"))

    error = None
    if request.method == "POST":
        if not _csrf_valid(request.form.get("csrf_token", "")):
            error = "Sessão expirou. Recarregue a página e tente de novo."
            return render_template("verify_2fa.html", error=error), 400

        codigo = (request.form.get("code", "") or "").strip().replace(" ", "")
        usuario = _buscar_usuario(session.get("pending_username", ""))
        if not usuario or not usuario.get("totp_secret"):
            session.clear()
            return redirect(url_for("login_page"))

        if _usuario_travado(usuario):
            error = f"Conta temporariamente bloqueada. Aguarde {LOGIN_LOCKOUT_MINUTES} minutos."
            return render_template("verify_2fa.html", error=error), 429

        totp = pyotp.TOTP(usuario["totp_secret"])
        if codigo and totp.verify(codigo, valid_window=1):
            _registrar_login_sucesso(usuario["id"])
            user_id = usuario["id"]
            username = usuario["username"]
            role = usuario.get("role") or "operador"
            session.clear()
            session.permanent = True
            session["logged_in"] = True
            session["user_id"] = user_id
            session["user"] = username
            session["role"] = role
            return redirect(url_for("index"))

        _registrar_falha_login(usuario)
        error = "Código inválido. Tente novamente."
        return render_template("verify_2fa.html", error=error), 401

    return render_template("verify_2fa.html", error=error)


@app.route("/setup-2fa", methods=["GET", "POST"])
def setup_2fa():
    """Primeiro acesso ou reconfiguração: gera segredo TOTP e exige confirmação."""
    pending_id = session.get("pending_user_id")
    autorizado = pending_id and session.get("must_setup_2fa")
    autorizado_por_login = session.get("logged_in")
    if not (autorizado or autorizado_por_login):
        return redirect(url_for("login_page"))

    user_id = pending_id or session.get("user_id")
    username = session.get("pending_username") or session.get("user")
    if not user_id or not username:
        session.clear()
        return redirect(url_for("login_page"))

    # Gera ou reaproveita segredo de uma tentativa anterior nesta sessão
    secret = session.get("setup_2fa_secret")
    if not secret:
        secret = pyotp.random_base32()
        session["setup_2fa_secret"] = secret

    error = None
    if request.method == "POST":
        if not _csrf_valid(request.form.get("csrf_token", "")):
            error = "Sessão expirou. Recarregue a página e tente de novo."
        else:
            codigo = (request.form.get("code", "") or "").strip().replace(" ", "")
            totp = pyotp.TOTP(secret)
            if codigo and totp.verify(codigo, valid_window=1):
                _atualizar_usuario(user_id, {
                    "totp_secret": secret,
                    "totp_enabled": True,
                })
                _registrar_login_sucesso(user_id)
                role = session.get("pending_role") or session.get("role") or "operador"
                session.clear()
                session.permanent = True
                session["logged_in"] = True
                session["user_id"] = user_id
                session["user"] = username
                session["role"] = role
                return redirect(url_for("index"))
            error = "Código inválido. Tente de novo."

    # Gera QR code SVG do otpauth URI
    issuer = "Politica Node Data"
    otp_uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(otp_uri, image_factory=factory, box_size=10, border=2)
    buf = BytesIO()
    img.save(buf)
    qr_svg = buf.getvalue().decode("utf-8")

    return render_template(
        "setup_2fa.html",
        username=username,
        secret=secret,
        qr_svg=qr_svg,
        error=error,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/")
def index():
    return render_template("data_node.html", user_role=(session.get("role") or "").lower())


@app.route("/api/events")
def get_events():
    """Retorna feedbacks com filtros e paginação"""
    categoria = request.args.get('categoria')
    regiao = request.args.get('regiao')
    prioridade = request.args.get('prioridade')
    status_filter = request.args.get('status')
    cidade = request.args.get('cidade')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Paginação direto no Supabase para performance
    if supabase:
        try:
            query = supabase.table('feedbacks').select('*', count='exact')

            if categoria:
                query = query.eq('category', categoria)
            if prioridade:
                query = query.eq('urgency', prioridade)
            if cidade:
                query = query.eq('city', cidade)
            if regiao:
                query = query.eq('region', regiao)
            if status_filter:
                query = query.eq('status', status_filter)

            query = query.order('id', desc=True).range(offset, offset + limit - 1)
            response = query.execute()

            total = response.count if response.count is not None else len(response.data)
            return jsonify({
                'data': response.data,
                'total': total,
                'limit': limit,
                'offset': offset
            })
        except Exception as e:
            print(f"Supabase paginated query error: {e}")

    # Fallback: filtro em memória
    feedbacks = get_feedbacks()
    if categoria:
        feedbacks = [f for f in feedbacks if f.get('category') == categoria]
    if regiao:
        feedbacks = [f for f in feedbacks if f.get('region') == regiao]
    if prioridade:
        feedbacks = [f for f in feedbacks if f.get('urgency') == prioridade]
    if status_filter:
        feedbacks = [f for f in feedbacks if f.get('status', 'aberto') == status_filter]
    if cidade:
        feedbacks = [f for f in feedbacks if f.get('city') == cidade]

    total = len(feedbacks)
    feedbacks = feedbacks[offset:offset + limit]
    return jsonify({
        'data': feedbacks,
        'total': total,
        'limit': limit,
        'offset': offset
    })


# Cache para AI Pulse
ai_pulse_cache = {"data": None, "timestamp": None}


@app.route("/api/ai-pulse")
def get_ai_pulse():
    """Retorna resumo inteligente do cenário político via IA"""
    global ai_pulse_cache

    now = datetime.utcnow()
    if ai_pulse_cache["data"] and ai_pulse_cache["timestamp"]:
        cache_age = (now - ai_pulse_cache["timestamp"]).total_seconds()
        if cache_age < 60:
            return jsonify(ai_pulse_cache["data"])

    feedbacks = get_feedbacks()
    result = generate_ai_pulse(feedbacks)
    result["updated_at"] = now.isoformat()
    result["feedbacks_count"] = len(feedbacks)

    ai_pulse_cache = {"data": result, "timestamp": now}

    return jsonify(result)


@app.route("/api/export/csv")
def export_csv():
    """Exporta feedbacks como CSV para download"""
    feedbacks = get_feedbacks()

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['id', 'message', 'category', 'urgency', 'timestamp', 'status', 'sender', 'name', 'region', 'city'])
    writer.writeheader()

    for fb in feedbacks:
        writer.writerow({
            'id': fb.get('id'),
            'message': fb.get('message'),
            'category': fb.get('category'),
            'urgency': fb.get('urgency'),
            'timestamp': fb.get('timestamp'),
            'status': fb.get('status', 'aberto'),
            'sender': fb.get('sender'),
            'name': fb.get('name'),
            'region': fb.get('region'),
            'city': fb.get('city', '')
        })

    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=feedbacks_politica.csv'
    }


@app.route("/api/export/json")
def export_json():
    """Exporta feedbacks como JSON para download"""
    feedbacks = get_feedbacks()
    return jsonify(feedbacks), 200, {
        'Content-Disposition': 'attachment; filename=feedbacks_politica.json'
    }


@app.route("/api/config", methods=["GET"])
def get_config_route():
    """Retorna config com contagens calculadas dinamicamente dos feedbacks"""
    config = get_config()
    feedbacks = get_feedbacks()

    category_counts = {}
    region_counts = {}
    city_counts = {}

    for fb in feedbacks:
        cat = fb.get('category', '')
        reg = fb.get('region', '')
        cit = fb.get('city', '')
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        if reg and reg != 'N/A':
            region_counts[reg] = region_counts.get(reg, 0) + 1
        if cit and cit != 'N/A':
            city_counts[cit] = city_counts.get(cit, 0) + 1

    for cat in config.get('categories', []):
        cat['count'] = category_counts.get(cat['name'], 0)

    for reg in config.get('regions', []):
        reg['count'] = region_counts.get(reg['name'], 0)

    # Adiciona cidades com contagens, ordenadas por volume
    cities_list = [{"name": name, "count": count} for name, count in city_counts.items()]
    cities_list.sort(key=lambda x: x['count'], reverse=True)
    config['cities'] = cities_list

    return jsonify(config)


@app.route("/api/insights")
def get_insights():
    """Retorna Top 3 Elogios e Problemas"""
    feedbacks = get_feedbacks()

    elogios = {}
    problemas = {}

    for fb in feedbacks:
        texto = fb.get('message', '') or fb.get('text', '')
        sentimento = fb.get('urgency', 'Neutro')
        categoria = fb.get('category', 'Outros')
        topic = fb.get('topic', texto[:20] + '...')

        display_text = topic if topic != 'Geral' else texto

        if sentimento == 'Positivo':
            if display_text not in elogios:
                elogios[display_text] = {'count': 0, 'topic': display_text}
            elogios[display_text]['count'] += 1

        if sentimento in ['Critico', 'Urgente', 'Crítico']:
            if display_text not in problemas:
                problemas[display_text] = {'count': 0, 'topic': display_text}
            problemas[display_text]['count'] += 1

    top_elogios = [v for k, v in sorted(elogios.items(), key=lambda x: x[1]['count'], reverse=True)[:3]]
    top_problemas = [v for k, v in sorted(problemas.items(), key=lambda x: x[1]['count'], reverse=True)[:3]]

    return jsonify({
        'top_elogios': top_elogios,
        'top_problemas': top_problemas
    })


@app.route("/api/analytics/top")
def get_top_analytics():
    """Returns data in the format data_node.html expects"""
    res = get_insights().get_json()
    return jsonify({
        "compliments": res['top_elogios'],
        "problems": res['top_problemas']
    })


# =============================================================================
# INSTAGRAM SCRAPER — Apify Integration
# Estratégia: perfil → últimos N posts → comentários de cada post → IA classifica
# Actor: apify/instagram-scraper  (docs: https://apify.com/apify/instagram-scraper)
# Configurar: APIFY_TOKEN no .env e no Coolify
# =============================================================================

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
_instagram_cache = {}
CACHE_TTL = 3600  # 1 hora


def _apify_run(actor_slug, payload, timeout=150):
    """Dispara um actor no Apify e retorna os itens do dataset resultante."""
    run_url = (
        f"https://api.apify.com/v2/acts/{actor_slug}/runs"
        f"?token={APIFY_TOKEN}&waitForFinish=120"
    )
    run_resp = requests.post(run_url, json=payload, timeout=timeout)
    run_resp.raise_for_status()
    dataset_id = run_resp.json().get("data", {}).get("defaultDatasetId")
    if not dataset_id:
        return []
    items_url = (
        f"https://api.apify.com/v2/datasets/{dataset_id}/items"
        f"?token={APIFY_TOKEN}&format=json&clean=true"
    )
    items_resp = requests.get(items_url, timeout=30)
    items_resp.raise_for_status()
    return items_resp.json()


_ALINHAMENTOS_VALIDOS = {
    "pro_candidato", "anti_candidato", "pro_adversario", "anti_adversario",
    "neutro", "spam", "off_topic"
}

# Pre-filtro: textos sem conteudo politico (so emojis, risos, URL puro, ruido)
# nao vao pra IA — economiza custo e evita classificacao errada por falta de contexto.
_URL_RE = re.compile(r"^\s*https?://\S+\s*$", re.IGNORECASE)
_RISOS_RE = re.compile(r"^[\sk!.,?😂🤣😅🤡🇧🇷👏🔥❤️🙏😍😎😘rsahe]+$", re.IGNORECASE)


def _eh_off_topic(texto):
    """Retorna True se o texto e claramente off_topic (sem conteudo politico classificavel)."""
    if not texto:
        return True
    t = texto.strip()
    if not t:
        return True
    if _URL_RE.match(t):
        return True
    # Texto reduzido a letras/digitos (sem emojis/pontuacao) tem menos de 4 chars
    significativo = re.sub(r"[^a-zA-ZÀ-ſ0-9]", "", t)
    if len(significativo) < 4:
        return True
    # Pattern de risos puros / emojis: "kkkk", "rsrs", "haha", "👏👏", etc
    if _RISOS_RE.match(t):
        return True
    return False


# Coerencia forcada: o alinhamento determina o sentimento RELATIVO ao candidato.
# A IA as vezes erra retornando anti_adversario + Negativo (deveria ser Positivo
# porque criticar adversario favorece o candidato). Aplicamos a regra no backend
# para garantir consistencia mesmo quando a IA escorrega.
_ALINHAMENTO_TO_SENTIMENTO = {
    "pro_candidato":   "Positivo",
    "anti_adversario": "Positivo",
    "anti_candidato":  "Negativo",
    "pro_adversario":  "Negativo",
    "neutro":          "Neutro",
    "spam":            "Neutro",
    "off_topic":       "Neutro",
}


def _classificar_chunk(textos, politico, adversarios=None):
    """
    Classifica um chunk de até 30 comentários em 1 chamada OpenAI.
    Quando `adversarios` é informado, o sentimento é RELATIVO ao candidato:
    apoio explícito a um adversário vira "Negativo" mesmo se o tom for entusiasmado.
    """
    default = {
        "sentimento": "Neutro",
        "categoria": "Propostas & Projetos",
        "alinhamento": "neutro",
        "adversario_mencionado": None,
        "nivel_hostilidade": 0,
        "sentimento_absoluto": "Neutro",
    }
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not textos:
        return [default.copy() for _ in textos]

    advs = [a.strip() for a in (adversarios or []) if a and a.strip()]
    advs_block = (
        f"Adversários do candidato (apoio a eles = NEGATIVO para o cliente; crítica a eles = POSITIVO para o cliente): "
        f"{', '.join(advs)}"
        if advs else
        "Nenhum adversário informado — classifique apenas pelo tom em relação ao candidato."
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        items_text = "\n".join([f"{i+1}. \"{t[:300]}\"" for i, t in enumerate(textos)])
        prompt = (
            f"Você é analista político SÊNIOR da campanha de {politico} (Minas Gerais, eleições 2026).\n\n"
            f"CONTEXTO POLÍTICO:\n"
            f"- {politico} é da ESQUERDA (alinhado ao PT/Lula).\n"
            f"- Adversários são da DIREITA (bolsonaristas): {', '.join(advs) if advs else 'Bolsonaro, Flávio Bolsonaro, Nikolas Ferreira'}.\n"
            f"- Pistas pró-candidato: '#lula', 'Lula 13', 'PT', '#pracimadelesPF', emojis 🔥👏 em apoio.\n"
            f"- Pistas pró-adversário: 'Bolsonaro 22', '🇧🇷22', '🇧🇷🇧🇷22', 'mito', 'capitão'.\n"
            f"- Sátiras/zombarias contra Bolsonaro (ex: 'BOLSOMASTER', '#bolsomaster', 'FamiLícia') = anti_adversario (FAVOREM o candidato).\n"
            f"- Referência a 'Dilma' ou 'tia' num post do {politico} pode ser ATAQUE indireto (Dilma é tia dele) = anti_candidato.\n\n"
            f"REGRA DO ALVO (a mais importante): identifique A QUEM o comentário se dirige.\n"
            f"- Pergunta retórica negativa ('Aprendeu a roubar?', 'Vai roubar também?') num post do {politico} = ataque AO {politico} = anti_candidato.\n"
            f"- Acusação genérica ('vocês são ladrões', 'que hipócrita') num post do {politico} = ataque AO candidato/aliados = anti_candidato.\n"
            f"- Crítica/zoeira a adversário ou família do adversário (ex: 'pai do Flávio preso', 'irmão do Vorcaro') = anti_adversario.\n"
            f"- Apoio explícito ao adversário ('FLAVIO PRESIDENTE!', 'Bolsonaro 22') = pro_adversario.\n\n"
            f"REGRA DE COERÊNCIA (sentimento DERIVADO do alinhamento):\n"
            f"- pro_candidato ou anti_adversario → sentimento Positivo\n"
            f"- anti_candidato ou pro_adversario → sentimento Negativo\n"
            f"- neutro/spam/off_topic → sentimento Neutro\n\n"
            "Responda SOMENTE com JSON array compacto (um objeto por comentário, mesma ordem):\n"
            '[{"sentimento":"Positivo|Negativo|Neutro",'
            '"sentimento_absoluto":"Positivo|Negativo|Neutro",'
            '"alinhamento":"pro_candidato|anti_candidato|pro_adversario|anti_adversario|neutro|spam|off_topic",'
            '"categoria":"...",'
            '"adversario_mencionado":"<nome ou null>",'
            '"nivel_hostilidade":0}]\n\n'
            "Demais regras:\n"
            "- sentimento_absoluto = tom do texto isolado, ignorando contexto político.\n"
            "- nivel_hostilidade: 0 (neutro), 1 (crítica branda), 2 (crítica forte), 3 (insulto/agressão).\n"
            "- adversario_mencionado: nome canônico citado ou null.\n"
            "- Categorias: Propostas & Projetos | Infraestrutura & Obras | Saúde & Educação | Segurança Pública | Transporte & Mobilidade | Meio Ambiente | Desenvolvimento Econômico | Assistência Social\n\n"
            f"EXEMPLOS (candidato={politico}):\n"
            '"FLAVIO BOLSONARO PRESIDENTE!" → {"sentimento":"Negativo","sentimento_absoluto":"Positivo","alinhamento":"pro_adversario","categoria":"Propostas & Projetos","adversario_mencionado":"Flávio Bolsonaro","nivel_hostilidade":1}\n'
            '"Aprendeu a roubar?" → {"sentimento":"Negativo","sentimento_absoluto":"Negativo","alinhamento":"anti_candidato","categoria":"Propostas & Projetos","adversario_mencionado":null,"nivel_hostilidade":2}\n'
            '"BOLSOMASTER, tudo em FamiLícia 🤡" → {"sentimento":"Positivo","sentimento_absoluto":"Negativo","alinhamento":"anti_adversario","categoria":"Propostas & Projetos","adversario_mencionado":"Bolsonaro","nivel_hostilidade":2}\n'
            '"Pai do Flávio preso, irmão do Vorcaro… coitado" → {"sentimento":"Positivo","sentimento_absoluto":"Negativo","alinhamento":"anti_adversario","categoria":"Propostas & Projetos","adversario_mencionado":"Flávio Bolsonaro","nivel_hostilidade":2}\n'
            '"Vai fazer igual a tia, não sabe nem 2+2" → {"sentimento":"Negativo","sentimento_absoluto":"Negativo","alinhamento":"anti_candidato","categoria":"Propostas & Projetos","adversario_mencionado":null,"nivel_hostilidade":2}\n'
            '"#Lula2026 e #flaviobolsonaronacadeia" → {"sentimento":"Positivo","sentimento_absoluto":"Positivo","alinhamento":"pro_candidato","categoria":"Propostas & Projetos","adversario_mencionado":"Flávio Bolsonaro","nivel_hostilidade":1}\n'
            '"A chapa tá esquentando 🔥🔥" → {"sentimento":"Positivo","sentimento_absoluto":"Positivo","alinhamento":"pro_candidato","categoria":"Propostas & Projetos","adversario_mencionado":null,"nivel_hostilidade":0}\n'
            '"kkkkk" → {"sentimento":"Neutro","sentimento_absoluto":"Neutro","alinhamento":"off_topic","categoria":"Propostas & Projetos","adversario_mencionado":null,"nivel_hostilidade":0}\n\n'
            f"Comentários a classificar:\n{items_text}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=len(textos) * 80 + 300,
            temperature=0
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        parsed = json.loads(raw)
        results = []
        for item in parsed:
            sentimento = item.get("sentimento", "Neutro")
            sentimento_abs = item.get("sentimento_absoluto", sentimento)
            alinhamento = (item.get("alinhamento") or "neutro").lower()
            categoria = item.get("categoria", "Propostas & Projetos")
            adv = item.get("adversario_mencionado")
            if isinstance(adv, str) and adv.strip().lower() in ("null", "none", ""):
                adv = None
            try:
                nivel = int(item.get("nivel_hostilidade", 0))
                nivel = max(0, min(3, nivel))
            except (TypeError, ValueError):
                nivel = 0
            if sentimento_abs not in ("Positivo", "Negativo", "Neutro"):
                sentimento_abs = "Neutro"
            if alinhamento not in _ALINHAMENTOS_VALIDOS:
                alinhamento = "neutro"
            # Coerencia forcada: o sentimento RELATIVO e DERIVADO do alinhamento.
            # Ignora o que a IA disse — se ela classificou anti_adversario, sentimento e
            # SEMPRE Positivo (criticar adversario favorece o candidato).
            sentimento = _ALINHAMENTO_TO_SENTIMENTO.get(alinhamento, "Neutro")
            results.append({
                "sentimento": sentimento,
                "categoria": categoria,
                "alinhamento": alinhamento,
                "adversario_mencionado": adv,
                "nivel_hostilidade": nivel,
                "sentimento_absoluto": sentimento_abs,
            })
        while len(results) < len(textos):
            results.append(default.copy())
        return results[:len(textos)]
    except Exception as e:
        print(f"❌ Batch classify error: {e}")
        return [default.copy() for _ in textos]


_OFF_TOPIC_CLASSIFICACAO = {
    "sentimento": "Neutro",
    "categoria": "Propostas & Projetos",
    "alinhamento": "off_topic",
    "adversario_mencionado": None,
    "nivel_hostilidade": 0,
    "sentimento_absoluto": "Neutro",
}


def _classificar_batch(textos, politico, chunk_size=30, adversarios=None):
    """
    Classifica comentários em batch, dividindo em chunks de 30 para não truncar tokens.
    Pre-filtra textos sem conteúdo político (URLs, risos, emojis puros) → off_topic
    sem chamar IA, economizando custo OpenAI e evitando classificações erradas.
    """
    if not textos:
        return []
    # Pre-filtro: separa indices que precisam de IA vs off_topic ja garantido
    classif_final = [None] * len(textos)
    indices_para_ia = []
    textos_para_ia = []
    for idx, t in enumerate(textos):
        if _eh_off_topic(t):
            classif_final[idx] = _OFF_TOPIC_CLASSIFICACAO.copy()
        else:
            indices_para_ia.append(idx)
            textos_para_ia.append(t)
    if not textos_para_ia:
        print(f"🧹 Todos os {len(textos)} comentários eram off_topic — sem chamada IA")
        return classif_final
    print(f"🧹 Pre-filtro: {len(textos) - len(textos_para_ia)} off_topic, {len(textos_para_ia)} vao pra IA")
    # Roda IA apenas nos sobreviventes
    ia_results = []
    for i in range(0, len(textos_para_ia), chunk_size):
        chunk = textos_para_ia[i:i + chunk_size]
        print(f"🤖 Classificando chunk {i//chunk_size + 1} ({len(chunk)} comentários)...")
        ia_results.extend(_classificar_chunk(chunk, politico, adversarios=adversarios))
    # Coloca de volta nos indices originais
    for ia_idx, original_idx in enumerate(indices_para_ia):
        classif_final[original_idx] = ia_results[ia_idx] if ia_idx < len(ia_results) else _OFF_TOPIC_CLASSIFICACAO.copy()
    return classif_final


def fetch_instagram_comments(username, politico, n_posts=5, comments_per_post=200, adversarios=None):
    """
    Fluxo dois passos via Apify:
      1. apify~instagram-scraper  → pega os N posts mais recentes do perfil
      2. apify~instagram-comment-scraper → pega TODOS os comentários de cada post
    Resultado cacheado por 1h para economizar crédito Apify.
    Quando `adversarios` é informado, a classificação é feita relativa ao candidato.
    """
    if not APIFY_TOKEN:
        return None

    username_clean = username.lstrip("@").strip()
    adv_key = "|".join(sorted((a or "").strip().lower() for a in (adversarios or []) if a)) or "noadv"
    chave = f"ig2_{username_clean}_{n_posts}_{adv_key}"
    agora_ts = time_now()

    if chave in _instagram_cache:
        if agora_ts - _instagram_cache[chave]["ts"] < CACHE_TTL:
            print(f"📸 Cache hit Instagram @{username_clean}")
            return _instagram_cache[chave]["data"]

    profile_url = f"https://www.instagram.com/{username_clean}/"
    print(f"📸 [1/2] Buscando posts de @{username_clean}...")

    try:
        posts = _apify_run("apify~instagram-scraper", {
            "directUrls": [profile_url],
            "resultsType": "posts",
            "resultsLimit": n_posts,
            "proxy": {"useApifyProxy": True}
        })

        if not posts:
            print(f"⚠️ Nenhum post encontrado para @{username_clean}")
            return None

        def _ts(p):
            t = p.get("timestamp") or p.get("taken_at_timestamp") or 0
            return t if isinstance(t, (int, float)) else 0

        posts_sorted = sorted(posts, key=_ts, reverse=True)[:n_posts]

        post_urls = []
        for p in posts_sorted:
            url = p.get("url") or (
                f"https://www.instagram.com/p/{p['shortCode']}/"
                if p.get("shortCode") else None
            )
            if url:
                post_urls.append(url)

        if not post_urls:
            print("⚠️ Não foi possível extrair URLs dos posts")
            return None

        print(f"✅ {len(post_urls)} posts. [2/2] Buscando todos os comentários...")

        raw_comments = _apify_run("apify~instagram-comment-scraper", {
            "directUrls": post_urls,
            "resultsLimit": comments_per_post,
        })

        if not raw_comments:
            print("⚠️ Nenhum comentário encontrado nos posts")
            return None

        print(f"✅ {len(raw_comments)} comentários brutos. Classificando em batch...")

        textos = [(c.get("text") or "").strip() for c in raw_comments]
        indices_validos = [i for i, t in enumerate(textos) if len(t) >= 5]
        textos_validos = [textos[i] for i in indices_validos]

        classificacoes = _classificar_batch(textos_validos, politico, adversarios=adversarios)
        cl_map = {indices_validos[i]: classificacoes[i] for i in range(len(indices_validos))}
        default_cl = {
            "sentimento": "Neutro",
            "categoria": "Propostas & Projetos",
            "alinhamento": "neutro",
            "adversario_mencionado": None,
            "nivel_hostilidade": 0,
            "sentimento_absoluto": "Neutro",
        }

        resultados = []
        for i, c in enumerate(raw_comments):
            texto = (c.get("text") or "").strip()
            if len(texto) < 5:
                continue

            data_c = c.get("timestamp") or datetime.utcnow().isoformat()
            if isinstance(data_c, (int, float)):
                from datetime import timezone as tz
                data_c = datetime.fromtimestamp(data_c, tz=tz.utc).isoformat()

            cl = cl_map.get(i, default_cl)
            resultados.append({
                "id": len(resultados) + 1,
                "fonte": "Instagram",
                "perfil_monitorado": politico,
                "tipo": "cliente",
                "usuario": c.get("ownerUsername", ""),
                "trecho": texto[:300],
                "sentimento": cl.get("sentimento", "Neutro"),
                "categoria": cl.get("categoria", "Propostas & Projetos"),
                "alinhamento": cl.get("alinhamento", "neutro"),
                "adversario_mencionado": cl.get("adversario_mencionado"),
                "nivel_hostilidade": cl.get("nivel_hostilidade", 0),
                "sentimento_absoluto": cl.get("sentimento_absoluto", cl.get("sentimento", "Neutro")),
                "post_url": c.get("postUrl") or "",
                "data": data_c,
            })

        print(f"✅ {len(resultados)} comentários prontos para @{username_clean}")
        _instagram_cache[chave] = {"ts": agora_ts, "data": resultados}
        save_json(LAST_COMMENTS_FILE, {
            "username": username_clean,
            "politico": politico,
            "comentarios": resultados
        })
        if supabase:
            try:
                rows = []
                for r in resultados:
                    rows.append({
                        "fonte": r.get("fonte", "Instagram"),
                        "contexto": politico,
                        "usuario": r.get("usuario", ""),
                        "texto": r.get("trecho", "")[:500],
                        "sentimento": r.get("sentimento", "Neutro"),
                        "categoria": r.get("categoria", "Geral"),
                        "alinhamento": r.get("alinhamento", "neutro"),
                        "adversario_mencionado": r.get("adversario_mencionado"),
                        "nivel_hostilidade": r.get("nivel_hostilidade", 0),
                        "sentimento_absoluto": r.get("sentimento_absoluto", r.get("sentimento", "Neutro")),
                        "post_url": r.get("post_url", ""),
                        "data_comentario": r.get("data"),
                        "origem": "radar"
                    })
                if rows:
                    supabase_admin.table('comentarios_politicos').insert(rows).execute()
                    print(f"💾 {len(rows)} comentários salvos no Supabase")
            except Exception as se:
                print(f"⚠️ Erro ao salvar no Supabase: {se}")
        print(f"💾 Comentários persistidos em last_ig_comments.json")
        return resultados

    except Exception as e:
        print(f"❌ Instagram scraper error: {e}")
        return None


# --- RADAR DE COMENTÁRIOS ---
@app.route("/api/radar-comentarios")
def radar_comentarios():
    """
    Com username: busca comentários reais do Instagram via Instaloader.
    Sem token ou username: retorna dados mock.
    """
    from datetime import timedelta, timezone
    periodo  = request.args.get('periodo', '7d')
    politico = request.args.get('politico', '')
    username = request.args.get('username', '')
    adversarios_raw = request.args.get('adversarios', '')
    try:
        adversarios = json.loads(adversarios_raw) if adversarios_raw else []
        if not isinstance(adversarios, list):
            adversarios = []
    except Exception:
        adversarios = [a.strip() for a in adversarios_raw.split(",") if a.strip()]

    # Dados reais do Instagram
    if APIFY_TOKEN and username:
        real_data = fetch_instagram_comments(username, politico or username, adversarios=adversarios)
        if real_data is not None:
            return jsonify(real_data)

    # Fallback: último scrape real salvo em disco (nunca dados fictícios)
    saved = load_json(LAST_COMMENTS_FILE, {})
    return jsonify(saved.get("comentarios", []))


@app.route("/api/radar-comentarios/cache")
def radar_comentarios_cache():
    """Retorna comentários salvos no Supabase SEM disparar Apify."""
    # Usa supabase_admin (service role) para bypassar RLS — sem isso o anon
    # retorna [] mesmo havendo registros, e cai no fallback de disco
    # (que não reflete reclassificações feitas direto no banco).
    client = supabase_admin or supabase
    if client:
        try:
            resp = client.table('comentarios_politicos') \
                .select('*') \
                .eq('origem', 'radar') \
                .order('created_at', desc=True) \
                .limit(500) \
                .execute()
            if resp.data:
                # Converter para formato esperado pelo frontend
                result = []
                for r in resp.data:
                    result.append({
                        "id": r["id"],
                        "fonte": r.get("fonte", "Instagram"),
                        "perfil_monitorado": r.get("contexto", ""),
                        "tipo": "cliente",
                        "usuario": r.get("usuario", ""),
                        "trecho": r.get("texto", ""),
                        "sentimento": r.get("sentimento", "Neutro"),
                        "categoria": r.get("categoria", "Geral"),
                        "alinhamento": r.get("alinhamento", "neutro"),
                        "adversario_mencionado": r.get("adversario_mencionado"),
                        "nivel_hostilidade": r.get("nivel_hostilidade", 0),
                        "sentimento_absoluto": r.get("sentimento_absoluto", r.get("sentimento", "Neutro")),
                        "post_url": r.get("post_url", ""),
                        "data": r.get("data_comentario") or r.get("created_at", ""),
                    })
                return jsonify(result)
        except Exception as e:
            print(f"⚠️ Supabase cache read error: {e}")
    # Fallback: disco
    saved = load_json(LAST_COMMENTS_FILE, {})
    return jsonify(saved.get("comentarios", []))


# --- COLETAR DADOS (Curated URL-based Scraping) ---

COLETAS_FILE = os.path.join(BASE_DIR, 'execution', 'coletas.json')

def _filtrar_qualidade(comentarios):
    """Filtra comentários de baixa qualidade antes de enviar à IA."""
    import re as _re
    resultado = []
    for c in comentarios:
        texto = (c.get("text") or "").strip()
        # Skip curtos demais
        if len(texto) < 10:
            continue
        # Skip apenas emojis
        sem_emojis = _re.sub(r'[\U00010000-\U0010ffff\u2600-\u27BF\u2300-\u23FF\uFE00-\uFE0F\u200d]+', '', texto, flags=_re.UNICODE).strip()
        if len(sem_emojis) < 5:
            continue
        # Skip spam patterns
        lower = texto.lower()
        spam_patterns = ['sigo de volta', 'segue de volta', 'sdv', 'follow back',
                         'link na bio', 'sigam meu', 'compre já', 'promoção',
                         'clique aqui', 'ganhe dinheiro', 'renda extra']
        if any(p in lower for p in spam_patterns):
            continue
        resultado.append(c)
    return resultado


@app.route("/api/coletar-dados", methods=["POST"])
def coletar_dados():
    """
    Recebe URLs de posts do Instagram → scraper Apify → filtra qualidade → IA classifica.
    Body: { "urls": ["https://instagram.com/p/..."], "contexto": "Candidato A" }
    """
    data = request.get_json(force=True) or {}
    urls = data.get("urls", [])
    contexto = data.get("contexto", "político")
    adversarios = data.get("adversarios") or []
    if not isinstance(adversarios, list):
        adversarios = []

    if not urls:
        return jsonify({"error": "Nenhuma URL fornecida"}), 400

    if not APIFY_TOKEN:
        return jsonify({"error": "APIFY_TOKEN não configurado no servidor"}), 500

    # Normalizar URLs
    post_urls = [u.strip() for u in urls if u.strip()]
    if not post_urls:
        return jsonify({"error": "URLs inválidas"}), 400

    try:
        print(f"📥 Coletar Dados: {len(post_urls)} URLs para analisar...")

        # Passo 1: Buscar comentários via Apify
        raw_comments = _apify_run("apify~instagram-comment-scraper", {
            "directUrls": post_urls,
            "resultsLimit": 150,
        })

        if not raw_comments:
            return jsonify({"error": "Nenhum comentário encontrado nessas URLs", "total_bruto": 0}), 200

        total_bruto = len(raw_comments)
        print(f"✅ {total_bruto} comentários brutos encontrados")

        # Passo 2: Filtro de qualidade
        filtrados = _filtrar_qualidade(raw_comments)
        total_filtrado = len(filtrados)
        descartados = total_bruto - total_filtrado
        print(f"🧹 Filtro: {total_filtrado} relevantes, {descartados} descartados")

        if not filtrados:
            return jsonify({
                "total_bruto": total_bruto,
                "descartados": descartados,
                "comentarios": [],
                "resumo": {"positivos": 0, "negativos": 0, "neutros": 0}
            })

        # Passo 3: Classificar com IA (relativo ao candidato, considerando adversários)
        textos = [(c.get("text") or "").strip() for c in filtrados]
        classificacoes = _classificar_batch(textos, contexto, adversarios=adversarios)

        # Passo 4: Montar resultados
        resultados = []
        for i, c in enumerate(filtrados):
            texto = (c.get("text") or "").strip()
            data_c = c.get("timestamp") or datetime.utcnow().isoformat()
            if isinstance(data_c, (int, float)):
                from datetime import timezone as tz
                data_c = datetime.fromtimestamp(data_c, tz=tz.utc).isoformat()

            cl = classificacoes[i] if i < len(classificacoes) else {
                "sentimento": "Neutro", "categoria": "Outro",
                "alinhamento": "neutro", "adversario_mencionado": None,
                "nivel_hostilidade": 0, "sentimento_absoluto": "Neutro",
            }
            resultados.append({
                "id": i + 1,
                "usuario": c.get("ownerUsername", ""),
                "texto": texto[:400],
                "sentimento": cl.get("sentimento", "Neutro"),
                "categoria": cl.get("categoria", "Outro"),
                "alinhamento": cl.get("alinhamento", "neutro"),
                "adversario_mencionado": cl.get("adversario_mencionado"),
                "nivel_hostilidade": cl.get("nivel_hostilidade", 0),
                "sentimento_absoluto": cl.get("sentimento_absoluto", cl.get("sentimento", "Neutro")),
                "post_url": c.get("postUrl") or "",
                "data": data_c,
                "likes": c.get("likesCount", 0),
            })

        # Resumo
        positivos = sum(1 for r in resultados if r["sentimento"] == "Positivo")
        negativos = sum(1 for r in resultados if r["sentimento"] == "Negativo")
        neutros = sum(1 for r in resultados if r["sentimento"] == "Neutro")

        # Categorias breakdown
        cats = {}
        for r in resultados:
            cat = r["categoria"]
            cats[cat] = cats.get(cat, 0) + 1

        resposta = {
            "total_bruto": total_bruto,
            "descartados": descartados,
            "total_analisados": total_filtrado,
            "comentarios": resultados,
            "resumo": {
                "positivos": positivos,
                "negativos": negativos,
                "neutros": neutros,
                "categorias": cats
            }
        }

        # Salvar coleta no histórico — Supabase + disco
        if supabase:
            try:
                # Salvar comentários individuais
                rows = []
                for r in resultados:
                    rows.append({
                        "fonte": "Instagram",
                        "contexto": contexto,
                        "usuario": r.get("usuario", ""),
                        "texto": r.get("texto", "")[:500],
                        "sentimento": r.get("sentimento", "Neutro"),
                        "categoria": r.get("categoria", "Geral"),
                        "alinhamento": r.get("alinhamento", "neutro"),
                        "adversario_mencionado": r.get("adversario_mencionado"),
                        "nivel_hostilidade": r.get("nivel_hostilidade", 0),
                        "sentimento_absoluto": r.get("sentimento_absoluto", r.get("sentimento", "Neutro")),
                        "post_url": r.get("post_url", ""),
                        "likes": r.get("likes", 0),
                        "data_comentario": r.get("data"),
                        "origem": "coleta"
                    })
                if rows:
                    supabase_admin.table('comentarios_politicos').insert(rows).execute()
                # Salvar metadados da coleta
                supabase_admin.table('coletas_historico').insert({
                    "urls": post_urls,
                    "contexto": contexto,
                    "total_bruto": total_bruto,
                    "total_analisados": total_filtrado,
                    "descartados": descartados,
                    "positivos": positivos,
                    "negativos": negativos,
                    "neutros": neutros,
                    "categorias": cats
                }).execute()
                print(f"💾 Coleta salva no Supabase: {len(rows)} comentários")
            except Exception as se:
                print(f"⚠️ Erro Supabase coleta: {se}")

        # Backup em disco
        coletas = load_json(COLETAS_FILE, [])
        coletas.insert(0, {
            "data": datetime.utcnow().isoformat(),
            "urls": post_urls,
            "contexto": contexto,
            "total_bruto": total_bruto,
            "total_analisados": total_filtrado,
            "resumo": resposta["resumo"]
        })
        save_json(COLETAS_FILE, coletas[:50])

        print(f"✅ Coleta concluída: {positivos}+ / {negativos}- / {neutros}~")
        return jsonify(resposta)

    except Exception as e:
        print(f"❌ Coletar dados error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/coletas")
def listar_coletas():
    """Retorna histórico de coletas do Supabase."""
    if supabase:
        try:
            resp = supabase.table('coletas_historico') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(50) \
                .execute()
            if resp.data:
                result = []
                for c in resp.data:
                    result.append({
                        "data": c.get("created_at", ""),
                        "urls": c.get("urls", []),
                        "contexto": c.get("contexto", ""),
                        "total_bruto": c.get("total_bruto", 0),
                        "total_analisados": c.get("total_analisados", 0),
                        "resumo": {
                            "positivos": c.get("positivos", 0),
                            "negativos": c.get("negativos", 0),
                            "neutros": c.get("neutros", 0)
                        }
                    })
                return jsonify(result)
        except Exception as e:
            print(f"⚠️ Supabase coletas read error: {e}")
    # Fallback: disco
    coletas = load_json(COLETAS_FILE, [])
    return jsonify(coletas)


@app.route("/api/coletas/detalhes")
def coleta_detalhes():
    """Retorna os comentários associados a um contexto de uma coleta prévia."""
    contexto = request.args.get('contexto')
    if not contexto:
        return jsonify({"error": "Contexto não informado"}), 400
        
    if supabase_admin:
        try:
            resp = supabase_admin.table('comentarios_politicos') \
                .select('*') \
                .eq('contexto', contexto) \
                .order('created_at', desc=True) \
                .limit(400) \
                .execute()
                
            resultados = []
            if resp.data:
                for r in resp.data:
                    resultados.append({
                        "usuario": r.get("usuario", ""),
                        "texto": r.get("texto", ""),
                        "sentimento": r.get("sentimento", "Neutro"),
                        "categoria": r.get("categoria", "Geral"),
                        "post_url": r.get("post_url", ""),
                        "likes": r.get("likes", 0),
                        "data": r.get("data_comentario", "") or r.get("created_at", "")
                    })
            
            # Recalcular estatísticas reais dos comentários retornados
            positivos = sum(1 for r in resultados if r["sentimento"] == "Positivo")
            negativos = sum(1 for r in resultados if r["sentimento"] == "Negativo")
            neutros = sum(1 for r in resultados if r["sentimento"] == "Neutro")
            
            cats = {}
            for r in resultados:
                cat = r["categoria"]
                cats[cat] = cats.get(cat, 0) + 1
                
            return jsonify({
                "comentarios": resultados,
                "total_bruto": len(resultados), # Total de comentários efetivamente salvos
                "descartados": 0,               # Não temos esse dado por contexto de forma agregada aqui
                "total_analisados": len(resultados),
                "resumo": {
                    "positivos": positivos,
                    "negativos": negativos,
                    "neutros": neutros,
                    "categorias": cats
                }
            })
        except Exception as e:
            print(f"⚠️ Erro ao buscar detalhes da coleta: {e}")
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "Sem conexão com Supabase para detalhes"}), 500


# --- RADAR DE NOTÍCIAS (Google News RSS) ---

_noticias_cache = {"data": [], "ts": 0}
_NOTICIAS_TTL = 1800  # 30 minutos

_PALAVRAS_NEGATIVAS = [
    "escândalo", "investigação", "preso", "prisão", "corrupção", "fraude",
    "denúncia", "suspeito", "acusado", "crime", "desvio", "improbidade",
    "afastado", "cassado", "reprovado", "rejeitado", "recusa", "polêmica",
    "crise", "protesto", "manifestação contra", "criticado", "ataque",
]
_PALAVRAS_POSITIVAS = [
    "aprovado", "aprovação", "inauguração", "inaugurou", "investimento",
    "conquista", "vitória", "eleito", "eleição", "benefício", "melhoria",
    "avanço", "projeto aprovado", "assinado", "entregue", "entrega",
    "celebra", "homenagem", "reconhecimento", "prêmio", "destaque",
    "parceria", "acordo", "acordo firmado", "sancionado",
]

def _classificar_sentimento(texto: str) -> str:
    t = texto.lower()
    neg = sum(1 for p in _PALAVRAS_NEGATIVAS if p in t)
    pos = sum(1 for p in _PALAVRAS_POSITIVAS if p in t)
    if neg > pos:
        return "Negativo"
    if pos > neg:
        return "Positivo"
    return "Neutro"

def _extrair_veiculo(source_title: str) -> str:
    """Normaliza o nome do veículo retornado pelo Google News."""
    mapa = {
        "g1": "G1", "globo": "G1", "folha": "Folha", "uol": "UOL",
        "estadão": "Estadão", "estadao": "Estadão", "r7": "R7",
        "terra": "Terra", "ig ": "IG", "correio braziliense": "Correio Braziliense",
        "o tempo": "O Tempo", "hoje em dia": "Hoje em Dia",
        "itatiaia": "Itatiaia", "estado de minas": "Estado de Minas",
        "em.com": "Estado de Minas", "diário do comércio": "Diário do Comércio",
        "agência minas": "Agência Minas", "cnn brasil": "CNN Brasil",
        "band": "Band", "record": "Record",
    }
    s = source_title.lower()
    for chave, nome in mapa.items():
        if chave in s:
            return nome
    # Retorna o original truncado
    return source_title[:25] if source_title else "Portal"

def _buscar_google_news(query: str, max_items: int = 15) -> list:
    url = (
        f"https://news.google.com/rss/search"
        f"?q={requests.utils.quote(query)}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt"
    )
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            titulo  = entry.get("title", "")
            resumo  = entry.get("summary", titulo)
            # Google News embute HTML no summary — limpa tags básicas
            resumo  = re.sub(r"<[^>]+>", "", resumo).strip()
            link    = entry.get("link", "#")
            # Data: struct_time → string YYYY-MM-DD
            pub = entry.get("published_parsed")
            if pub:
                data = datetime(*pub[:3]).strftime("%Y-%m-%d")
            else:
                data = datetime.now().strftime("%Y-%m-%d")
            veiculo = _extrair_veiculo(entry.get("source", {}).get("title", ""))
            sentimento = _classificar_sentimento(titulo + " " + resumo)
            items.append({
                "titulo": titulo,
                "resumo": resumo[:300] + ("…" if len(resumo) > 300 else ""),
                "veiculo": veiculo,
                "sentimento": sentimento,
                "url": link,
                "data": data,
                "politico": query,  # será sobrescrito pelo caller
            })
        return items
    except Exception as e:
        print(f"⚠️ Google News RSS erro ({query}): {e}")
        return []

def _carregar_noticias(politico_extra: str = "") -> list:
    global _noticias_cache
    agora = time_now()
    if agora - _noticias_cache["ts"] < _NOTICIAS_TTL and _noticias_cache["data"]:
        base = _noticias_cache["data"]
    else:
        queries_base = [
            ("Minas Gerais política", "MG — Política"),
            ("eleições 2026 Minas Gerais deputado federal", "Eleições 2026 MG"),
        ]
        todos = []
        for q, label in queries_base:
            items = _buscar_google_news(q, max_items=10)
            for it in items:
                it["politico"] = label
            todos.extend(items)
        # Remove duplicatas por URL
        vistos = set()
        dedup = []
        for n in todos:
            if n["url"] not in vistos:
                vistos.add(n["url"])
                dedup.append(n)
        dedup.sort(key=lambda x: x["data"], reverse=True)
        _noticias_cache = {"data": dedup, "ts": agora}
        base = dedup

    # Se há nome de político extra, busca em tempo real (sem cache)
    if politico_extra:
        extras = _buscar_google_news(politico_extra, max_items=10)
        for it in extras:
            it["politico"] = politico_extra
        vistos = {n["url"] for n in base}
        extras = [n for n in extras if n["url"] not in vistos]
        return extras + base

    return base

@app.route("/api/radar-noticias")
def radar_noticias():
    politico_param = request.args.get('politico', '').strip()
    sentimento     = request.args.get('sentimento', '').strip()

    noticias = _carregar_noticias(politico_param)

    if sentimento:
        noticias = [n for n in noticias if n["sentimento"] == sentimento]

    # Numera os IDs para o frontend
    for i, n in enumerate(noticias, 1):
        n["id"] = i

    return jsonify(noticias)


# --- TALKING POINTS IA ---
@app.route("/api/talking-points", methods=["POST"])
def talking_points():
    """Analisa comentários classificados e gera estratégia política com IA."""
    body        = request.get_json(silent=True) or {}
    comentarios = body.get("comentarios", [])
    politico    = body.get("politico", "o político")
    adversarios = body.get("adversarios") or []
    if not isinstance(adversarios, list):
        adversarios = []

    if not comentarios:
        return jsonify({"error": "Sem comentários para analisar"}), 400

    total  = len(comentarios)
    pos    = sum(1 for c in comentarios if c.get("sentimento") == "Positivo")
    neg    = sum(1 for c in comentarios if c.get("sentimento") == "Negativo")
    neutro = total - pos - neg

    pro_adv = sum(1 for c in comentarios if c.get("alinhamento") == "pro_adversario")
    cat_count = {}
    for c in comentarios:
        cat = c.get("categoria", "Outros")
        cat_count[cat] = cat_count.get(cat, 0) + 1
    top_cats = sorted(cat_count.items(), key=lambda x: x[1], reverse=True)[:5]

    neg_samples = [c["trecho"] for c in comentarios if c.get("sentimento") == "Negativo"][:8]
    pos_samples = [c["trecho"] for c in comentarios if c.get("sentimento") == "Positivo"][:5]
    pro_adv_samples = [c["trecho"] for c in comentarios if c.get("alinhamento") == "pro_adversario"][:5]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OpenAI não configurado"}), 500

    try:
        from openai import OpenAI
        client   = OpenAI(api_key=api_key)
        pct_pos    = pos    * 100 // total
        pct_neg    = neg    * 100 // total
        pct_neutro = neutro * 100 // total
        cats_text  = "\n".join([f"- {cat}: {cnt} menções" for cat, cnt in top_cats])
        neg_text   = "\n".join([f'"{t[:200]}"' for t in neg_samples])
        pos_text   = "\n".join([f'"{t[:200]}"' for t in pos_samples])
        adv_block = (
            f"Adversários monitorados: {', '.join(adversarios)}\n"
            f"Comentários promovendo adversários: {pro_adv} ({pro_adv * 100 // total if total else 0}%)"
            if adversarios else "Sem adversários cadastrados."
        )
        pro_adv_text = "\n".join([f'"{t[:200]}"' for t in pro_adv_samples]) or "(nenhum)"

        prompt = f"""Você é um estrategista político sênior. Analise os dados de comentários do Instagram do político {politico}.

MÉTRICAS:
- Total: {total} comentários  |  Positivos: {pos} ({pct_pos}%)  |  Negativos: {neg} ({pct_neg}%)  |  Neutros: {neutro} ({pct_neutro}%)
- {adv_block}

Top categorias mencionadas:
{cats_text}

Amostras de comentários negativos:
{neg_text}

Amostras de comentários positivos:
{pos_text}

Amostras de comentários promovendo adversários (infiltração no perfil do cliente):
{pro_adv_text}

Gere uma análise estratégica respondendo SOMENTE em JSON:
{{
  "situacao": "análise da situação atual em 2 frases objetivas. Se houver infiltração de adversários (>10%), aponte como prioridade",
  "talking_points": ["ponto prioritário 1", "ponto prioritário 2", "ponto prioritário 3"],
  "oportunidade": "uma oportunidade de comunicação específica identificada nos dados"
}}"""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return jsonify(json.loads(raw))
    except Exception as e:
        print(f"❌ Talking points error: {e}")
        return jsonify({"error": str(e)}), 500


# --- RADAR 360° — BRIEFING IA UNIFICADO (notícias + comentários) ---
_briefing_cache: dict = {}
_BRIEFING_TTL = 1800  # 30 minutos


def _radar_briefing_internal(
    politico: str,
    instagram: str = "",
    periodo: str = "7d",
    adversarios: list | None = None,
    force_refresh: bool = False,
) -> dict:
    """Versão pura (sem Flask) do briefing para uso interno (Marcos etc.).
    Levanta ValueError em erros conhecidos. Sempre retorna dict completo do briefing."""
    politico = (politico or "").strip()
    instagram = (instagram or "").strip().lstrip("@")
    if not isinstance(adversarios, list):
        adversarios = []
    adversarios = [a.strip() for a in (adversarios or []) if a and a.strip()]

    if not politico:
        raise ValueError("politico_obrigatorio")

    adv_key = "|".join(sorted(a.lower() for a in adversarios)) or "noadv"
    cache_key = f"{politico.lower()}|{instagram.lower()}|{periodo}|{adv_key}"
    now = time_now()
    if not force_refresh:
        cached = _briefing_cache.get(cache_key)
        if cached and (now - cached["ts"]) < _BRIEFING_TTL:
            return {**cached["data"], "cached": True, "cache_age_s": int(now - cached["ts"])}

    # 1) Notícias — reusa função existente com cache de 30min
    try:
        noticias_full = _carregar_noticias(politico) or []
    except Exception as e:
        print(f"[Briefing] Falha ao carregar notícias: {e}")
        noticias_full = []
    noticias = noticias_full[:25]

    # 2) Comentários Instagram — reusa scraper existente com cache de 1h
    comentarios = []
    if instagram and os.getenv("APIFY_TOKEN"):
        try:
            comentarios = (fetch_instagram_comments(instagram, politico, adversarios=adversarios) or [])[:200]
        except Exception as e:
            print(f"[Briefing] Falha ao buscar comentários: {e}")

    # 3) Estatísticas agregadas (com alinhamento se disponível)
    n_total = len(noticias)
    n_pos   = sum(1 for n in noticias if n.get("sentimento") == "Positivo")
    n_neg   = sum(1 for n in noticias if n.get("sentimento") == "Negativo")
    c_total = len(comentarios)
    c_pos   = sum(1 for c in comentarios if c.get("sentimento") == "Positivo")
    c_neg   = sum(1 for c in comentarios if c.get("sentimento") == "Negativo")
    c_pro_adv = sum(1 for c in comentarios if c.get("alinhamento") == "pro_adversario")
    c_anti_adv = sum(1 for c in comentarios if c.get("alinhamento") == "anti_adversario")

    # Contagem por adversário mencionado
    adv_mention_count: dict = {}
    for c in comentarios:
        adv = c.get("adversario_mencionado")
        if adv:
            adv_mention_count[adv] = adv_mention_count.get(adv, 0) + 1

    # Nível de infiltração adversária
    pct_pro_adv = (c_pro_adv * 100 // c_total) if c_total else 0
    if pct_pro_adv >= 25:
        infiltracao_nivel = "alto"
    elif pct_pro_adv >= 10:
        infiltracao_nivel = "medio"
    else:
        infiltracao_nivel = "baixo"

    cat_count: dict = {}
    for c in comentarios:
        cat = c.get("categoria", "Outros")
        cat_count[cat] = cat_count.get(cat, 0) + 1
    top_cats = sorted(cat_count.items(), key=lambda x: -x[1])[:6]

    # 4) Amostras para o prompt
    noticias_amostras = [
        f"- [{(n.get('veiculo') or '?')}|{(n.get('sentimento') or '?')}] {(n.get('titulo') or '')[:160]}"
        for n in noticias[:12]
    ]
    coment_neg = [(c.get("trecho") or "")[:180] for c in comentarios if c.get("sentimento") == "Negativo"][:8]
    coment_pos = [(c.get("trecho") or "")[:180] for c in comentarios if c.get("sentimento") == "Positivo"][:5]
    coment_pro_adv = [(c.get("trecho") or "")[:180] for c in comentarios if c.get("alinhamento") == "pro_adversario"][:5]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("openai_nao_configurado")

    if n_total == 0 and c_total == 0:
        raise ValueError("dados_insuficientes")

    noticias_block = "\n".join(noticias_amostras) or "(sem cobertura recente)"
    categorias_block = "\n".join(f"  - {cat}: {n}" for cat, n in top_cats) or "(sem dados)"
    criticas_block = "\n".join(f'  "{t}"' for t in coment_neg) or "(sem críticas registradas)"
    apoio_block = "\n".join(f'  "{t}"' for t in coment_pos) or "(sem apoio registrado)"
    pro_adv_block = "\n".join(f'  "{t}"' for t in coment_pro_adv) or "(nenhum)"
    adv_mention_block = "\n".join(f"  - {a}: {n} menções" for a, n in sorted(adv_mention_count.items(), key=lambda x: -x[1])[:5]) or "(nenhum adversário citado nos comentários)"
    adversarios_str = ", ".join(adversarios) if adversarios else "nenhum cadastrado"

    prompt = f"""Você é um estrategista político sênior em Minas Gerais. Sua missão é dar ao político {politico} um briefing executivo cruzando IMPRENSA e REDES SOCIAIS.

Adversários monitorados: {adversarios_str}
Infiltração de adversários no perfil: {pct_pro_adv}% ({c_pro_adv}/{c_total}) — nível {infiltracao_nivel}

═══ IMPRENSA — últimas {n_total} notícias monitoradas ═══
Positivas: {n_pos} | Negativas: {n_neg} | Neutras: {n_total - n_pos - n_neg}
Manchetes recentes:
{noticias_block}

═══ REDES SOCIAIS — {c_total} comentários no Instagram (sentimento RELATIVO ao candidato) ═══
Positivos: {c_pos} | Negativos: {c_neg} | Neutros: {c_total - c_pos - c_neg}
Pro-adversário: {c_pro_adv} | Anti-adversário: {c_anti_adv}

Adversários citados nos comentários:
{adv_mention_block}

Top categorias:
{categorias_block}

Amostras de críticas:
{criticas_block}

Amostras de apoio:
{apoio_block}

Amostras de infiltração adversária (comentários promovendo adversários no perfil do cliente):
{pro_adv_block}

Gere um briefing em JSON com esta estrutura EXATA:
{{
  "panorama": "3-4 frases descrevendo o momento atual do político, conectando o que sai na imprensa com a reação das redes. Se houver descompasso (imprensa positiva mas redes hostis) OU infiltração de adversários >10%, aponte como prioridade.",
  "temperatura": "fria|morna|aquecendo|quente",
  "infiltracao_adversario": {{
    "nivel": "baixo|medio|alto",
    "descricao": "Uma frase explicando o nível de presença dos adversários nos comentários do cliente, citando os mais frequentes",
    "recomendacao": "O que fazer estrategicamente sobre isso (responder, ignorar, mudar tom, etc) — 1-2 frases"
  }},
  "temas_quentes": [
    {{
      "tema": "Nome curto do tema (ex: Saúde Pública)",
      "relevancia": "alta|media|baixa",
      "sentimento_popular": "positivo|negativo|misto",
      "evidencia_imprensa": "1 frase resumindo o que a imprensa está dizendo sobre este tema (ou 'sem cobertura')",
      "evidencia_redes": "1 frase resumindo o que as redes estão dizendo (ou 'sem menções')",
      "o_que_falar": "Argumento ou posicionamento estratégico concreto que o político deve usar — 1-2 frases",
      "o_que_evitar": "O que NÃO dizer ou tom a evitar — 1 frase"
    }}
  ]
}}

REGRAS:
- Liste de 3 a 6 temas quentes, ordenados por relevância
- Seja específico: cite dados ("X% dos comentários", "Y notícias negativas") quando relevante
- NÃO invente fatos. Se faltar dado, escreva "dados insuficientes"
- Foco em ação: cada "o_que_falar" deve ser algo que o político pode dizer amanhã
- Se infiltração for alta/média, o panorama DEVE mencionar e infiltracao_adversario.recomendacao deve ser concreta
- Retorne APENAS o JSON, sem markdown."""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        data["meta"] = {
            "politico": politico,
            "instagram": instagram,
            "periodo": periodo,
            "adversarios": adversarios,
            "total_noticias": n_total,
            "total_comentarios": c_total,
            "noticias_pos": n_pos,
            "noticias_neg": n_neg,
            "comentarios_pos": c_pos,
            "comentarios_neg": c_neg,
            "comentarios_pro_adversario": c_pro_adv,
            "comentarios_anti_adversario": c_anti_adv,
            "pct_infiltracao": pct_pro_adv,
            "adversarios_citados": adv_mention_count,
            "gerado_em": datetime.utcnow().isoformat() + "Z",
        }
        _briefing_cache[cache_key] = {"ts": now, "data": data}
        return {**data, "cached": False}
    except json.JSONDecodeError as e:
        print(f"❌ Briefing IA parse error: {e}")
        raise ValueError(f"falha_json: {e}")
    except Exception as e:
        print(f"❌ Briefing IA error: {e}")
        raise


@app.route("/api/radar/briefing", methods=["POST"])
def radar_briefing():
    """Cruza notícias da imprensa + comentários do Instagram e gera briefing estratégico para o candidato."""
    body = request.get_json(silent=True) or {}
    try:
        result = _radar_briefing_internal(
            politico=body.get("politico", ""),
            instagram=body.get("instagram", ""),
            periodo=body.get("periodo", "7d"),
            adversarios=body.get("adversarios") or [],
            force_refresh=bool(body.get("force_refresh")),
        )
        return jsonify(result)
    except ValueError as ve:
        msg = str(ve)
        if msg == "politico_obrigatorio":
            return jsonify({"error": "Nome do político é obrigatório"}), 400
        if msg == "openai_nao_configurado":
            return jsonify({"error": "OpenAI não configurado"}), 500
        if msg == "dados_insuficientes":
            return jsonify({
                "error": "Sem dados suficientes para briefing",
                "detalhe": "Nenhuma notícia recente encontrada e nenhum comentário coletado do Instagram. Verifique o nome do político e o @ do Instagram."
            }), 400
        return jsonify({"error": f"Falha ao gerar briefing: {ve}"}), 500
    except Exception as e:
        return jsonify({"error": f"Falha ao gerar briefing: {e}"}), 500


@app.route("/api/radar/reclassificar-historico", methods=["POST"])
def radar_reclassificar_historico():
    """
    Re-roda o classificador nos comentários já salvos no Supabase usando o NOVO prompt
    (relativo ao candidato, com adversários). Útil para corrigir comentários antigos
    classificados com o prompt absoluto antigo (ex: 'FLAVIO BOLSONARO PRESIDENTE' marcado
    como Positivo quando deveria ser Negativo para Pedro Rousseff).
    """
    body        = request.get_json(silent=True) or {}
    politico    = (body.get("politico") or "").strip()
    adversarios = body.get("adversarios") or []
    limite      = int(body.get("limite", 500))
    if not isinstance(adversarios, list):
        adversarios = []
    adversarios = [a.strip() for a in adversarios if a and a.strip()]

    if not politico:
        return jsonify({"error": "Nome do político é obrigatório"}), 400
    if not supabase_admin:
        return jsonify({"error": "Supabase service role não configurado"}), 500

    try:
        # Usa supabase_admin (service role) para bypassar RLS na leitura — sem isso,
        # o anon client retorna [] mesmo havendo registros.
        resp = supabase_admin.table("comentarios_politicos") \
            .select("id, texto") \
            .ilike("contexto", politico) \
            .order("created_at", desc=True) \
            .limit(limite) \
            .execute()
        registros = resp.data or []
    except Exception as e:
        print(f"❌ Reclassificar: erro ao buscar histórico: {e}")
        return jsonify({"error": f"Erro Supabase: {e}"}), 500

    if not registros:
        return jsonify({
            "atualizados": 0,
            "total_lido": 0,
            "mensagem": f"Nenhum comentário encontrado para {politico}",
        })

    textos = [(r.get("texto") or "").strip() for r in registros]
    print(f"🔄 Reclassificando {len(textos)} comentários históricos de {politico}…")
    classificacoes = _classificar_batch(textos, politico, adversarios=adversarios)

    atualizados = 0
    erros = 0
    for r, cl in zip(registros, classificacoes):
        try:
            supabase_admin.table("comentarios_politicos").update({
                "sentimento": cl.get("sentimento", "Neutro"),
                "categoria": cl.get("categoria", "Propostas & Projetos"),
                "alinhamento": cl.get("alinhamento", "neutro"),
                "adversario_mencionado": cl.get("adversario_mencionado"),
                "nivel_hostilidade": cl.get("nivel_hostilidade", 0),
                "sentimento_absoluto": cl.get("sentimento_absoluto", cl.get("sentimento", "Neutro")),
            }).eq("id", r["id"]).execute()
            atualizados += 1
        except Exception as e:
            erros += 1
            if erros <= 3:
                print(f"⚠️ Falha ao atualizar id={r.get('id')}: {e}")

    # Invalida cache do briefing para forçar regerar com dados atualizados
    _briefing_cache.clear()

    custo_estimado_usd = round(len(textos) * 0.002, 3)  # estimativa para GPT-4o-mini
    return jsonify({
        "atualizados": atualizados,
        "total_lido": len(registros),
        "erros": erros,
        "custo_estimado_usd": custo_estimado_usd,
        "ts": datetime.utcnow().isoformat() + "Z",
    })


# =============================================================================
# VÍDEOS & PODCASTS — rotas
# =============================================================================

@app.route("/api/videos/analisar", methods=["POST"])
def api_videos_analisar():
    """Enfileira análise de URL pública (YouTube/podcast). Retorna {id, status}."""
    if not supabase_admin:
        return jsonify({"error": "supabase_indisponivel"}), 503
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    candidato = (body.get("candidato") or "").strip()
    tipo = (body.get("tipo") or "").strip()
    contexto_extra = (body.get("contexto_extra") or "").strip()[:2000] or None

    ok, motivo = validar_url_video(url)
    if not ok:
        return jsonify({"error": f"URL inválida: {motivo}"}), 400
    if not candidato:
        return jsonify({"error": "candidato obrigatório"}), 400
    if tipo not in ("adversario", "proprio"):
        return jsonify({"error": "tipo deve ser 'adversario' ou 'proprio'"}), 400

    # Dedup: se já existe análise para essa URL, retorna a existente
    try:
        existe = supabase_admin.table("videos_analises").select("id, status") \
            .eq("url", url).limit(1).execute()
        if existe.data:
            existing = existe.data[0]
            return jsonify({
                "id": existing["id"], "status": existing["status"],
                "duplicado": True,
            }), 200
    except Exception as e:
        print(f"[videos] erro dedup: {e}")

    # Cap mensal
    if VIDEOS_BUDGET_USD_MONTH > 0:
        gasto = _custo_mensal_videos_usd()
        if gasto >= VIDEOS_BUDGET_USD_MONTH:
            return jsonify({
                "error": "Limite mensal atingido",
                "gasto_usd": round(gasto, 2),
                "limite_usd": VIDEOS_BUDGET_USD_MONTH,
            }), 402

    plataforma = "youtube"
    if "spotify" in url:
        plataforma = "podcast"
    elif "podcasts.apple" in url:
        plataforma = "podcast"
    elif "libsyn" in url or "megaphone" in url:
        plataforma = "podcast"

    payload = {
        "url": url,
        "plataforma": plataforma,
        "tipo": tipo,
        "candidato": candidato[:200],
        "contexto_extra": contexto_extra,
        "status": "queued",
        "progresso": 0,
        "criado_por": session.get("user", "desconhecido")[:120],
    }
    try:
        res = supabase_admin.table("videos_analises").insert(payload).execute()
        criado = (res.data or [{}])[0]
        video_id = criado.get("id")
        if not video_id:
            return jsonify({"error": "Falha ao criar registro"}), 500
    except Exception as e:
        print(f"[videos] erro insert: {e}")
        return jsonify({"error": f"Erro Supabase: {e}"}), 500

    import threading
    threading.Thread(
        target=_processar_video_pipeline,
        args=(video_id, url),
        daemon=True,
        name=f"video-pipeline-{video_id}",
    ).start()

    return jsonify({"id": video_id, "status": "queued", "duplicado": False}), 201


@app.route("/api/videos", methods=["GET"])
def api_videos_listar():
    """Lista análises. Filtros: candidato, tipo, status, limit."""
    if not supabase_admin:
        return jsonify({"data": [], "total": 0}), 200
    try:
        candidato = (request.args.get("candidato") or "").strip()
        tipo = (request.args.get("tipo") or "").strip()
        status_f = (request.args.get("status") or "").strip()
        periodo = (request.args.get("periodo") or "").strip().lower()
        limit = min(int(request.args.get("limit", 50)), 200)

        # Lista sem campos pesados (transcricao, segmentos) — performance.
        cols = ("id, url, plataforma, tipo, candidato, titulo, canal, thumbnail_url, "
                "duracao_segundos, status, progresso, erro, sentimento_geral, tags, "
                "custo_usd, criado_em, finalizado_em")
        q = supabase_admin.table("videos_analises").select(cols)
        if candidato:
            q = q.eq("candidato", candidato)
        if tipo in ("adversario", "proprio"):
            q = q.eq("tipo", tipo)
        if status_f:
            q = q.eq("status", status_f)
        if periodo in ("hoje", "7d", "30d"):
            agora = datetime.utcnow()
            if periodo == "hoje":
                inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
            elif periodo == "7d":
                inicio = agora - timedelta(days=7)
            else:
                inicio = agora - timedelta(days=30)
            q = q.gte("criado_em", inicio.isoformat())
        q = q.order("criado_em", desc=True).limit(limit)
        res = q.execute()
        return jsonify({"data": res.data or [], "total": len(res.data or [])})
    except Exception as e:
        print(f"[videos] listar erro: {e}")
        return jsonify({"data": [], "total": 0, "error": str(e)}), 200


@app.route("/api/videos/<int:video_id>", methods=["GET"])
def api_videos_detalhe(video_id):
    """Retorna detalhes completos da análise (inclui transcrição e JSONBs)."""
    if not supabase_admin:
        return jsonify({"error": "supabase_indisponivel"}), 503
    try:
        res = supabase_admin.table("videos_analises").select("*") \
            .eq("id", video_id).limit(1).execute()
        if not res.data:
            return jsonify({"error": "não encontrado"}), 404
        return jsonify({"data": res.data[0]})
    except Exception as e:
        print(f"[videos] detalhe erro: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/videos/<int:video_id>/status", methods=["GET"])
def api_videos_status(video_id):
    """Endpoint leve para polling — só status, progresso e erro."""
    if not supabase_admin:
        return jsonify({"error": "supabase_indisponivel"}), 503
    try:
        res = supabase_admin.table("videos_analises") \
            .select("id, status, progresso, erro") \
            .eq("id", video_id).limit(1).execute()
        if not res.data:
            return jsonify({"error": "não encontrado"}), 404
        return jsonify(res.data[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/videos/<int:video_id>/regerar-respostas", methods=["POST"])
def api_videos_regerar_respostas(video_id):
    """Re-gera respostas_sugeridas sem retranscrever. Custo só de GPT-4o."""
    if not supabase_admin:
        return jsonify({"error": "supabase_indisponivel"}), 503
    try:
        res = supabase_admin.table("videos_analises") \
            .select("transcricao, transcricao_segmentos, candidato, tipo, contexto_extra, "
                    "pontos_atencao, custo_usd, custo_breakdown, duracao_segundos, tokens_consumidos") \
            .eq("id", video_id).limit(1).execute()
        if not res.data:
            return jsonify({"error": "não encontrado"}), 404
        v = res.data[0]
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not v.get("transcricao"):
        return jsonify({"error": "transcrição não disponível"}), 400

    pontos = v.get("pontos_atencao") or []
    if not pontos:
        return jsonify({"error": "sem pontos de atenção para gerar respostas"}), 400

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY ausente"}), 503
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        return jsonify({"error": f"openai client: {e}"}), 500

    timeline = _formatar_timeline(v.get("transcricao_segmentos") or [], max_chars=15000)
    body = request.get_json(silent=True) or {}
    ponto_ids = body.get("ponto_ids")
    if ponto_ids:
        ponto_ids_set = {int(x) for x in ponto_ids if str(x).isdigit()}
        pontos_filtrados = [p for p in pontos if int(p.get("id", 0)) in ponto_ids_set]
        if not pontos_filtrados:
            pontos_filtrados = pontos[:15]
    else:
        pontos_filtrados = pontos[:15]

    try:
        system, user = _prompt_respostas_sugeridas(
            v.get("tipo") or "proprio",
            v.get("candidato") or "Candidato",
            v.get("contexto_extra") or "",
            v.get("transcricao") or "",
            timeline,
            pontos_filtrados,
        )
        parsed, t_in, t_out = _chat_json(client, system, user, max_tokens=3000)
    except Exception as e:
        return jsonify({"error": f"GPT-4o erro: {e}"}), 500

    novas_respostas = parsed.get("itens") or []

    # Atualiza custo acumulado
    custo_adicional = calcular_custo_processamento(0, t_in, t_out)
    custo_atual = float(v.get("custo_usd") or 0)
    novo_custo_total = round(custo_atual + custo_adicional["total_usd"], 4)

    breakdown_atual = v.get("custo_breakdown") or {}
    breakdown_novo = {
        "whisper_usd": float(breakdown_atual.get("whisper_usd") or 0),
        "gpt_in_usd": round(float(breakdown_atual.get("gpt_in_usd") or 0) + custo_adicional["gpt_in_usd"], 4),
        "gpt_out_usd": round(float(breakdown_atual.get("gpt_out_usd") or 0) + custo_adicional["gpt_out_usd"], 4),
        "total_usd": novo_custo_total,
        "total_brl": round(novo_custo_total * 5.0, 2),
    }
    tokens_atual = v.get("tokens_consumidos") or {}
    tokens_novo = {
        "input": int(tokens_atual.get("input") or 0) + t_in,
        "output": int(tokens_atual.get("output") or 0) + t_out,
        "total": int(tokens_atual.get("input") or 0) + int(tokens_atual.get("output") or 0) + t_in + t_out,
    }

    _videos_update_status(
        video_id, "done",
        respostas_sugeridas=novas_respostas,
        custo_usd=novo_custo_total,
        custo_breakdown=breakdown_novo,
        tokens_consumidos=tokens_novo,
    )
    return jsonify({
        "success": True,
        "respostas": novas_respostas,
        "tokens_consumidos": {"input": t_in, "output": t_out},
        "custo_adicional_usd": custo_adicional["total_usd"],
    })


@app.route("/api/videos/<int:video_id>", methods=["DELETE"])
def api_videos_deletar(video_id):
    """Remove análise. Requer role admin/coordenador."""
    if not supabase_admin:
        return jsonify({"error": "supabase_indisponivel"}), 503
    role = (session.get("role") or "").lower()
    if role not in ("admin", "coordenador"):
        return jsonify({"error": "sem permissão"}), 403
    try:
        supabase_admin.table("videos_analises").delete().eq("id", video_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/videos/orcamento", methods=["GET"])
def api_videos_orcamento():
    """KPI: gasto mensal vs cap."""
    gasto = _custo_mensal_videos_usd()
    return jsonify({
        "gasto_usd": round(gasto, 2),
        "limite_usd": VIDEOS_BUDGET_USD_MONTH,
        "disponivel_usd": round(max(0.0, VIDEOS_BUDGET_USD_MONTH - gasto), 2),
        "esgotado": VIDEOS_BUDGET_USD_MONTH > 0 and gasto >= VIDEOS_BUDGET_USD_MONTH,
    })


# --- HELPER: GET ACTIVE FEEDBACK ---
def get_active_feedback(remote_jid):
    """Verifica se existe um chamado Aberto ou Em Andamento para este número"""
    if not supabase:
        return None

    try:
        response = supabase.table('feedbacks')\
            .select("*")\
            .eq('sender', remote_jid)\
            .in_('status', ['aberto', 'em_andamento'])\
            .order('id', desc=True)\
            .limit(1)\
            .execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Erro ao buscar feedback ativo (sender): {e}")
        try:
            response = supabase.table('feedbacks')\
                .select("*")\
                .eq('remoteJid', remote_jid)\
                .in_('status', ['aberto', 'em_andamento'])\
                .order('id', desc=True)\
                .limit(1)\
                .execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e2:
            print(f"Erro dados ativo fallback: {e2}")
        return None


def append_to_feedback(feedback_id, old_message, new_content, new_region=None, new_urgency=None, new_sentiment=None, new_category=None):
    """Adiciona mensagem ao feedback existente e atualiza classificações se necessário"""
    if not supabase:
        return False

    try:
        from datetime import timezone, timedelta
        tz_brt = timezone(timedelta(hours=-3))
        hora_local = datetime.now(tz_brt).strftime('%H:%M')
        updated_message = f"{old_message}\n\n[Atualização {hora_local}]: {new_content}"
        data = {'message': updated_message}

        if new_region and new_region != "N/A":
            data['region'] = new_region
        if new_urgency:
            data['urgency'] = new_urgency
        if new_sentiment:
            data['sentiment'] = new_sentiment
        if new_category and new_category != "Geral" and new_category != "N/A":
            data['category'] = new_category

        supabase_admin.table('feedbacks').update(data).eq('id', feedback_id).execute()
        print(f"✅ Feedback {feedback_id} atualizado com sucesso.")
        return True
    except Exception as e:
        print(f"❌ Erro ao atualizar feedback {feedback_id}: {e}")
        return False


def _normalizar_telefone_jid(valor: str) -> str:
    """Mantem apenas digitos para comparar telefones/JIDs de WhatsApp."""
    return re.sub(r'\D+', '', str(valor or ''))


def _variantes_telefone_jid(valor: str) -> set[str]:
    """Gera variacoes comuns para numeros BR com/sem 55 e com/sem nono digito."""
    digitos = _normalizar_telefone_jid(valor)
    if not digitos:
        return set()

    nacional = digitos[2:] if digitos.startswith("55") and len(digitos) > 11 else digitos
    variantes_nacionais = {nacional}

    if len(nacional) == 11 and nacional[2] == "9":
        variantes_nacionais.add(nacional[:2] + nacional[3:])
    elif len(nacional) == 10:
        variantes_nacionais.add(nacional[:2] + "9" + nacional[2:])

    variantes = {digitos}
    for numero in variantes_nacionais:
        if not numero:
            continue
        variantes.add(numero)
        variantes.add(f"55{numero}")

    return {item for item in variantes if len(item) >= 10}


def _jid_para_envio(telefone: str) -> str:
    """Converte telefone cadastrado em identificador aceito pela Evolution API.

    Aceita os formatos comuns BR:
      - "(44) 91236866"      → 554491236866
      - "(44) 9 1236-8666"   → 5544912368666
      - "+55 (44) 91236866"  → 554491236866
      - "554491236866"       → 554491236866 (mantém)

    Se vier só DDD + número (10 ou 11 dígitos), prepende automaticamente
    o código do país BR (55) para garantir envio via Evolution API.
    """
    texto = str(telefone or '').strip()
    if '@' in texto:
        return texto
    digitos = _normalizar_telefone_jid(texto)
    if len(digitos) in (10, 11):  # DDD + número sem código do país
        digitos = "55" + digitos
    return digitos


def _mascarar_telefone(valor: str) -> str:
    """Mascara telefone para logs e interface sem expor dado pessoal completo."""
    digitos = _normalizar_telefone_jid(valor)
    if len(digitos) <= 6:
        return "***"
    return f"{digitos[:4]}***{digitos[-2:]}"


# ============================================================
# Score de prioridade do operador (Operação Local)
# Fórmula: (influencia × 10) + (peso_funcao × 5) + (votos_cidade ÷ 1000)
# Documentada no painel "Como o score funciona" do dashboard.
# ============================================================
PESOS_FUNCAO_OPERADOR = {
    "prefeito": 10,
    "vice-prefeito": 9,
    "vereador": 8,
    "secretario": 7,
    "lideranca-comunitaria": 6,
    "cabo-eleitoral": 5,
    "influenciador": 4,
    "voluntario": 3,
}

FUNCOES_OPERADOR_LABEL = {
    "prefeito": "Prefeito",
    "vice-prefeito": "Vice-prefeito",
    "vereador": "Vereador",
    "secretario": "Secretário",
    "lideranca-comunitaria": "Liderança comunitária",
    "cabo-eleitoral": "Cabo eleitoral",
    "influenciador": "Influenciador",
    "voluntario": "Voluntário",
}

# SLA por faixa de score (em horas) — usado no badge URGENTE
FAIXAS_SCORE_OPERADOR = [
    {"min": 100, "nivel": "maxima", "label": "Prioridade máxima", "sla_horas": 2},
    {"min": 60, "nivel": "alta", "label": "Prioridade alta", "sla_horas": 4},
    {"min": 30, "nivel": "media", "label": "Prioridade média", "sla_horas": 8},
    {"min": 0, "nivel": "normal", "label": "Prioridade normal", "sla_horas": 24},
]


def _normalizar_funcao_chave(valor) -> str:
    """Converte rótulo livre em chave canônica de função."""
    if not valor:
        return "voluntario"
    chave = str(valor).strip().lower()
    if chave in PESOS_FUNCAO_OPERADOR:
        return chave
    # Aceita rótulos humanos comuns
    normalizado = _normalizar_texto(chave).replace(" ", "-")
    if normalizado in PESOS_FUNCAO_OPERADOR:
        return normalizado
    # Heurística para casos legados (campo livre)
    for k in PESOS_FUNCAO_OPERADOR:
        if k.split("-")[0] in normalizado:
            return k
    return "voluntario"


def calcular_score_operador(funcao_chave: str, influencia, votos_cidade) -> float:
    """Score de prioridade do operador. Fórmula auditável:
    score = (influencia × 10) + (peso_funcao × 10) + (votos_cidade ÷ 1000)
    Exemplo: prefeito (peso 10) + 8★ + cidade 5k votos = 80 + 100 + 5 = 185 pts.
    """
    peso_funcao = PESOS_FUNCAO_OPERADOR.get(_normalizar_funcao_chave(funcao_chave), 3)
    try:
        infl = int(influencia or 0)
    except (TypeError, ValueError):
        infl = 0
    infl = max(1, min(10, infl)) if infl else 1
    try:
        votos = max(0, int(votos_cidade or 0))
    except (TypeError, ValueError):
        votos = 0
    return round((infl * 10) + (peso_funcao * 10) + (votos / 1000), 2)


def faixa_score_operador(score) -> dict:
    """Devolve a faixa (nível, label, SLA em horas) para um score numérico."""
    try:
        valor = float(score or 0)
    except (TypeError, ValueError):
        valor = 0
    for faixa in FAIXAS_SCORE_OPERADOR:
        if valor >= faixa["min"]:
            return faixa
    return FAIXAS_SCORE_OPERADOR[-1]


# Cache em memória da base eleitoral demo (recarrega só uma vez)
_BASE_ELEITORAL_CACHE = {"data": None}


def carregar_base_eleitoral_demo() -> dict:
    """Carrega static/base_eleitoral_demo.json (votos Lula 2022 fictícios por município MG)."""
    if _BASE_ELEITORAL_CACHE["data"] is not None:
        return _BASE_ELEITORAL_CACHE["data"]
    caminho = os.path.join(BASE_DIR, "static", "base_eleitoral_demo.json")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            payload = json.load(f)
        _BASE_ELEITORAL_CACHE["data"] = payload
        return payload
    except Exception as e:
        print(f"[operacao] Falha ao carregar base_eleitoral_demo: {e}")
        return {"cidades": {}, "total_municipios": 0}


def carregar_base_eleitoral_unificada() -> dict:
    """Une a base do Mapa Eleitoral (votos_*.json — fonte cadastrada) com a base
    demo (fallback) em um único dicionário por cidade. Mapa Eleitoral tem prioridade.

    Retorna: { cidade_nome: {
        cidade, regiao, polo, votos_total, votos_candidato_a, votos_candidato_b, origem
    } }
    """
    cidades = {}

    # 1) Mapa Eleitoral — fonte cadastrada (prioritária)
    try:
        from os.path import getmtime
        # _carregar_votos_eleitorais já está definida mais abaixo no módulo.
        # Aqui usamos referência tardia para evitar problemas de ordem.
        base_mapa = _carregar_votos_eleitorais()
        for dados in base_mapa.values():
            nome = dados.get("cidade")
            if not nome:
                continue
            votos_a = int(dados.get("votos_candidato_a") or 0)
            votos_b = int(dados.get("votos_candidato_b") or 0)
            cidades[nome] = {
                "cidade": nome,
                "regiao": dados.get("regiao_eleitoral") or "",
                "polo": dados.get("polo") or "",
                "votos_total": votos_a + votos_b,
                "votos_candidato_a": votos_a,
                "votos_candidato_b": votos_b,
                "origem": "mapa_eleitoral",
            }
    except Exception as e:
        print(f"[operacao] Falha ao consolidar Mapa Eleitoral: {e}")

    # 2) Base demo — complementa cidades não cobertas pelo Mapa
    try:
        base_demo = carregar_base_eleitoral_demo()
        for nome, dados in (base_demo.get("cidades") or {}).items():
            if nome in cidades:
                continue
            cidades[nome] = {
                "cidade": nome,
                "regiao": dados.get("regiao") or "",
                "polo": "",
                "votos_total": int(dados.get("votos_lula_2022") or 0),
                "votos_candidato_a": 0,
                "votos_candidato_b": 0,
                "origem": "demo",
            }
    except Exception as e:
        print(f"[operacao] Falha ao mesclar base demo: {e}")

    return cidades


def buscar_votos_cidade(cidade_nome: str):
    """Retorna votos cadastrados para a cidade (Mapa Eleitoral ou demo)."""
    if not cidade_nome:
        return None
    base = carregar_base_eleitoral_unificada()
    if cidade_nome in base:
        return base[cidade_nome].get("votos_total")
    alvo = _normalizar_texto(cidade_nome)
    for nome, dados in base.items():
        if _normalizar_texto(nome) == alvo:
            return dados.get("votos_total")
    return None


def _operadores_demo_padrao():
    """Seed visual usado quando ainda nao ha operadores reais cadastrados."""
    return [{
        "id": 1,
        "nome": "Operador de Campo Demo",
        "telefone": "55DDDNUMERO",
        "telefone_mascarado": "55***00",
        "jid": "",
        "funcao": "Coordenador regional",
        "cidade_base": "Cidade exemplo",
        "regiao": "Regiao de demonstracao",
        "status": "ativo",
        "notas": "Substitua pelo numero real antes da reuniao.",
        "criado_em": datetime.utcnow().isoformat(),
        "demo": True,
    }]


def _normalizar_operador(row: dict) -> dict:
    """Padroniza o registro do operador para API e comparacao."""
    row = dict(row or {})
    telefone = row.get("telefone") or row.get("jid") or ""
    jid = row.get("jid") or telefone
    row["telefone"] = telefone
    row["jid"] = jid
    row["telefone_normalizado"] = _normalizar_telefone_jid(jid or telefone)
    row["telefone_mascarado"] = _mascarar_telefone(jid or telefone)
    row["status"] = row.get("status") or "ativo"

    # Score de prioridade (Operação Local)
    funcao_chave = row.get("funcao_chave") or _normalizar_funcao_chave(row.get("funcao"))
    row["funcao_chave"] = funcao_chave
    row["funcao_label"] = FUNCOES_OPERADOR_LABEL.get(funcao_chave, row.get("funcao") or "Operador")
    row["peso_funcao"] = PESOS_FUNCAO_OPERADOR.get(funcao_chave, 3)
    try:
        row["influencia"] = max(1, min(10, int(row.get("influencia") or 1)))
    except (TypeError, ValueError):
        row["influencia"] = 1
    try:
        row["votos_cidade"] = max(0, int(row.get("votos_cidade") or 0))
    except (TypeError, ValueError):
        row["votos_cidade"] = 0
    row["especificacao"] = (row.get("especificacao") or "").strip()
    row["score"] = calcular_score_operador(funcao_chave, row["influencia"], row["votos_cidade"])
    faixa = faixa_score_operador(row["score"])
    row["score_nivel"] = faixa["nivel"]
    row["score_label"] = faixa["label"]
    row["sla_horas"] = faixa["sla_horas"]
    return row


def _serializar_operador_cache(operador: dict) -> dict:
    """Remove campos derivados antes de salvar operadores em cache local."""
    row = dict(operador or {})
    row.pop("telefone_normalizado", None)
    row.pop("telefone_mascarado", None)
    return row


def _sincronizar_cache_operadores(operadores: list[dict]) -> None:
    """Mantem um espelho local dos operadores para tolerar falhas temporarias do banco."""
    try:
        serializados = [_serializar_operador_cache(op) for op in operadores]
        cache_atual = load_json(OPERADORES_FILE, [])
        if json.dumps(cache_atual, ensure_ascii=False, sort_keys=True) != json.dumps(serializados, ensure_ascii=False, sort_keys=True):
            save_json(OPERADORES_FILE, serializados)
    except Exception as e:
        print(f"[operacao] Falha ao sincronizar cache local de operadores: {e}")


def listar_operadores_campo(incluir_demo=True):
    """Lista operadores de campo cadastrados no Supabase ou fallback local."""
    operadores = []
    if supabase_admin:
        try:
            res = supabase_admin.table("operadores_campo").select("*").order("criado_em", desc=True).execute()
            operadores = res.data or []
        except Exception as e:
            print(f"[operacao] Supabase operadores indisponivel: {e}")

    if not operadores:
        operadores = load_json(OPERADORES_FILE, [])

    operadores = [_normalizar_operador(op) for op in operadores]
    if operadores:
        _sincronizar_cache_operadores(operadores)
    if not operadores and incluir_demo:
        return _operadores_demo_padrao()
    return operadores


def salvar_operador_campo(payload: dict) -> dict:
    """Cadastra operador de campo, com fallback local se o banco nao existir."""
    nome = (payload.get("nome") or "").strip()
    telefone = (payload.get("telefone") or payload.get("jid") or "").strip()
    if not nome or not telefone:
        raise ValueError("nome_e_telefone_obrigatorios")

    telefone_norm = _normalizar_telefone_jid(telefone)
    if len(telefone_norm) < 10:
        raise ValueError("telefone_invalido")
    variantes_telefone = _variantes_telefone_jid(telefone)
    if any(_variantes_telefone_jid(op.get("jid") or op.get("telefone")) & variantes_telefone for op in listar_operadores_campo(incluir_demo=False)):
        raise ValueError("telefone_ja_cadastrado")

    funcao_chave = _normalizar_funcao_chave(payload.get("funcao_chave") or payload.get("funcao"))
    funcao_label = FUNCOES_OPERADOR_LABEL.get(funcao_chave, (payload.get("funcao") or "Operador de campo").strip()[:120])
    try:
        influencia = max(1, min(10, int(payload.get("influencia") or 1)))
    except (TypeError, ValueError):
        influencia = 1
    try:
        votos_cidade = max(0, int(payload.get("votos_cidade") or 0))
    except (TypeError, ValueError):
        votos_cidade = 0
    especificacao = (payload.get("especificacao") or "").strip()[:160]
    score_calculado = calcular_score_operador(funcao_chave, influencia, votos_cidade)

    operador = {
        "nome": nome[:120],
        "telefone": telefone_norm,
        "jid": _jid_para_envio(telefone),
        "funcao": funcao_label[:120],
        "funcao_chave": funcao_chave,
        "especificacao": especificacao,
        "influencia": influencia,
        "votos_cidade": votos_cidade,
        "score": score_calculado,
        "cidade_base": (payload.get("cidade_base") or "").strip()[:120],
        "regiao": (payload.get("regiao") or "").strip()[:120],
        "status": payload.get("status") if payload.get("status") in ("ativo", "pausado") else "ativo",
        "notas": (payload.get("notas") or "").strip()[:500],
        "criado_em": datetime.utcnow().isoformat(),
        "atualizado_em": datetime.utcnow().isoformat(),
    }

    if supabase_admin:
        try:
            res = supabase_admin.table("operadores_campo").insert(operador).execute()
            if res.data:
                operador_salvo = _normalizar_operador(res.data[0])
                cache_local = [_normalizar_operador(op) for op in load_json(OPERADORES_FILE, [])]
                cache_filtrado = [
                    op for op in cache_local
                    if str(op.get("id")) != str(operador_salvo.get("id"))
                    and not (_variantes_telefone_jid(op.get("jid") or op.get("telefone")) & _variantes_telefone_jid(operador_salvo.get("jid") or operador_salvo.get("telefone")))
                ]
                _sincronizar_cache_operadores([operador_salvo, *cache_filtrado])
                return operador_salvo
        except Exception as e:
            print(f"[operacao] Falha ao salvar operador no Supabase: {e}")

    operadores = [_normalizar_operador(op) for op in load_json(OPERADORES_FILE, [])]
    operador["id"] = max([int(op.get("id") or 0) for op in operadores] or [0]) + 1
    operadores.insert(0, operador)
    save_json(OPERADORES_FILE, operadores)
    return _normalizar_operador(operador)


def buscar_operador_por_jid(remote_jid: str):
    """Retorna operador ativo pelo JID/telefone, sem usar o numero do deputado."""
    variantes_remetente = _variantes_telefone_jid(remote_jid)
    if not variantes_remetente:
        return None

    try:
        from gabinete_agent import is_deputado
        if is_deputado(remote_jid):
            return None
    except Exception:
        pass

    for operador in listar_operadores_campo(incluir_demo=False):
        if operador.get("status") != "ativo":
            continue
        variantes_operador = _variantes_telefone_jid(operador.get("jid") or operador.get("telefone"))
        if variantes_operador & variantes_remetente:
            return operador
    return None


def _extrair_cidade_operacao(texto: str) -> str:
    """Extrai cidade da atualizacao de campo por padroes simples de WhatsApp."""
    texto = texto or ""
    padroes = [
        r"cidade\s*[:\-]\s*([A-Za-zÀ-ÿ' .-]{3,60})",
        r"munic[ií]pio\s*[:\-]\s*([A-Za-zÀ-ÿ' .-]{3,60})",
        r"\bem\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ' -]{2,45}?)(?=\s+(?:fiz|fez|realiz|teve|tem|principal|com|no|na|bairro|reuni|evento|demanda|hoje|ontem|amanh)|[,.]|$)",
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, flags=re.IGNORECASE)
        if match:
            cidade = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
            if cidade:
                return cidade[:80]

    texto_norm = _normalizar_texto(texto)
    if texto_norm:
        for item in _carregar_cidades_estaticas().values():
            cidade = item.get("cidade")
            if cidade and f" {_normalizar_texto(cidade)} " in f" {texto_norm} ":
                return cidade
    return ""


def _classificar_tipo_operacao(texto: str) -> str:
    """Classifica o tipo principal da mensagem de campo."""
    t = _normalizar_texto(texto)
    if _detectar_pedido_financeiro_operacao(texto).get("detectado"):
        return "pedido_financeiro"
    if any(p in t for p in ("reuniao", "reunimos", "encontro", "liderancas")):
        return "reuniao"
    if any(p in t for p in ("evento", "agenda", "visita", "carreata", "adesivaco")):
        return "evento"
    if any(p in t for p in ("lideranca", "vereador", "prefeito", "pastor", "presidente")):
        return "lideranca"
    if any(p in t for p in ("adversario", "oposicao", "concorrente")):
        return "adversario"
    if any(p in t for p in ("demanda", "reclamacao", "problema", "pedido", "cobranca")):
        return "demanda"
    return "relato"


def _detectar_pedido_financeiro_operacao(texto: str) -> dict:
    """Identifica pedidos de verba/recurso sem exigir novas colunas no banco."""
    texto_original = str(texto or "")
    t = _normalizar_texto(texto_original)
    if not t:
        return {"detectado": False, "valor": "", "label": ""}

    palavras_financeiras = (
        "verba",
        "dinheiro",
        "recurso",
        "recursos",
        "orcamento",
        "apoio financeiro",
        "pix",
        "pagar",
        "pagamento",
        "reembolso",
        "combustivel",
        "gasolina",
        "diaria",
        "custo",
        "custear",
    )
    padrao_valor = r"(?:r\$\s*)?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?\s*(?:mil|milhao|milhoes|reais)?|\d+\s*mil"
    tem_valor_monetario = bool(re.search(r"r\$\s*\d|\d+\s*mil(?:\s+reais)?|\d+\s+reais", texto_original, flags=re.IGNORECASE))
    detectado = any(p in t for p in palavras_financeiras) or tem_valor_monetario
    if not detectado:
        return {"detectado": False, "valor": "", "label": ""}

    valor = ""
    match = re.search(padrao_valor, texto_original, flags=re.IGNORECASE)
    if match:
        valor = re.sub(r"\s+", " ", match.group(0)).strip(" .,-")[:40]

    label = "Pedido financeiro"
    if valor:
        label = f"Pedido financeiro: {valor}"
    return {"detectado": True, "valor": valor, "label": label}


def _extrair_tema_operacao(texto: str) -> str:
    """Extrai tema politico dominante por palavras-chave."""
    temas = _detectar_temas_operacao(texto)
    return temas[0] if temas else "Mobilizacao local"


def _detectar_temas_operacao(texto: str, limite: int = 3) -> list[str]:
    """Detecta os temas mais fortes da mensagem de campo sem depender da ordem das palavras."""
    t = _normalizar_texto(texto)
    if not t:
        return ["Mobilizacao local"]

    catalogo = [
        ("Estradas rurais", ("estrada rural", "estradas rurais", "cascalho", "patrolamento", "mata burro", "ponte rural", "acesso rural", "ponte")),
        ("Saude", ("fila de exame", "fila de exames", "cirurgia", "hospital", "ubs", "posto de saude", "saude", "exame", "exames", "samu", "medico")),
        ("Infraestrutura", ("asfalto", "buraco", "obra", "iluminacao", "energia", "calcamento", "pavimentacao")),
        ("Educacao", ("transporte escolar", "creche", "professor", "professores", "aluno", "alunos", "escola")),
        ("Agricultura", ("agricultor", "agricultores", "produtor", "produtores", "safra", "cooperativa", "cooperativas")),
        ("Seguranca", ("seguranca", "roubo", "policia", "violencia", "furto")),
        ("Emprego e renda", ("emprego", "empresa", "industria", "comercio", "renda")),
        ("Saneamento", ("saneamento", "esgoto", "coleta de lixo", "agua", "abastecimento")),
    ]

    temas_pontuados = []
    for indice, (tema, palavras) in enumerate(catalogo):
        score = 0
        primeira_posicao = None
        spans_usados = []
        for palavra in sorted(palavras, key=lambda item: len(_normalizar_texto(item)), reverse=True):
            termo = _normalizar_texto(palavra)
            if not termo or termo not in t:
                continue
            inicio = t.find(termo)
            fim = inicio + len(termo)
            if any(not (fim <= span_inicio or inicio >= span_fim) for span_inicio, span_fim in spans_usados):
                continue
            spans_usados.append((inicio, fim))
            peso = 3 if " " in termo else 1
            score += peso
            if primeira_posicao is None or inicio < primeira_posicao:
                primeira_posicao = inicio
        if score > 0:
            temas_pontuados.append((score, primeira_posicao if primeira_posicao is not None else 9999, indice, tema))

    if not temas_pontuados:
        return ["Mobilizacao local"]

    temas_pontuados.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [tema for _, _, _, tema in temas_pontuados[:max(1, limite)]]


def _extrair_quantidade_pessoas(texto: str):
    """Captura quantidade de pessoas/liderancas mencionada no relato."""
    match = re.search(r"(\d{1,4})\s+(?:pessoas|lideran[cç]as|moradores|participantes|apoiadores|cabos)", texto or "", re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extrair_liderancas(texto: str) -> str:
    """Captura mencoes simples a liderancas locais."""
    encontrados = []
    padrao = r"\b(vereador|prefeito|pastor|lideran[cç]a|presidente|secret[aá]rio|deputado)\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ' -]{2,40})"
    for cargo, nome in re.findall(padrao, texto or "", flags=re.IGNORECASE):
        nome_limpo = " ".join(nome.strip(" .,-").split()[:3])
        encontrados.append(f"{cargo.title()} {nome_limpo}")
    return ", ".join(dict.fromkeys(encontrados))[:300]


def _sentimento_operacao(texto: str) -> str:
    """Resume o tom do relato de campo."""
    t = _normalizar_texto(texto)
    if any(p in t for p in ("reclam", "problema", "critico", "urgente", "bravo", "cobranca")):
        return "atencao"
    if any(p in t for p in ("apoio", "positivo", "bem recebido", "aprovou", "animado")):
        return "positivo"
    return "neutro"


def _proxima_acao_operacao(tipo: str, tema: str, liderancas: str, sentimento: str, texto: str = "") -> str:
    """Gera uma recomendacao objetiva para o coordenador."""
    tema_norm = _normalizar_texto(tema)
    financeiro = tipo == "pedido_financeiro" or _detectar_pedido_financeiro_operacao(texto).get("detectado")
    if financeiro:
        return "Confirmar valor, finalidade, responsavel local e comprovantes antes de aprovar qualquer recurso."
    if tema_norm in ("estradas rurais", "infraestrutura"):
        return "Pedir localizacao exata, fotos e lideranca responsavel para transformar em tarefa com evidencia."
    if tema_norm == "saude":
        return "Levantar unidade ou servico afetado, volume de pessoas e urgencia para preparar resposta do gabinete."
    if liderancas:
        return "Confirmar telefone da lideranca, forca local e proximo contato com agenda definida."
    if tipo in ("reuniao", "evento"):
        return "Solicitar lista de presentes, fotos e tres demandas prioritarias para virar plano de acao."
    if sentimento == "atencao":
        return f"Tratar {tema.lower()} como pauta sensivel e preparar retorno local."
    return "Acompanhar a cidade e pedir nova atualizacao ao operador em ate 7 dias."


def montar_atualizacao_campo(texto: str, operador: dict, remote_jid: str, origem="whatsapp") -> dict:
    """Transforma uma mensagem de WhatsApp em atualizacao estruturada de campo."""
    cidade = _extrair_cidade_operacao(texto) or operador.get("cidade_base") or "Cidade nao informada"
    tipo = _classificar_tipo_operacao(texto)
    temas_detectados = _detectar_temas_operacao(texto)
    tema = temas_detectados[0] if temas_detectados else _extrair_tema_operacao(texto)
    liderancas = _extrair_liderancas(texto)
    sentimento = _sentimento_operacao(texto)
    quantidade = _extrair_quantidade_pessoas(texto)
    resumo = re.sub(r"\s+", " ", texto or "").strip()
    resumo = resumo[:260] + ("..." if len(resumo) > 260 else "")

    return {
        "operador_id": operador.get("id"),
        "operador_nome": operador.get("nome") or "Operador",
        "operador_jid": remote_jid,
        "cidade": cidade,
        "regiao": operador.get("regiao") or "",
        "tipo": tipo,
        "tema_principal": tema,
        "resumo": resumo,
        "quantidade_pessoas": quantidade,
        "liderancas": liderancas,
        "sentimento": sentimento,
        "proxima_acao": _proxima_acao_operacao(tipo, tema, liderancas, sentimento, texto),
        "mensagem_original": texto,
        "origem": origem,
        "criada_em": datetime.utcnow().isoformat(),
    }


def _enriquecer_atualizacao_campo(item: dict) -> dict:
    """Completa campos derivados das atualizacoes sem exigir mudanca de schema."""
    row = dict(item or {})
    texto_base = row.get("mensagem_original") or row.get("resumo") or ""
    financeiro = _detectar_pedido_financeiro_operacao(texto_base)
    row["pedido_financeiro"] = bool(financeiro.get("detectado"))
    row["pedido_financeiro_valor"] = financeiro.get("valor") or ""
    row["pedido_financeiro_label"] = financeiro.get("label") or ""
    if financeiro.get("detectado"):
        row["tipo"] = "pedido_financeiro"
    temas_detectados = _detectar_temas_operacao(texto_base)
    row["temas_detectados"] = temas_detectados
    if temas_detectados:
        row["tema_principal"] = temas_detectados[0]
    elif not row.get("tema_principal"):
        row["tema_principal"] = "Mobilizacao local"
    row["proxima_acao"] = _proxima_acao_operacao(
        row.get("tipo") or "relato",
        row.get("tema_principal") or "Mobilizacao local",
        row.get("liderancas") or "",
        row.get("sentimento") or "neutro",
        texto_base,
    )
    return row


def salvar_atualizacao_campo(atualizacao: dict) -> dict:
    """Salva atualizacao de campo no Supabase ou fallback local."""
    if supabase_admin:
        try:
            res = supabase_admin.table("operacao_local_atualizacoes").insert(atualizacao).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"[operacao] Falha ao salvar atualizacao no Supabase: {e}")

    atualizacoes = load_json(OPERACAO_FILE, [])
    registro = dict(atualizacao)
    registro["id"] = max([int(a.get("id") or 0) for a in atualizacoes] or [0]) + 1
    atualizacoes.insert(0, registro)
    save_json(OPERACAO_FILE, atualizacoes)
    return registro


def listar_atualizacoes_campo(limit=80):
    """Lista atualizacoes recentes de campo."""
    limit = max(1, min(int(limit or 80), 300))
    atualizacoes = []
    if supabase_admin:
        try:
            res = supabase_admin.table("operacao_local_atualizacoes").select("*").order("criada_em", desc=True).limit(limit).execute()
            atualizacoes = res.data or []
        except Exception as e:
            print(f"[operacao] Supabase atualizacoes indisponivel: {e}")

    if not atualizacoes:
        atualizacoes = load_json(OPERACAO_FILE, [])[:limit]
    return [_enriquecer_atualizacao_campo(item) for item in atualizacoes]


def buscar_atualizacao_campo_por_id(atualizacao_id) -> dict | None:
    """Busca atualizacao de campo por id (Supabase ou fallback local)."""
    if not atualizacao_id:
        return None
    id_str = str(atualizacao_id)
    if supabase_admin:
        try:
            res = supabase_admin.table("operacao_local_atualizacoes").select("*").eq("id", atualizacao_id).limit(1).execute()
            if res.data:
                return _enriquecer_atualizacao_campo(res.data[0])
        except Exception as e:
            print(f"[operacao] Supabase busca atualizacao falhou: {e}")

    for item in load_json(OPERACAO_FILE, []):
        if str(item.get("id")) == id_str:
            return _enriquecer_atualizacao_campo(item)
    return None


def salvar_mensagem_operacao(registro: dict) -> dict:
    """Persiste mensagem enviada ao operador (Supabase ou fallback local)."""
    payload = dict(registro)
    if supabase_admin:
        try:
            res = supabase_admin.table("operacao_local_mensagens").insert(payload).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"[operacao] Falha ao salvar mensagem no Supabase: {e}")

    mensagens = load_json(OPERACAO_MSGS_FILE, [])
    payload["id"] = max([int(m.get("id") or 0) for m in mensagens] or [0]) + 1
    mensagens.insert(0, payload)
    save_json(OPERACAO_MSGS_FILE, mensagens)
    return payload


def listar_mensagens_operacao(atualizacao_id=None, limit=60) -> list:
    """Lista mensagens enviadas a operadores, filtrando opcionalmente por atualizacao."""
    limit = max(1, min(int(limit or 60), 200))
    mensagens = []
    if supabase_admin:
        try:
            query = supabase_admin.table("operacao_local_mensagens").select("*").order("enviada_em", desc=True).limit(limit)
            if atualizacao_id:
                query = query.eq("atualizacao_id", atualizacao_id)
            res = query.execute()
            mensagens = res.data or []
        except Exception as e:
            print(f"[operacao] Supabase mensagens indisponivel: {e}")

    if not mensagens:
        todas = load_json(OPERACAO_MSGS_FILE, [])
        if atualizacao_id:
            id_str = str(atualizacao_id)
            todas = [m for m in todas if str(m.get("atualizacao_id")) == id_str]
        mensagens = todas[:limit]
    return mensagens


def handle_operacao_local(text: str, remote_jid: str, push_name: str):
    """Processa atualizacao de operador cadastrado e confirma pelo WhatsApp."""
    operador = buscar_operador_por_jid(remote_jid)
    if not operador:
        return False

    atualizacao = montar_atualizacao_campo(text, operador, remote_jid)
    salvo = salvar_atualizacao_campo(atualizacao)
    print(f"[operacao] Atualizacao salva operador={operador.get('nome')} telefone={_mascarar_telefone(remote_jid)} cidade={salvo.get('cidade')}")

    resposta = (
        f"✅ Atualização registrada em *{salvo.get('cidade')}*.\n"
        f"• Tema: *{salvo.get('tema_principal')}*\n"
        f"• Tipo: {salvo.get('tipo')}\n"
        f"• Próxima ação: {salvo.get('proxima_acao')}\n\n"
        "_O painel Operação Local já foi atualizado._"
    )
    send_whatsapp_message(remote_jid, resposta)
    return True


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
    except Exception:
        return jsonify({"error": "invalid_json"}), 400

    event_type = data.get("type") or data.get("event")

    if event_type in ["message", "messages.upsert", "MESSAGES_UPSERT"]:
        msg_data = data.get("data", {})
        print(f"DEBUG [Política]: Incoming event {event_type}")
        print(f"DEBUG [Política]: Payload message keys: {list(msg_data.get('message', {}).keys())}")

        key = msg_data.get("key", {})

        if key.get("fromMe"):
            return jsonify({"status": "ignored_self"}), 200

        remote_jid = key.get("remoteJid")
        push_name = msg_data.get("pushName", "Cidadão")
        message_content = msg_data.get("message", {})

        text = message_content.get("conversation") or message_content.get("extendedTextMessage", {}).get("text")

        native_transcription = message_content.get("transcription")
        audio_msg = message_content.get("audioMessage")

        # Audio Processing
        if not text and audio_msg and remote_jid:
            seconds = audio_msg.get("seconds", 0)
            if seconds > 35:
                print(f"[AUDIO] Ignored too long: {seconds}s")
                send_whatsapp_message(remote_jid, "⚠️ O seu áudio é muito longo. Por favor, envie áudios de no máximo 35 segundos para que eu possa processar.")
                return jsonify({"status": "audio_too_long"}), 200

            if native_transcription:
                print(f"[AUDIO] Using native transcription: {native_transcription}")
                text = native_transcription
            else:
                print(f"[AUDIO] Manual transcription for {seconds}s audio...")

                import base64
                audio_data = None

                if "base64" in message_content:
                    try:
                        audio_data = base64.b64decode(message_content["base64"])
                    except Exception as e:
                        print(f"❌ Error decoding base64 from message_content: {e}")

                if not audio_data and "base64" in msg_data:
                    try:
                        audio_data = base64.b64decode(msg_data["base64"])
                    except Exception as e:
                        print(f"❌ Error decoding base64 from msg_data: {e}")

                if not audio_data:
                    print(f"[AUDIO] No base64 found, attempting download...")
                    audio_data = download_evolution_media(remote_jid, msg_data.get("key", {}).get("id"))

                if audio_data:
                    print(f"[AUDIO] Audio data ready ({len(audio_data)} bytes). Starting Whisper...")
                    text = transcribe_audio(audio_data)
                    if not text:
                        print(f"❌ Whisper transcription returned None")
                        send_whatsapp_message(remote_jid, "❌ Não consegui transcrever seu áudio. Por favor, tente novamente ou digite sua mensagem.")
                        return jsonify({"status": "transcription_failed"}), 200
                else:
                    print(f"❌ Media download failed from Evolution")
                    send_whatsapp_message(remote_jid, "❌ Erro ao baixar o áudio. Verifique a configuração da Evolution API.")
                    return jsonify({"status": "download_failed"}), 200

        if text and remote_jid:
            # GABINETE (deputado) — roteia antes das regras de cidadão
            try:
                from gabinete_agent import is_deputado, handle_gabinete
                if is_deputado(remote_jid):
                    print(f"[GABINETE] Mensagem do Deputado {remote_jid}")
                    handle_gabinete(text, remote_jid)
                    return jsonify({"status": "gabinete_handled"}), 200
            except Exception as e:
                print(f"[GABINETE] Erro no roteamento: {e}")

            # OPERACAO LOCAL (cabos/coordenadores) — fluxo separado do gabinete e do cidadão
            try:
                if handle_operacao_local(text, remote_jid, push_name):
                    return jsonify({"status": "operacao_local_handled"}), 200
            except Exception as e:
                print(f"[operacao] Erro no roteamento: {e}")

            # SPAM PROTECTION
            if len(text.strip()) < MIN_MESSAGE_LENGTH:
                print(f"[SPAM] Message too short ({len(text)} chars): {text}")
                return jsonify({"status": "ignored_too_short"}), 200

            if is_emoji_only(text):
                print(f"[SPAM] Emoji-only message ignored: {text}")
                return jsonify({"status": "ignored_emoji_only"}), 200

            if is_rate_limited(remote_jid):
                print(f"[RATE-LIMIT] {remote_jid} exceeded {RATE_LIMIT_MAX} msgs in {RATE_LIMIT_WINDOW}s")
                send_whatsapp_message(remote_jid, "⚠️ Você já enviou várias mensagens recentes. Aguarde alguns minutos antes de enviar outra.")
                return jsonify({"status": "rate_limited"}), 200

            feedbacks = get_feedbacks()

            # Deduplication
            msg_hash = hashlib.md5(f"{text}{remote_jid}".encode()).hexdigest()
            existing_hashes = {hashlib.md5(f"{fb.get('message', '')}{fb.get('sender', '')}".encode()).hexdigest() for fb in feedbacks}

            if msg_hash in existing_hashes:
                print(f"[CACHE] Ignored Duplicate: {text}")
                return jsonify({"status": "ignored_duplicate"}), 200

            # THREADING LOGIC
            active_feedback = get_active_feedback(remote_jid)

            if active_feedback:
                print(f"[THREADING] Found active feedback {active_feedback.get('id')} for {remote_jid}")

                ia_result = classificar_com_ia(text)

                new_region = ia_result.get('regiao') if ia_result else None
                new_urgency = ia_result.get('sentimento') if ia_result else None
                new_category = ia_result.get('categoria') if ia_result else None

                # Lógica de upgrade de categoria
                current_category = active_feedback.get('category', 'N/A')
                update_category = None
                if (not current_category or current_category in ['N/A', 'Geral', 'Propostas & Projetos']) and (new_category and new_category not in ['N/A', 'Geral', 'Propostas & Projetos']):
                    print(f"[THREADING] Upgrading Category: {current_category} -> {new_category}")
                    update_category = new_category

                current_region = active_feedback.get('region', 'N/A')
                update_region = None
                if (not current_region or current_region == 'N/A') and (new_region and new_region != 'N/A'):
                    update_region = new_region

                current_urgency = active_feedback.get('urgency', 'Neutro')
                update_urgency = None
                update_sentiment = None

                priority_map = {"Critico": 3, "Urgente": 2, "Positivo": 1, "Neutro": 0}
                current_prio = priority_map.get(current_urgency, 0)
                new_prio = priority_map.get(new_urgency, 0)

                if new_prio > current_prio:
                    print(f"[THREADING] Upgrading Urgency: {current_urgency} -> {new_urgency}")
                    update_urgency = new_urgency
                    update_sentiment = "Positivo" if new_urgency == "Positivo" else ("Negativo" if new_urgency in ["Critico", "Urgente"] else "Neutro")

                append_to_feedback(active_feedback['id'], active_feedback['message'], text, update_region, update_urgency, update_sentiment, update_category)

                current_urgency_disp = update_urgency or current_urgency
                urgency_note = ''
                if update_urgency in ['Critico', 'Urgente']:
                    urgency_note = 'A prioridade do chamado foi elevada. Informe ao cidadão que o gestor político foi alertado.'

                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    reply_prompt = f"""Você é o Marcos, assistente de inteligência política.
O cidadão já tem um chamado aberto. Ele enviou uma nova mensagem adicional.

CONDIÇÃO ESPECIAL (EMPATIA):
Se a mensagem do cidadão for um relato de MAL ATENDIMENTO, negligência ou decepção com o político:
- Comece lamentando sinceramente o ocorrido.
- Reforce que o relato dele é fundamental para que o gestor possa melhorar.
- Mantenha o tom humano e acolhedor.

MENSAGEM DO CIDADÃO: "{text}"
{urgency_note}

Escreva UMA resposta amigável e curta (máx. 3 frases) confirmando que a informação foi adicionada ao chamado.
Não mencione número de protocolo — já foi informado antes.
Tom: próximo, humano, sem burocracia."""

                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": reply_prompt}],
                        max_tokens=100,
                        temperature=0.6
                    )
                    reply = resp.choices[0].message.content.strip()
                except Exception as e:
                    print(f"Erro na resposta de threading: {e}")
                    reply = "Lamento que sua experiência não tenha sido positiva. Já adicionei esse relato ao seu chamado e o gestor será informado. Obrigado por nos avisar."

                send_whatsapp_message(remote_jid, reply)
                return jsonify({"status": "updated_existing"}), 200

            # Novo feedback — classificar e salvar
            print(f"Processing new feedback: {text}")
            ia_result = classificar_com_ia(text)

            if ia_result:
                sentimento = ia_result.get('sentimento', 'Neutro')
                categoria = ia_result.get('categoria', 'Propostas & Projetos')
                regiao = ia_result.get('regiao', 'N/A')
                cidade = ia_result.get('cidade', 'N/A')
                print(f"[AI-FIRST] Classified: {categoria} / {sentimento} / {regiao} / {cidade}")
            else:
                print(f"[FALLBACK] AI failed, using keywords...")
                sentimento = classificar_sentimento(text)
                categoria = classificar_categoria(text)
                regiao = classificar_regiao(text)
                cidade = 'N/A'

            # Topic extraction
            topic = "Geral"
            text_lower = text.lower()
            if categoria != 'Propostas & Projetos' or sentimento != 'Neutro':
                topic = f"{categoria}"
                if "buraco" in text_lower: topic = "Buraco na Via"
                elif "lixo" in text_lower: topic = "Lixo/Sujeira"
                elif "esgoto" in text_lower: topic = "Esgoto"
                elif "iluminação" in text_lower or "luz" in text_lower: topic = "Iluminação"
                elif "onibus" in text_lower or "ônibus" in text_lower: topic = "Ônibus"
                elif "escola" in text_lower or "creche" in text_lower: topic = "Educação"
                elif "saúde" in text_lower or "hospital" in text_lower or "ubs" in text_lower: topic = "Saúde"
                elif "segurança" in text_lower or "assalto" in text_lower: topic = "Segurança"
                elif "emprego" in text_lower or "empresa" in text_lower: topic = "Emprego"
                elif "corrupção" in text_lower or "corrupcao" in text_lower or "desvio" in text_lower: topic = "Corrupção"
                elif "votou" in text_lower or "projeto" in text_lower: topic = "Votação/Projeto"
            else:
                topic = text if len(text.split()) <= 3 else text[:20] + "..."

            # Generate Protocol
            current_id = get_next_id()
            current_year = datetime.now().year
            protocol_num = f"{current_year}{current_id:04d}"

            new_report = {
                "id": current_id,
                "sender": remote_jid,
                "name": push_name,
                "message": text,
                "timestamp": datetime.utcnow().isoformat(),
                "category": categoria,
                "region": regiao,
                "urgency": sentimento,
                "sentiment": "Positivo" if sentimento == "Positivo" else ("Negativo" if sentimento in ["Critico", "Urgente"] else "Neutro"),
                "topic": topic,
                "status": "aberto",
                "city": cidade
            }

            save_feedback(new_report)

            # Reply via Marcos persona
            reply = generate_ai_response(text, categoria, sentimento, protocol_num)
            send_whatsapp_message(remote_jid, reply)

            return jsonify({"status": "processed", "protocol": protocol_num}), 200

    return jsonify({"status": "ignored"}), 200


def _montar_tarefa_de_operacao(atualizacao: dict) -> dict:
    """Transforma uma atualizacao de campo em tarefa objetiva para o gabinete."""
    cidade = (atualizacao.get("cidade") or "Cidade nao informada").strip()
    tema = (atualizacao.get("tema_principal") or "Mobilizacao local").strip()
    operador = (atualizacao.get("operador_nome") or "Operador de campo").strip()
    liderancas = (atualizacao.get("liderancas") or "").strip()
    resumo = (atualizacao.get("resumo") or atualizacao.get("mensagem_original") or "").strip()
    proxima_acao = (atualizacao.get("proxima_acao") or "Acompanhar a cidade e desdobrar a demanda com a equipe.").strip()
    temas_detectados = atualizacao.get("temas_detectados") or []

    resumo_curto = _resumir_tarefa_operacao(resumo, tema, liderancas)
    pontos = _extrair_pontos_tarefa_operacao(
        atualizacao.get("mensagem_original") or resumo,
        liderancas=liderancas,
        tema=tema,
        temas_detectados=temas_detectados,
    )

    detalhes = [
        f"Enviado por: {operador}",
        f"Resumo: {resumo_curto}",
    ]
    if pontos:
        detalhes.append("Pontos principais:")
        detalhes.extend(f"- {ponto}" for ponto in pontos[:3])
    detalhes.append(f"Próxima ação: {proxima_acao}")

    return {
        "titulo": f"{cidade} — {tema}",
        "detalhes": "\n".join(detalhes),
        "status": "aberta",
        "origem": "operacao_local",
        "criada_por_jid": atualizacao.get("operador_jid") or "operacao_local",
        "responsavel": None,
        "responsavel_contato_id": None,
        "deadline": None,
    }


def _resumir_tarefa_operacao(texto: str, tema: str, liderancas: str = "") -> str:
    """Monta um resumo curto e legivel para a tarefa do gabinete."""
    texto_limpo = re.sub(r"\s+", " ", str(texto or "")).strip(" .,-")
    if not texto_limpo:
        base = f"Atualizacao de campo sobre {tema.lower()}."
        if liderancas:
            base = f"{liderancas} enviou atualizacao de campo sobre {tema.lower()}."
        return base

    resumo = re.sub(r"^(hoje|ontem|agora)\b[:, -]*", "", texto_limpo, flags=re.IGNORECASE).strip()
    resumo = re.sub(r"^eu\s+(?:estive|fui|tive|conversei)\b", "", resumo, flags=re.IGNORECASE).strip(" ,.-")
    resumo = resumo or texto_limpo
    resumo = resumo[0].upper() + resumo[1:] if resumo else texto_limpo

    if len(resumo) > 190:
        corte = resumo[:187].rsplit(" ", 1)[0] or resumo[:187]
        resumo = corte.rstrip(" ,.-") + "..."
    return resumo


def _extrair_pontos_tarefa_operacao(texto: str, liderancas: str = "", tema: str = "", temas_detectados=None) -> list[str]:
    """Destaca os pontos principais do relato para o gabinete bater o olho e agir."""
    texto_bruto = re.sub(r"\s+", " ", str(texto or "")).strip(" .,-")
    texto_norm = _normalizar_texto(texto_bruto)
    pontos = []

    if liderancas:
        pontos.append(f"Lideranca citada: {liderancas}.")

    valor_match = re.search(r"(?:r\$\s*)?(\d{1,3}(?:[\.,]\d{3})*(?:,\d{2})?|\d+\s*mil)", texto_bruto, re.IGNORECASE)
    valor = valor_match.group(1).strip() if valor_match else ""

    if "verba" in texto_norm or "recurso" in texto_norm:
        if valor:
            if "cabo" in texto_norm:
                pontos.append(f"Pedido de verba de {valor} para mobilizacao de cabos eleitorais.")
            else:
                pontos.append(f"Pedido de verba de {valor}.")
        else:
            pontos.append("Ha pedido de verba no relato.")

    if "asfalt" in texto_norm and "vila rural" in texto_norm:
        pontos.append("Pedido de asfaltamento em vila rural.")
    elif "asfalt" in texto_norm:
        pontos.append("Pedido de asfaltamento ou melhoria viaria.")
    elif "estrada rural" in texto_norm or "patrol" in texto_norm or "cascalho" in texto_norm:
        pontos.append("Demanda por estrada rural ou melhoria de acesso.")

    if "fila de exame" in texto_norm or "fila de exames" in texto_norm:
        pontos.append("Relato de fila de exames na area da saude.")
    elif "saude" in texto_norm or "hospital" in texto_norm or "exame" in texto_norm or "samu" in texto_norm:
        pontos.append("Demanda de saude mencionada no relato.")

    temas = [tema] + list(temas_detectados or [])
    temas = [t for t in dict.fromkeys([str(t).strip() for t in temas if t])]
    if not pontos and temas:
        pontos.append(f"Tema central: {temas[0]}.")

    if not pontos and texto_bruto:
        segmentos = [seg.strip(" ,.-") for seg in re.split(r"(?<=[.!?])\s+|,\s+", texto_bruto) if seg.strip()]
        for segmento in segmentos:
            if len(segmento) >= 18:
                trecho = segmento[:120].rstrip(" ,.-")
                pontos.append(trecho + ("..." if len(segmento) > 120 else "."))
                break

    pontos_limpos = []
    vistos = set()
    for ponto in pontos:
        ponto_limpo = re.sub(r"\s+", " ", ponto).strip()
        chave = _normalizar_texto(ponto_limpo)
        if not ponto_limpo or chave in vistos:
            continue
        vistos.add(chave)
        pontos_limpos.append(ponto_limpo)
    return pontos_limpos[:3]


@app.route("/api/tarefas", methods=["GET", "POST"])
def api_listar_tarefas():
    """Lista tarefas do gabinete ou cria tarefa manual/originada da operacao local."""
    if not supabase_admin:
        return jsonify({"data": [], "total": 0, "error": "supabase_indisponivel"}), 200

    if request.method == "POST":
        data = request.json or {}
        origem = (data.get("origem") or "manual").strip()[:40]
        try:
            if origem == "operacao_local":
                atualizacao = data.get("atualizacao") or {}
                if not isinstance(atualizacao, dict) or not (atualizacao.get("cidade") or atualizacao.get("resumo") or atualizacao.get("mensagem_original")):
                    return jsonify({"error": "atualizacao_invalida"}), 400
                payload = _montar_tarefa_de_operacao(atualizacao)
            else:
                titulo = (data.get("titulo") or "").strip()
                if not titulo:
                    return jsonify({"error": "titulo_obrigatorio"}), 400
                payload = {
                    "titulo": titulo[:180],
                    "detalhes": (data.get("detalhes") or "").strip()[:4000] or None,
                    "status": data.get("status") if data.get("status") in ("aberta", "em_andamento", "concluida") else "aberta",
                    "origem": origem or "manual",
                    "criada_por_jid": (data.get("criada_por_jid") or "").strip()[:120] or None,
                    "responsavel": (data.get("responsavel") or "").strip()[:120] or None,
                    "responsavel_contato_id": data.get("responsavel_contato_id"),
                    "deadline": data.get("deadline") or None,
                }

            res = supabase_admin.table("tarefas_gabinete").insert(payload).execute()
            tarefa = (res.data or [{}])[0]
            return jsonify({"success": True, "data": tarefa}), 201
        except Exception as e:
            print(f"[tarefas] Erro ao criar tarefa: {e}")
            return jsonify({"error": str(e)}), 500

    try:
        status_filter = request.args.get("status")
        limit = request.args.get("limit", 100, type=int)
        query = supabase_admin.table("tarefas_gabinete").select("*", count="exact")
        if status_filter:
            query = query.eq("status", status_filter)
        query = query.order("criada_em", desc=True).limit(limit)
        res = query.execute()
        return jsonify({
            "data": res.data or [],
            "total": res.count if res.count is not None else len(res.data or [])
        })
    except Exception as e:
        print(f"[tarefas] Erro: {e}")
        return jsonify({"data": [], "total": 0, "error": str(e)}), 200


@app.route("/api/tarefas/<int:tarefa_id>/status", methods=["PUT"])
def api_atualizar_status_tarefa(tarefa_id):
    """Atualiza o status de uma tarefa (aberta, em_andamento, concluida)."""
    if not supabase_admin:
        return jsonify({"error": "supabase_indisponivel"}), 503
    data = request.json or {}
    novo_status = data.get("status")
    if novo_status not in ("aberta", "em_andamento", "concluida"):
        return jsonify({"error": "status_invalido"}), 400
    try:
        supabase_admin.table("tarefas_gabinete").update({
            "status": novo_status,
            "atualizada_em": datetime.utcnow().isoformat(),
        }).eq("id", tarefa_id).execute()
        return jsonify({"success": True, "status": novo_status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao-local", methods=["GET"])
def api_operacao_local():
    """Retorna operadores, atualizacoes recentes e KPIs da operacao de campo."""
    try:
        operadores = listar_operadores_campo()
        atualizacoes = listar_atualizacoes_campo(request.args.get("limit", 80, type=int))

        # Indexa operadores por variações de JID/telefone para enriquecer cada atualização
        index_operadores = {}
        for op in operadores:
            for chave in _variantes_telefone_jid(op.get("jid") or op.get("telefone")):
                if chave:
                    index_operadores[chave] = op

        agora = datetime.utcnow()
        hoje = agora.date()
        cidades = set()
        hoje_count = 0
        atencao_count = 0
        urgentes_sem_resposta = 0

        enriquecidas = []
        for item in atualizacoes:
            item = dict(item or {})
            jid_op = item.get("operador_jid") or item.get("operador_telefone") or ""
            operador = None
            for chave in _variantes_telefone_jid(jid_op):
                if chave in index_operadores:
                    operador = index_operadores[chave]
                    break

            if operador:
                item["operador_score"] = operador.get("score") or 0
                item["operador_nivel"] = operador.get("score_nivel") or "normal"
                item["operador_funcao_chave"] = operador.get("funcao_chave")
                item["operador_funcao_label"] = operador.get("funcao_label")
                item["operador_influencia"] = operador.get("influencia")
                item["operador_sla_horas"] = operador.get("sla_horas") or 24
            else:
                item["operador_score"] = 0
                item["operador_nivel"] = "normal"
                item["operador_sla_horas"] = 24

            data_item = _parse_data_feedback(item.get("criada_em"))
            if data_item:
                if data_item.date() == hoje:
                    hoje_count += 1
                horas = max(0.0, (agora - data_item).total_seconds() / 3600.0)
                item["horas_desde_chamado"] = round(horas, 2)
                sla = item.get("operador_sla_horas") or 24
                item["fora_sla"] = bool(horas > sla)
                item["urgente_sem_resposta"] = bool(horas >= 24)
                if item["urgente_sem_resposta"]:
                    urgentes_sem_resposta += 1
            else:
                item["horas_desde_chamado"] = None
                item["fora_sla"] = False
                item["urgente_sem_resposta"] = False

            if item.get("sentimento") == "atencao":
                atencao_count += 1
            if item.get("cidade"):
                cidades.add(item["cidade"])

            enriquecidas.append(item)

        # Ordenação por importância política: score do operador manda primeiro
        # (cabo eleitoral/prefeito > voluntário). Urgência >24h é desempate
        # dentro da mesma faixa de score, e data é o critério final.
        def chave_ordenacao(a):
            data = _parse_data_feedback(a.get("criada_em"))
            return (
                -(a.get("operador_score") or 0),
                0 if a.get("urgente_sem_resposta") else 1,
                -(data.timestamp() if data else 0),
            )
        enriquecidas.sort(key=chave_ordenacao)

        # Operadores: ativos primeiro, depois por score decrescente
        operadores_ordenados = sorted(
            operadores,
            key=lambda op: (op.get("status") != "ativo", -(op.get("score") or 0)),
        )

        return jsonify({
            "operadores": operadores_ordenados,
            "atualizacoes": enriquecidas,
            "kpis": {
                "operadores_ativos": sum(1 for op in operadores if op.get("status") == "ativo" and not op.get("demo")),
                "atualizacoes_hoje": hoje_count,
                "cidades_movimentadas": len(cidades),
                "pontos_atencao": atencao_count,
                "urgentes_sem_resposta": urgentes_sem_resposta,
            }
        })
    except Exception as e:
        print(f"[operacao] Erro API geral: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao-local/operadores", methods=["GET", "POST"])
def api_operadores_campo():
    """Lista ou cadastra operadores/cabos autorizados a atualizar por WhatsApp."""
    if request.method == "GET":
        return jsonify({"data": listar_operadores_campo()})

    data = request.json or {}
    try:
        operador = salvar_operador_campo(data)
        return jsonify({"success": True, "data": operador}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[operacao] Erro ao cadastrar operador: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao-local/base-eleitoral", methods=["GET"])
def api_base_eleitoral_operacao():
    """Base eleitoral unificada para o formulário da Operação Local.

    Fonte prioritária: Mapa Eleitoral (static/votos_*.json — votos Candidato A + B 2022).
    Fonte complementar: base demo (static/base_eleitoral_demo.json), apenas para cidades
    fora do Mapa Eleitoral.
    """
    base = carregar_base_eleitoral_unificada()

    por_regiao = {}
    for nome, dados in base.items():
        regiao = dados.get("regiao") or "Outras regiões"
        por_regiao.setdefault(regiao, []).append({
            "cidade": nome,
            "votos_total": int(dados.get("votos_total") or 0),
            "votos_candidato_a": int(dados.get("votos_candidato_a") or 0),
            "votos_candidato_b": int(dados.get("votos_candidato_b") or 0),
            "origem": dados.get("origem") or "demo",
            "polo": dados.get("polo") or "",
        })
    for lista in por_regiao.values():
        lista.sort(key=lambda c: c["votos_total"], reverse=True)

    top_cidades = sorted(
        ({"cidade": n, **d} for n, d in base.items()),
        key=lambda c: c.get("votos_total") or 0,
        reverse=True,
    )[:6]

    mapa_count = sum(1 for d in base.values() if d.get("origem") == "mapa_eleitoral")
    demo_count = sum(1 for d in base.values() if d.get("origem") == "demo")

    return jsonify({
        "fonte": "Mapa Eleitoral (Candidato A + Candidato B, 2022) + base demo",
        "total_municipios": len(base),
        "mapa_eleitoral_municipios": mapa_count,
        "demo_municipios": demo_count,
        "por_regiao": por_regiao,
        "regioes": sorted(por_regiao.keys()),
        "top_cidades": top_cidades,
        "funcoes": [
            {"chave": chave, "label": FUNCOES_OPERADOR_LABEL[chave], "peso": peso}
            for chave, peso in PESOS_FUNCAO_OPERADOR.items()
        ],
        "faixas": FAIXAS_SCORE_OPERADOR,
    })


def _ultima_mensagem_por_operador() -> dict:
    """Devolve dict {jid_normalizado: datetime} com a ultima mensagem trocada por operador.

    Cruza tabela `operacao_local_mensagens` (Supabase) e fallback JSON local.
    """
    por_jid: dict[str, datetime] = {}
    fontes: list[list[dict]] = []
    if supabase_admin:
        try:
            res = supabase_admin.table("operacao_local_mensagens").select("operador_jid,enviada_em").execute()
            fontes.append(res.data or [])
        except Exception as e:
            print(f"[operacao] Supabase ultima_mensagem indisponivel: {e}")
    try:
        fontes.append(load_json(OPERACAO_MSGS_FILE, []))
    except Exception:
        pass

    for fonte in fontes:
        for msg in fonte:
            jid = (msg.get("operador_jid") or msg.get("jid") or "").strip()
            if not jid:
                continue
            data = _parse_data_feedback(msg.get("enviada_em") or msg.get("criada_em"))
            if not data:
                continue
            chave = _normalizar_telefone_jid(jid)
            if not chave:
                continue
            if chave not in por_jid or data > por_jid[chave]:
                por_jid[chave] = data
    return por_jid


@app.route("/api/operacao-local/sem-contato", methods=["GET"])
def api_operadores_sem_contato():
    """Lista operadores ativos que estao ha mais de 7 dias sem mensagem nem atualizacao.

    Retorna ate 5 operadores ordenados por dias_sem_contato (desc). Serve para o
    card "Quem precisa de mim agora" no painel lateral da Operacao Local.
    """
    try:
        limite_dias = max(1, request.args.get("dias", 7, type=int))
        topo = max(1, min(20, request.args.get("limit", 5, type=int)))

        operadores = listar_operadores_campo(incluir_demo=False)
        atualizacoes = listar_atualizacoes_campo(limit=500)
        ultima_msg_por_jid = _ultima_mensagem_por_operador()

        # Indexa ultima atualizacao por jid normalizado
        ultima_atual_por_jid: dict[str, datetime] = {}
        for a in atualizacoes:
            jid = a.get("operador_jid") or ""
            data = _parse_data_feedback(a.get("criada_em"))
            if not jid or not data:
                continue
            chave = _normalizar_telefone_jid(jid)
            if not chave:
                continue
            if chave not in ultima_atual_por_jid or data > ultima_atual_por_jid[chave]:
                ultima_atual_por_jid[chave] = data

        agora = datetime.utcnow()
        dormentes = []
        for op in operadores:
            if op.get("status") != "ativo" or op.get("demo"):
                continue
            jid_variantes = _variantes_telefone_jid(op.get("jid") or op.get("telefone"))
            if not jid_variantes:
                continue
            candidatos = []
            for chave in jid_variantes:
                if chave in ultima_atual_por_jid:
                    candidatos.append(ultima_atual_por_jid[chave])
                if chave in ultima_msg_por_jid:
                    candidatos.append(ultima_msg_por_jid[chave])
            ultima = max(candidatos) if candidatos else None
            dias = (agora - ultima).days if ultima else 999
            if dias < limite_dias:
                continue
            dormentes.append({
                "jid": op.get("jid") or op.get("telefone"),
                "nome": op.get("nome") or "Operador",
                "telefone_mascarado": op.get("telefone_mascarado"),
                "funcao_label": op.get("funcao_label") or op.get("funcao") or "Operador",
                "especificacao": op.get("especificacao") or "",
                "cidade_base": op.get("cidade_base") or "",
                "regiao": op.get("regiao") or "",
                "score": op.get("score") or 0,
                "score_nivel": op.get("score_nivel") or "normal",
                "influencia": op.get("influencia") or 0,
                "dias_sem_contato": min(dias, 999),
                "nunca_contatado": ultima is None,
                "ultima_atividade_iso": ultima.isoformat() if ultima else None,
            })

        dormentes.sort(key=lambda d: (-d["dias_sem_contato"], -(d.get("score") or 0)))
        return jsonify({
            "data": dormentes[:topo],
            "total_dormentes": len(dormentes),
            "limite_dias": limite_dias,
        })
    except Exception as e:
        print(f"[operacao] sem-contato erro: {e}")
        return jsonify({"data": [], "total_dormentes": 0, "error": str(e)}), 200


@app.route("/api/operacao-local/atualizacoes", methods=["GET", "POST"])
def api_atualizacoes_campo():
    """Lista atualizacoes de campo ou cria uma atualizacao manual para demo."""
    if request.method == "GET":
        limit = request.args.get("limit", 80, type=int)
        return jsonify({"data": listar_atualizacoes_campo(limit)})

    data = request.json or {}
    texto = (data.get("mensagem") or data.get("texto") or "").strip()
    if not texto:
        return jsonify({"error": "mensagem_obrigatoria"}), 400

    operadores = listar_operadores_campo(incluir_demo=False)
    operador = None
    operador_id = str(data.get("operador_id") or "")
    if operador_id:
        operador = next((op for op in operadores if str(op.get("id")) == operador_id), None)
    if not operador:
        operador = {
            "id": None,
            "nome": data.get("operador_nome") or "Registro manual",
            "regiao": data.get("regiao") or "",
            "cidade_base": data.get("cidade_base") or "",
        }

    atualizacao = montar_atualizacao_campo(texto, operador, data.get("operador_jid") or "manual", origem="manual")
    if data.get("cidade"):
        atualizacao["cidade"] = data.get("cidade").strip()[:120]
    salvo = salvar_atualizacao_campo(atualizacao)
    return jsonify({"success": True, "data": salvo}), 201


@app.route("/api/operacao-local/mensagens", methods=["GET", "POST"])
def api_mensagens_operacao():
    """Envia WhatsApp ao operador de campo e mantem historico por chamado."""
    if request.method == "GET":
        atualizacao_id = request.args.get("atualizacao_id")
        limit = request.args.get("limit", 60, type=int)
        return jsonify({"data": listar_mensagens_operacao(atualizacao_id, limit)})

    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY or not EVOLUTION_INSTANCE_NAME:
        return jsonify({"error": "whatsapp_nao_configurado"}), 503

    data = request.json or {}
    texto = (data.get("mensagem") or data.get("texto") or "").strip()
    if not texto:
        return jsonify({"error": "mensagem_obrigatoria"}), 400
    if len(texto) > 4000:
        return jsonify({"error": "mensagem_muito_longa"}), 400

    atualizacao_id = data.get("atualizacao_id")
    atualizacao = buscar_atualizacao_campo_por_id(atualizacao_id) if atualizacao_id else None

    destino_raw = (data.get("destinatario") or "").strip()
    if not destino_raw and atualizacao:
        destino_raw = atualizacao.get("operador_jid") or ""
    if not destino_raw and atualizacao:
        operador = next(
            (op for op in listar_operadores_campo(incluir_demo=False)
             if op.get("nome") == atualizacao.get("operador_nome")),
            None,
        )
        if operador:
            destino_raw = operador.get("jid") or operador.get("telefone") or ""

    destino = _jid_para_envio(destino_raw)
    if not destino or len(destino) < 10:
        return jsonify({"error": "destinatario_invalido"}), 400

    try:
        send_whatsapp_message(destino, texto)
    except Exception as e:
        print(f"[operacao] Erro ao enviar WhatsApp: {e}")
        return jsonify({"error": "falha_ao_enviar"}), 502

    registro = {
        "atualizacao_id": atualizacao.get("id") if atualizacao else None,
        "destinatario_jid": destino,
        "destinatario_nome": (atualizacao or {}).get("operador_nome") or data.get("destinatario_nome") or "Operador",
        "cidade": (atualizacao or {}).get("cidade") or data.get("cidade") or "",
        "direcao": "enviada",
        "canal": "whatsapp",
        "texto": texto,
        "autor": data.get("autor") or session.get("user") or "gabinete",
        "enviada_em": datetime.utcnow().isoformat(),
    }
    salvo = salvar_mensagem_operacao(registro)
    print(f"[operacao] Mensagem enviada destino={_mascarar_telefone(destino)} atualizacao={registro['atualizacao_id']}")
    salvo["destinatario_mascarado"] = _mascarar_telefone(destino)
    salvo.pop("destinatario_jid", None)
    return jsonify({"success": True, "data": salvo}), 201


@app.route("/api/feedback/<int:feedback_id>/status", methods=["PUT"])
def update_feedback_status(feedback_id):
    """Atualiza o status de um feedback"""
    data = request.json
    new_status = data.get('status')

    if new_status not in ['aberto', 'em_andamento', 'resolvido']:
        return jsonify({"error": "Status inválido"}), 400

    updates = {'status': new_status}
    if new_status == 'resolvido':
        updates['resolved_at'] = datetime.utcnow().isoformat()
    else:
        updates['resolved_at'] = None

    if update_feedback(feedback_id, updates):
        return jsonify({"success": True, "status": new_status})
    else:
        return jsonify({"error": "Feedback não encontrado"}), 404


@app.route("/api/debug")
def debug_env():
    """Endpoint para verificar variáveis de ambiente"""
    return jsonify({
        "status": "online",
        "app": "Política Node Data",
        "env_check": {
            "SUPABASE_URL": "OK" if os.getenv("SUPABASE_URL") else "MISSING",
            "SUPABASE_KEY": "OK" if os.getenv("SUPABASE_KEY") else "MISSING",
            "OPENAI_API_KEY": "OK" if os.getenv("OPENAI_API_KEY") else "MISSING",
            "EVOLUTION_API_URL": os.getenv("EVOLUTION_API_URL", "MISSING"),
            "EVOLUTION_INSTANCE": os.getenv("EVOLUTION_INSTANCE_NAME", "MISSING"),
            "EVOLUTION_KEY_SET": "YES" if os.getenv("EVOLUTION_API_KEY") else "NO"
        }
    })


# ============================================================
# MAPA ELEITORAL — Votação por Região
# ============================================================

@app.route('/mapa-eleitoral')
def mapa_eleitoral():
    return render_template('data_node.html', active_page='mapa_eleitoral')


@app.route('/api/mapa-eleitoral/dados')
@app.route('/api/mapa-eleitoral/dados/<regiao>')
def mapa_eleitoral_dados(regiao='rio-doce'):
    """Retorna dados de votação por região"""
    arquivos = {
        'rio-doce': 'votos_vale_rio_doce.json',
        'jequitinhonha': 'votos_jequitinhonha.json',
        'mucuri': 'votos_mucuri.json'
    }
    arquivo = arquivos.get(regiao, 'votos_vale_rio_doce.json')
    return send_from_directory('static', arquivo)


def _normalizar_texto(valor: str) -> str:
    """Normaliza texto para comparacoes sem acento e sem pontuacao."""
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = texto.encode('ASCII', 'ignore').decode('ASCII').lower()
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


def _parse_data_feedback(valor):
    """Converte timestamps conhecidos para datetime, retornando None se falhar."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor).replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return None


def _carregar_cidades_estaticas():
    """Carrega metadata local das cidades monitoradas."""
    cidades = {}
    for item in load_json(os.path.join(BASE_DIR, 'static', 'cidades_mg.json'), []):
        nome = item.get('cidade')
        if not nome:
            continue
        cidades[_normalizar_texto(nome)] = {
            'cidade': nome,
            'regiao': item.get('regiao') or '',
            'latitude': item.get('latitude'),
            'longitude': item.get('longitude'),
        }
    return cidades


def _carregar_votos_eleitorais():
    """Consolida votos historicos locais por cidade para o ranking de prioridade."""
    arquivos = {
        'rio-doce': 'votos_vale_rio_doce.json',
        'jequitinhonha': 'votos_jequitinhonha.json',
        'mucuri': 'votos_mucuri.json',
    }
    cidades = {}
    for regiao_key, arquivo in arquivos.items():
        dados = load_json(os.path.join(BASE_DIR, 'static', arquivo), {})
        regiao_nome = dados.get('regiao', regiao_key)
        for polo in dados.get('polos', []):
            for item in polo.get('cidades', []):
                nome = item.get('cidade')
                if not nome:
                    continue
                chave = _normalizar_texto(nome)
                registro = cidades.setdefault(chave, {
                    'cidade': nome,
                    'regiao_eleitoral': regiao_nome,
                    'polo': polo.get('nome', ''),
                    'votos_candidato_a': 0,
                    'votos_candidato_b': 0,
                })
                registro['votos_candidato_a'] += int(item.get('candidato_a') or 0)
                registro['votos_candidato_b'] += int(item.get('candidato_b') or 0)
    return cidades


def _inferir_cidade_feedback(feedback, aliases_cidades):
    """Usa o campo city quando existe; caso contrario tenta achar cidade no texto."""
    cidade = (feedback.get('city') or '').strip()
    if cidade and cidade.upper() != 'N/A':
        return _normalizar_texto(cidade), cidade

    texto = _normalizar_texto(feedback.get('message') or feedback.get('text') or '')
    if not texto:
        return None, None

    texto_pad = f" {texto} "
    for chave, nome in aliases_cidades:
        if len(chave) >= 5 and f" {chave} " in texto_pad:
            return chave, nome
    return None, None


def _coletar_radar_prioridades():
    """Busca o ultimo Radar MG por cidade, sem bloquear a feature se o Supabase falhar."""
    if not supabase:
        return {}
    try:
        pesquisas = supabase.table('radar_cidades_pesquisas') \
            .select('id,cidade,sentimento_geral,total_posts,resumo_ia,created_at') \
            .order('created_at', desc=True) \
            .limit(80) \
            .execute()
    except Exception as e:
        if 'sentimento_geral' in str(e):
            try:
                pesquisas = supabase.table('radar_cidades_pesquisas') \
                    .select('id,cidade,total_posts,resumo_ia,created_at') \
                    .order('created_at', desc=True) \
                    .limit(80) \
                    .execute()
                print("[prioridades] Radar local sem coluna sentimento_geral; usando fallback neutro.")
            except Exception as fallback_error:
                print(f"[prioridades] Radar MG indisponivel: {fallback_error}")
                return {}
        else:
            print(f"[prioridades] Radar MG indisponivel: {e}")
            return {}

    por_cidade = {}
    pesquisa_ids = []
    for item in pesquisas.data or []:
        cidade = item.get('cidade')
        if not cidade:
            continue
        chave = _normalizar_texto(cidade)
        if chave not in por_cidade:
            por_cidade[chave] = {
                'pesquisa_id': item.get('id'),
                'cidade': cidade,
                'sentimento': item.get('sentimento_geral') or 'neutro',
                'total_posts': item.get('total_posts') or 0,
                'resumo': item.get('resumo_ia') or '',
                'created_at': item.get('created_at'),
                'temas': [],
            }
            pesquisa_ids.append(item.get('id'))

    if not pesquisa_ids:
        return por_cidade

    try:
        temas = supabase.table('radar_cidades_temas') \
            .select('pesquisa_id,tema,mencoes,sentimento_predominante') \
            .in_('pesquisa_id', pesquisa_ids[:50]) \
            .execute()
        por_id = {v['pesquisa_id']: v for v in por_cidade.values()}
        for tema in temas.data or []:
            radar = por_id.get(tema.get('pesquisa_id'))
            if radar:
                radar['temas'].append({
                    'tema': tema.get('tema'),
                    'mencoes': tema.get('mencoes') or 0,
                    'sentimento': tema.get('sentimento_predominante') or '',
                })
    except Exception as e:
        print(f"[prioridades] Temas do Radar MG indisponiveis: {e}")

    return por_cidade


def _coletar_operacao_prioridades():
    """Agrupa atualizacoes de campo por cidade para alimentar prioridades."""
    por_cidade = defaultdict(lambda: {
        "total": 0,
        "atencao": 0,
        "topicos": Counter(),
        "ultima_interacao": None,
        "operadores": set(),
    })
    try:
        for item in listar_atualizacoes_campo(300):
            cidade = item.get("cidade")
            if not cidade or cidade == "Cidade nao informada":
                continue
            chave = _normalizar_texto(cidade)
            grupo = por_cidade[chave]
            grupo["cidade"] = cidade
            grupo["total"] += 1
            if item.get("sentimento") == "atencao":
                grupo["atencao"] += 1
            if item.get("tema_principal"):
                grupo["topicos"][item.get("tema_principal")] += 1
            if item.get("operador_nome"):
                grupo["operadores"].add(item.get("operador_nome"))
            data_item = _parse_data_feedback(item.get("criada_em"))
            if data_item and (not grupo["ultima_interacao"] or data_item > grupo["ultima_interacao"]):
                grupo["ultima_interacao"] = data_item
    except Exception as e:
        print(f"[prioridades] Operacao local indisponivel: {e}")
        return {}

    return {
        chave: {
            **dados,
            "topicos": dados["topicos"],
            "operadores": list(dados["operadores"]),
        }
        for chave, dados in por_cidade.items()
    }


def _prioridades_semana_internal(limit: int = 30) -> dict:
    """Versão pura (sem Flask) do ranking de prioridades para uso interno (Marcos etc.)."""
    limite = max(5, min(int(limit) if limit else 30, 100))

    cidades_meta = _carregar_cidades_estaticas()
    votos_por_cidade = _carregar_votos_eleitorais()
    radar_por_cidade = _coletar_radar_prioridades()
    operacao_por_cidade = _coletar_operacao_prioridades()

    nomes_para_busca = {
        chave: dados.get('cidade', chave)
        for chave, dados in {**cidades_meta, **votos_por_cidade}.items()
    }
    aliases = sorted(nomes_para_busca.items(), key=lambda x: len(x[0]), reverse=True)

    feedbacks_por_cidade = defaultdict(lambda: {
        'total': 0,
        'negativos': 0,
        'urgentes': 0,
        'abertos': 0,
        'topicos': Counter(),
        'ultima_interacao': None,
    })

    for fb in get_feedbacks():
        chave, cidade_nome = _inferir_cidade_feedback(fb, aliases)
        if not chave:
            continue

        grupo = feedbacks_por_cidade[chave]
        grupo['total'] += 1

        sentimento = _normalizar_texto(fb.get('sentiment') or fb.get('urgency') or '')
        urgencia = _normalizar_texto(fb.get('urgency') or '')
        status = _normalizar_texto(fb.get('status') or 'aberto')
        if 'negativo' in sentimento or 'critico' in urgencia or 'alta' in urgencia:
            grupo['negativos'] += 1
        if 'critico' in urgencia or 'urgente' in urgencia or 'alta' in urgencia:
            grupo['urgentes'] += 1
        if status != 'resolvido':
            grupo['abertos'] += 1

        topico = fb.get('topic') or fb.get('category') or 'Demanda cidadã'
        grupo['topicos'][topico] += 1

        data_fb = _parse_data_feedback(fb.get('created_at') or fb.get('timestamp'))
        if data_fb and (not grupo['ultima_interacao'] or data_fb > grupo['ultima_interacao']):
            grupo['ultima_interacao'] = data_fb

        if chave not in nomes_para_busca and cidade_nome:
            nomes_para_busca[chave] = cidade_nome

    chaves_candidatas = set(votos_por_cidade) | set(feedbacks_por_cidade) | set(radar_por_cidade) | set(operacao_por_cidade)
    max_base = max([
        (v.get('votos_candidato_a', 0) + v.get('votos_candidato_b', 0))
        for v in votos_por_cidade.values()
    ] or [1])
    max_gap = max([
        max((v.get('votos_candidato_a', 0) - v.get('votos_candidato_b', 0)), 0)
        for v in votos_por_cidade.values()
    ] or [1])

    prioridades = []
    agora = datetime.utcnow()
    for chave in chaves_candidatas:
        votos = votos_por_cidade.get(chave, {})
        fb = feedbacks_por_cidade.get(chave, {})
        radar = radar_por_cidade.get(chave, {})
        operacao = operacao_por_cidade.get(chave, {})
        meta = cidades_meta.get(chave, {})

        votos_candidato_a = int(votos.get('votos_candidato_a') or 0)
        votos_candidato_b = int(votos.get('votos_candidato_b') or 0)
        base_aliada = votos_candidato_a + votos_candidato_b
        gap_conversao = max(votos_candidato_a - votos_candidato_b, 0)

        base_score = 0 if not max_base else 30 * ((base_aliada / max_base) ** 0.55)
        gap_score = 0 if not max_gap else 30 * ((gap_conversao / max_gap) ** 0.55)

        total_fb = int(fb.get('total') or 0)
        negativos = int(fb.get('negativos') or 0)
        urgentes = int(fb.get('urgentes') or 0)
        abertos = int(fb.get('abertos') or 0)
        total_operacao = int(operacao.get('total') or 0)
        atencao_operacao = int(operacao.get('atencao') or 0)
        pressao_score = min(22, total_fb * 2.5 + negativos * 3 + urgentes * 4 + abertos * 2 + total_operacao * 3 + atencao_operacao * 4)

        recencia_score = 0
        ultima_interacao = fb.get('ultima_interacao')
        ultima_operacao = operacao.get('ultima_interacao')
        if ultima_operacao and (not ultima_interacao or ultima_operacao > ultima_interacao):
            ultima_interacao = ultima_operacao
        if ultima_interacao:
            dias = max((agora - ultima_interacao).days, 0)
            if dias <= 7:
                recencia_score = 8
            elif dias <= 30:
                recencia_score = 5
            elif dias <= 90:
                recencia_score = 2

        radar_sent = _normalizar_texto(radar.get('sentimento') or '')
        radar_score = 0
        if radar:
            radar_score += min(4, int(radar.get('total_posts') or 0) / 5)
            if 'negativo' in radar_sent:
                radar_score += 6
            elif 'positivo' in radar_sent:
                radar_score += 2
            else:
                radar_score += 4

        score = int(round(min(100, base_score + gap_score + pressao_score + recencia_score + radar_score)))
        nivel = 'alta' if score >= 60 else 'media' if score >= 40 else 'monitorar'

        top_temas = [t for t, _ in fb.get('topicos', Counter()).most_common(3)]
        if operacao.get('topicos'):
            temas_operacao = [t for t, _ in operacao.get('topicos').most_common(3)]
            top_temas = list(dict.fromkeys(temas_operacao + top_temas))[:3]
        if not top_temas and radar.get('temas'):
            top_temas = [t.get('tema') for t in sorted(
                radar.get('temas', []),
                key=lambda x: x.get('mencoes', 0),
                reverse=True
            )[:3] if t.get('tema')]

        motivos = []
        if gap_conversao > 0:
            motivos.append(f"{gap_conversao:,}".replace(',', '.') + " votos potenciais")
        if base_aliada > 0:
            motivos.append(f"{base_aliada:,}".replace(',', '.') + " votos de base mapeada")
        if urgentes or negativos:
            motivos.append(f"{urgentes} urgência(s) e {negativos} sinal(is) negativo(s)")
        elif total_fb:
            motivos.append(f"{total_fb} feedback(s) cidadão(s)")
        if total_operacao:
            motivos.append(f"{total_operacao} movimento(s) de campo")
        if radar:
            motivos.append("Radar local recente com sentimento " + (radar.get('sentimento') or 'neutro'))
        if not motivos:
            motivos.append("Cidade em monitoramento por dados eleitorais")

        if urgentes or negativos or atencao_operacao or 'negativo' in radar_sent:
            acao = "Entrar com resposta local: ligar para liderança, preparar fala curta e criar tarefa de acompanhamento."
        elif gap_conversao >= 1000:
            acao = "Marcar agenda de mobilização: visita com lideranças locais e pauta ligada aos temas quentes."
        elif radar:
            acao = "Usar o radar local para transformar os temas recentes em roteiro de visita ou vídeo curto."
        else:
            acao = "Acompanhar e reforçar presença digital antes de deslocamento presencial."

        prioridades.append({
            'cidade': meta.get('cidade') or votos.get('cidade') or radar.get('cidade') or operacao.get('cidade') or nomes_para_busca.get(chave, chave.title()),
            'regiao': meta.get('regiao') or votos.get('regiao_eleitoral') or '',
            'polo': votos.get('polo') or '',
            'score': score,
            'nivel': nivel,
            'votos_candidato_a': votos_candidato_a,
            'votos_candidato_b': votos_candidato_b,
            'base_aliada': base_aliada,
            'gap_conversao': gap_conversao,
            'feedbacks': total_fb,
            'negativos': negativos,
            'urgentes': urgentes,
            'abertos': abertos,
            'movimentos_campo': total_operacao,
            'pontos_atencao_campo': atencao_operacao,
            'ultima_interacao': ultima_interacao.isoformat() if ultima_interacao else None,
            'top_temas': top_temas,
            'radar': {
                'sentimento': radar.get('sentimento'),
                'total_posts': radar.get('total_posts') or 0,
                'resumo': radar.get('resumo') or '',
                'created_at': radar.get('created_at'),
            } if radar else None,
            'motivos': motivos[:4],
            'acao_recomendada': acao,
        })

    prioridades.sort(key=lambda item: item['score'], reverse=True)
    top_prioridades = prioridades[:limite]

    return {
        'generated_at': agora.isoformat(),
        'kpis': {
            'total_cidades': len(prioridades),
            'alta_prioridade': sum(1 for p in prioridades if p['nivel'] == 'alta'),
            'media_prioridade': sum(1 for p in prioridades if p['nivel'] == 'media'),
            'cidades_com_pressao': sum(1 for p in prioridades if p['feedbacks'] > 0 or p['radar'] or p.get('movimentos_campo', 0) > 0),
            'gap_top10': sum(p['gap_conversao'] for p in prioridades[:10]),
        },
        'metodologia': {
            'base_eleitoral': 30,
            'gap_conversao': 30,
            'pressao_cidada': 22,
            'recencia': 8,
            'radar_mg': 10,
        },
        'prioridades': top_prioridades,
    }


@app.route('/api/prioridades-semana')
def api_prioridades_semana():
    """Ranking de cidades prioritarias para a atuacao semanal do deputado."""
    try:
        limite = request.args.get('limit', 30, type=int)
        return jsonify(_prioridades_semana_internal(limit=limite))
    except Exception as e:
        print(f"[prioridades] Erro geral: {e}")
        return jsonify({'error': 'erro_ao_calcular_prioridades', 'detail': str(e)}), 500


# ============================================================
# RADAR MG — Inteligência por cidade de Minas Gerais
# ============================================================

@app.route('/radar-mg')
def radar_mg():
    # Conteúdo migrado para o Painel. Redireciona para compatibilidade com links antigos.
    return redirect(url_for('index'))


@app.route('/static/cidades_mg.json')
def cidades_mg_json():
    return send_from_directory('static', 'cidades_mg.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')


@app.route('/api/radar-mg/pesquisar', methods=['POST'])
def radar_mg_pesquisar():
    """Pesquisa cidade via Google News RSS + Apify Facebook Groups + OpenAI"""
    import xml.etree.ElementTree as ET
    from urllib.parse import quote

    pesquisa_id = None
    try:
        data = request.get_json()
        cidade = data.get('cidade', '').strip()
        estado = data.get('estado', 'MG')
        periodo_dias = data.get('periodo_dias', 7)

        if not cidade:
            return jsonify({'error': 'Cidade é obrigatória'}), 400

        # 1. Cria registro no Supabase
        pesquisa = supabase_admin.table('radar_cidades_pesquisas').insert({
            'cidade': cidade,
            'estado': estado,
            'periodo_dias': periodo_dias,
            'status': 'processando'
        }).execute()
        pesquisa_id = pesquisa.data[0]['id']

        apify_token = os.getenv('APIFY_TOKEN')

        # ── FONTE 1: Google News RSS ──────────────────────────────────────────
        print(f"[Radar MG] Buscando Google News para: {cidade}")
        posts_google = []
        try:
            rss_url = (
                f"https://news.google.com/rss/search"
                f"?q={quote(cidade + ' Minas Gerais')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            )
            rss_resp = requests.get(rss_url, timeout=15,
                                    headers={"User-Agent": "Mozilla/5.0"})
            if rss_resp.status_code == 200:
                root = ET.fromstring(rss_resp.content)
                for item in root.findall('.//item')[:20]:
                    title = item.findtext('title') or ''
                    desc  = item.findtext('description') or ''
                    # Remove tags HTML simples da description
                    import re as _re
                    desc_clean = _re.sub(r'<[^>]+>', '', desc).strip()
                    conteudo = (title + ' - ' + desc_clean).strip(' -')
                    if len(conteudo) < 20:
                        continue
                    posts_google.append({
                        'pesquisa_id': pesquisa_id,
                        'grupo_facebook': 'Google News',
                        'autor': 'Imprensa Local',
                        'conteudo': conteudo[:2000],
                        'likes': 0,
                        'comentarios': 0,
                    })
            print(f"[Radar MG] Google News: {len(posts_google)} notícias")
        except Exception as e_gn:
            print(f"[Radar MG] Google News falhou: {e_gn}")

        # ── FONTE 2: Apify Facebook Groups (2 etapas) ─────────────────────────
        posts_facebook = []
        try:
            # Etapa A — buscar grupos relevantes
            print(f"[Radar MG] Apify: buscando grupos Facebook para '{cidade}'")
            grupos_resp = requests.post(
                f"https://api.apify.com/v2/acts/memo23~facebook-search-groups-scraper"
                f"/run-sync-get-dataset-items?token={apify_token}",
                json={"query": f"moradores {cidade} Minas Gerais", "maxGroups": 5},
                timeout=60
            )
            print(f"[Radar MG] Grupos status: {grupos_resp.status_code} | {grupos_resp.text[:300]}")

            urls_grupos = []
            if grupos_resp.status_code == 200:
                grupos_data = grupos_resp.json()
                for g in grupos_data:
                    url = g.get('url') or g.get('groupUrl') or g.get('link') or ''
                    if url:
                        urls_grupos.append(url)

            # Etapa B — buscar posts dos grupos encontrados
            if urls_grupos:
                print(f"[Radar MG] Apify: buscando posts de {len(urls_grupos)} grupos")
                posts_resp = requests.post(
                    f"https://api.apify.com/v2/acts/apify~facebook-groups-scraper"
                    f"/run-sync-get-dataset-items?token={apify_token}",
                    json={
                        "startUrls": [{"url": u} for u in urls_grupos[:3]],
                        "maxPosts": 30,
                        "proxy": {"useApifyProxy": True}
                    },
                    timeout=120
                )
                print(f"[Radar MG] Posts FB status: {posts_resp.status_code} | {posts_resp.text[:300]}")
                if posts_resp.status_code == 200:
                    for post in posts_resp.json():
                        conteudo = post.get('text') or post.get('message') or ''
                        if not conteudo or len(conteudo) < 20:
                            continue
                        posts_facebook.append({
                            'pesquisa_id': pesquisa_id,
                            'grupo_facebook': post.get('groupName') or post.get('pageName') or 'Grupo Facebook',
                            'autor': post.get('authorName') or 'Anônimo',
                            'conteudo': conteudo[:2000],
                            'likes': post.get('likes') or 0,
                            'comentarios': post.get('commentsCount') or 0,
                        })
            print(f"[Radar MG] Facebook: {len(posts_facebook)} posts")
        except Exception as e_fb:
            print(f"[Radar MG] Facebook Apify falhou: {e_fb}")

        # ── Combinar e salvar ─────────────────────────────────────────────────
        posts_combinados = posts_google + posts_facebook
        if posts_combinados:
            supabase_admin.table('radar_cidades_posts').insert(posts_combinados).execute()

        # ── FONTE 3: Feedbacks locais (WhatsApp dos cidadaos) ─────────────────
        feedbacks_cidade = []
        try:
            todos_feedbacks = get_feedbacks()
            cidade_lower = cidade.lower().strip()
            feedbacks_cidade = [
                f for f in todos_feedbacks
                if (f.get('city') or '').lower().strip() == cidade_lower
            ][:25]
            print(f"[Radar MG] Feedbacks locais: {len(feedbacks_cidade)} mensagens")
        except Exception as e_fb:
            print(f"[Radar MG] Feedbacks locais falhou: {e_fb}")

        # ── OPENAI — analise com tres fontes separadas ────────────────────────
        openai_client = __import__('openai').OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        textos_google = "\n---\n".join([p['conteudo'] for p in posts_google[:15]]) or \
                        f"Nenhuma notícia encontrada sobre {cidade} MG."
        textos_facebook = "\n---\n".join([p['conteudo'] for p in posts_facebook[:30]]) or \
                          f"Nenhum post público de grupos do Facebook encontrado sobre {cidade} MG."

        if feedbacks_cidade:
            fb_linhas = []
            for f in feedbacks_cidade:
                msg = (f.get('message') or '').strip()[:400]
                cat = f.get('category') or 'outros'
                urg = f.get('urgency') or 'neutro'
                if msg:
                    fb_linhas.append(f"[{cat} · {urg}] {msg}")
            textos_feedbacks = "\n---\n".join(fb_linhas)
        else:
            textos_feedbacks = f"Nenhum feedback direto de cidadão via WhatsApp para {cidade} ainda."

        prompt_analise = f"""Você é um analista político especializado em Minas Gerais.

Analise os dados coletados de TRÊS fontes sobre a cidade de {cidade} - MG:

NOTÍCIAS DA MÍDIA LOCAL (imprensa, portais):
{textos_google}

POSTS PÚBLICOS DE GRUPOS DO FACEBOOK (opinião pública online):
{textos_facebook}

FEEDBACKS DIRETOS DE CIDADÃOS (mensagens via WhatsApp do canal do deputado):
{textos_feedbacks}

Retorne um JSON com esta estrutura exata:
{{
  "resumo": "Resumo executivo geral em 3 linhas, cruzando as três fontes. Se houver divergência entre o que a mídia reporta e o que a população fala, destaque.",
  "resumo_midia": "Síntese em 3-4 linhas focada APENAS no que está SAINDO NA MÍDIA (notícias Google News). O que a imprensa está noticiando sobre a cidade? Cite assuntos, pautas e tom da cobertura. Se não houver notícias, diga 'Sem cobertura de mídia encontrada no período.'",
  "resumo_voz_povo": "Síntese em 3-4 linhas do SENTIMENTO DA POPULAÇÃO, combinando posts do Facebook e feedbacks diretos via WhatsApp. Quais queixas, demandas e elogios os moradores estão expressando? Se só houver uma das fontes, use a disponível. Se nenhuma, diga 'Sem voz direta da população capturada.'",
  "sentimento_geral": "positivo|negativo|neutro|misto",
  "temas": [
    {{
      "tema": "Nome do tema",
      "categoria": "saude|transporte|seguranca|educacao|infraestrutura|meio_ambiente|economia|outros",
      "mencoes": 0,
      "sentimento_predominante": "positivo|negativo|neutro",
      "exemplos": ["exemplo 1", "exemplo 2"]
    }}
  ],
  "oportunidades_politicas": ["oportunidade 1", "oportunidade 2"],
  "sugestao_trafego_pago": "Sugestão de copy para anúncio direcionado para esta cidade"
}}

Retorne APENAS o JSON, sem explicações."""

        ai_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_analise}],
            temperature=0.3
        )

        ai_text = ai_response.choices[0].message.content.strip()
        if '```json' in ai_text:
            ai_text = ai_text.split('```json')[1].split('```')[0].strip()
        elif '```' in ai_text:
            ai_text = ai_text.split('```')[1].split('```')[0].strip()

        ai_data = json.loads(ai_text)

        # Salva temas
        temas = ai_data.get('temas', [])
        if temas:
            supabase_admin.table('radar_cidades_temas').insert([{
                'pesquisa_id': pesquisa_id,
                'tema': t.get('tema', ''),
                'categoria': t.get('categoria', 'outros'),
                'mencoes': t.get('mencoes', 0),
                'sentimento_predominante': t.get('sentimento_predominante', 'neutro'),
                'exemplos': t.get('exemplos', [])
            } for t in temas]).execute()

        # Atualiza pesquisa como concluída
        supabase_admin.table('radar_cidades_pesquisas').update({
            'status': 'concluido',
            'total_posts': len(posts_combinados),
            'resumo_ia': ai_data.get('resumo', '')
        }).eq('id', pesquisa_id).execute()

        return jsonify({
            'success': True,
            'pesquisa_id': pesquisa_id,
            'cidade': cidade,
            'total_posts': len(posts_combinados),
            'total_noticias': len(posts_google),
            'total_posts_facebook': len(posts_facebook),
            'total_feedbacks_locais': len(feedbacks_cidade),
            'resumo': ai_data.get('resumo', ''),
            'resumo_midia': ai_data.get('resumo_midia', ''),
            'resumo_voz_povo': ai_data.get('resumo_voz_povo', ''),
            'sentimento_geral': ai_data.get('sentimento_geral', 'neutro'),
            'temas': temas,
            'oportunidades_politicas': ai_data.get('oportunidades_politicas', []),
            'sugestao_trafego_pago': ai_data.get('sugestao_trafego_pago', '')
        })

    except Exception as e:
        print(f"[Radar MG] Erro geral: {e}")
        try:
            if pesquisa_id:
                supabase_admin.table('radar_cidades_pesquisas').update({
                    'status': 'erro'
                }).eq('id', pesquisa_id).execute()
        except:
            pass
        return jsonify({'error': str(e)}), 500


@app.route('/api/radar-mg/pesquisas', methods=['GET'])
def radar_mg_listar_pesquisas():
    """Lista todas as pesquisas já realizadas"""
    try:
        pesquisas = supabase.table('radar_cidades_pesquisas')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(20)\
            .execute()

        return jsonify({'pesquisas': pesquisas.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ibge/<cidade>')
def _ibge_cidade_internal(cidade: str) -> dict | None:
    """Versão pura (sem Flask) para uso interno por outros módulos como o Marcos.
    Retorna dict com dados IBGE ou None se cidade não encontrada.
    Pode levantar exceção em caso de erro de rede."""
    import unicodedata

    def normalize(s: str) -> str:
        return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII').lower()

    def extrair_ultimo_valor(item: dict) -> tuple:
        res_list = item.get('res', [])
        if not res_list:
            return None, None
        serie = res_list[0].get('res', {})
        for ano in sorted(serie.keys(), reverse=True):
            val = serie[ano]
            if val is not None:
                return val, ano
        return None, None

    cidade_norm = normalize(cidade)

    loc_url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/MG/municipios"
    loc_resp = requests.get(loc_url, timeout=10)
    municipios = loc_resp.json() if loc_resp.status_code == 200 else []

    codigo = None
    nome_oficial = cidade
    for m in municipios:
        if normalize(m.get('nome', '')) == cidade_norm:
            codigo = m['id']
            nome_oficial = m['nome']
            break

    if not codigo:
        for m in municipios:
            if cidade_norm in normalize(m.get('nome', '')):
                codigo = m['id']
                nome_oficial = m['nome']
                break

    if not codigo:
        return None

    resultado = {
        'cidade': nome_oficial,
        'codigo_ibge': codigo,
        'estado': 'MG'
    }

    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/pesquisas/-/indicadores/29171|47001|29167|29170/resultados/{codigo}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            for item in resp.json():
                ind_id = item.get('id')
                val, ano = extrair_ultimo_valor(item)
                if not val:
                    continue
                if ind_id == 29171:
                    resultado['populacao'] = int(val)
                    resultado['populacao_ano'] = ano
                elif ind_id == 47001:
                    resultado['pib_per_capita'] = round(float(val), 2)
                    resultado['pib_ano'] = ano
                elif ind_id == 29167:
                    resultado['area_km2'] = round(float(val), 3)
                elif ind_id == 29170:
                    resultado['prefeito'] = val.title()
    except Exception as e:
        print(f"[IBGE] Erro pesquisas panorama: {e}")

    try:
        idh_url = f"https://servicodados.ibge.gov.br/api/v1/pesquisas/10111/indicadores/329756/resultados/{codigo}"
        idh_resp = requests.get(idh_url, timeout=10)
        if idh_resp.status_code == 200:
            dados = idh_resp.json()
            if dados:
                val, ano = extrair_ultimo_valor(dados[0])
                if val:
                    resultado['idh'] = float(val)
                    resultado['idh_ano'] = ano
    except Exception as e:
        print(f"[IBGE] Erro IDHM: {e}")

    if resultado.get('populacao') and resultado.get('area_km2'):
        resultado['densidade'] = round(resultado['populacao'] / resultado['area_km2'], 1)

    return resultado


def ibge_cidade(cidade):
    """Busca dados do IBGE via API de pesquisas (mesma usada pelo IBGE Cidades)"""
    try:
        resultado = _ibge_cidade_internal(cidade)
        if resultado is None:
            return jsonify({'error': f'Cidade "{cidade}" não encontrada no IBGE', 'cidade': cidade}), 404
        return jsonify(resultado)
    except Exception as e:
        print(f"[IBGE] Erro: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pitch-estrategico', methods=['POST'])
def _pitch_estrategico_internal(cidade: str) -> dict:
    """Versão pura (sem Flask) do pitch estratégico para uso interno por Marcos etc.
    Retorna dict com o pitch ou lança ValueError para erros conhecidos."""
    cidade = (cidade or "").strip()
    if not cidade:
        raise ValueError("cidade_obrigatoria")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("openai_key_ausente")

    # ── 1. Feedbacks da cidade ──────────────────────────────────────────
    feedbacks = get_feedbacks()
    fb_cidade = [f for f in feedbacks if (f.get('city') or '').lower() == cidade.lower()]

    # Contagens por categoria
    cat_counts = {}
    urgency_counts = {}
    topics = []
    for fb in fb_cidade:
        cat = fb.get('category', 'Outros')
        urg = fb.get('urgency', 'Neutro')
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
        topics.append(fb.get('topic', ''))

    # Top categorias e mensagens recentes
    top_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    msgs_recentes = [fb.get('message', '')[:150] for fb in fb_cidade[:15]]

    # ── 2. Radar MG — temas e resumos ──────────────────────────────────
    radar_resumos = []
    radar_temas = []

    if supabase:
        try:
            pesquisas = supabase.table('radar_cidades_pesquisas') \
                .select('id, resumo_ia, created_at') \
                .ilike('cidade', cidade) \
                .eq('status', 'concluido') \
                .order('created_at', desc=True) \
                .limit(3) \
                .execute()

            for p in pesquisas.data:
                if p.get('resumo_ia'):
                    radar_resumos.append(p['resumo_ia'])
                pesq_id = p.get('id')
                if pesq_id:
                    temas = supabase.table('radar_cidades_temas') \
                        .select('tema, categoria, mencoes, sentimento_predominante') \
                        .eq('pesquisa_id', pesq_id) \
                        .order('mencoes', desc=True) \
                        .limit(10) \
                        .execute()
                    radar_temas.extend(temas.data)
        except Exception as e:
            print(f"[Pitch] Erro ao buscar Radar MG: {e}")

    # Deduplicar temas do radar
    temas_unicos = {}
    for t in radar_temas:
        nome = t.get('tema', '')
        if nome not in temas_unicos:
            temas_unicos[nome] = t
        else:
            temas_unicos[nome]['mencoes'] = max(temas_unicos[nome].get('mencoes', 0), t.get('mencoes', 0))
    radar_temas_dedup = sorted(temas_unicos.values(), key=lambda x: x.get('mencoes', 0), reverse=True)[:8]

    # ── 3. Montar prompt para IA ────────────────────────────────────────
    fb_section = "NENHUM FEEDBACK DISPONÍVEL"
    if fb_cidade:
        fb_lines = []
        for cat, count in top_cats:
            fb_lines.append(f"  - {cat}: {count} feedbacks")
        urg_lines = []
        for urg, count in sorted(urgency_counts.items(), key=lambda x: x[1], reverse=True):
            urg_lines.append(f"  - {urg}: {count}")
        msg_lines = "\n".join([f'  - "{m}"' for m in msgs_recentes[:10]])
        fb_section = f"""Total de feedbacks: {len(fb_cidade)}

Por categoria:
{chr(10).join(fb_lines)}

Por urgência:
{chr(10).join(urg_lines)}

Mensagens recentes dos cidadãos:
{msg_lines}"""

    radar_section = "NENHUM DADO DO RADAR MG DISPONÍVEL"
    if radar_resumos or radar_temas_dedup:
        parts = []
        if radar_resumos:
            parts.append("Resumos de inteligência (mídia + redes sociais):\n" + "\n---\n".join(radar_resumos[:2]))
        if radar_temas_dedup:
            tema_lines = [f"  - {t['tema']} ({t.get('categoria','')}, {t.get('mencoes',0)} menções, sentimento: {t.get('sentimento_predominante','')})" for t in radar_temas_dedup]
            parts.append("Principais temas detectados:\n" + "\n".join(tema_lines))
        radar_section = "\n\n".join(parts)

    prompt = f"""Você é um estrategista político experiente em Minas Gerais.

Um deputado estadual vai visitar a cidade de {cidade} - MG. Precisa de um pitch estratégico para saber O QUE FALAR e COMO SE POSICIONAR.

Cruze os dados abaixo e gere um briefing executivo:

═══ FEEDBACKS DOS CIDADÃOS (WhatsApp) ═══
{fb_section}

═══ RADAR MG — INTELIGÊNCIA DE MÍDIA E REDES ═══
{radar_section}

Gere um JSON com esta estrutura:
{{
  "titulo": "Briefing Estratégico — {cidade}",
  "panorama": "Resumo de 3-4 linhas do cenário político da cidade",
  "temas_quentes": [
    {{
      "tema": "Nome do tema",
      "relevancia": "alta|media|baixa",
      "sentimento_popular": "positivo|negativo|misto",
      "o_que_falar": "Frase ou argumento estratégico para o político usar",
      "cuidado": "O que NÃO dizer ou evitar"
    }}
  ],
  "frase_de_abertura": "Sugestão de frase para abrir discurso/entrevista na cidade",
  "dados_impacto": ["Dado numérico 1 para citar", "Dado numérico 2"],
  "oportunidades": ["Oportunidade política 1", "Oportunidade 2"],
  "riscos": ["Risco ou tema sensível 1", "Risco 2"],
  "tom_recomendado": "Descrição do tom ideal (combativo, conciliador, técnico, etc.)"
}}

IMPORTANTE: Seja específico para {cidade}. Use os dados reais dos feedbacks e radar. Não invente dados — se não houver informação suficiente, indique isso.
Retorne APENAS o JSON."""

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=2000
    )

    ai_text = response.choices[0].message.content.strip()
    if '```json' in ai_text:
        ai_text = ai_text.split('```json')[1].split('```')[0].strip()
    elif '```' in ai_text:
        ai_text = ai_text.split('```')[1].split('```')[0].strip()

    pitch_data = json.loads(ai_text)
    pitch_data['meta'] = {
        'cidade': cidade,
        'total_feedbacks': len(fb_cidade),
        'total_radar_temas': len(radar_temas_dedup),
        'categorias_feedbacks': dict(top_cats),
        'gerado_em': datetime.utcnow().isoformat()
    }
    return pitch_data


def pitch_estrategico():
    """Gera pitch estratégico para o político visitar uma cidade, cruzando feedbacks + Radar MG"""
    try:
        data = request.get_json() or {}
        cidade = (data.get('cidade') or '').strip()
        return jsonify(_pitch_estrategico_internal(cidade))
    except ValueError as ve:
        msg = str(ve)
        if msg == "cidade_obrigatoria":
            return jsonify({'error': 'Cidade é obrigatória'}), 400
        if msg == "openai_key_ausente":
            return jsonify({'error': 'OpenAI API key não configurada'}), 500
        return jsonify({'error': msg}), 400
    except json.JSONDecodeError as e:
        print(f"[Pitch] Erro ao parsear JSON da IA: {e}")
        return jsonify({'error': 'Erro ao processar resposta da IA'}), 500
    except Exception as e:
        print(f"[Pitch] Erro geral: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Google Calendar — OAuth + criacao de eventos a partir dos chamados
# =============================================================================

def _calendar_redirect_uri() -> str:
    override = os.getenv("GOOGLE_REDIRECT_URI")
    if override:
        return override
    return url_for("calendar_oauth_callback", _external=True)


@app.route("/api/calendar/status", methods=["GET"])
@login_required
def calendar_status():
    try:
        from google_calendar import status_integracao
        status = status_integracao(supabase_admin)
        convidados_padrao = [e.strip() for e in (os.getenv("GOOGLE_CALENDAR_CONVIDADOS_PADRAO") or "").split(",") if e.strip()]
        status["convidados_padrao"] = convidados_padrao
        return jsonify(status)
    except Exception as e:
        print(f"[calendar] status erro: {e}")
        return jsonify({"conectado": False, "erro": str(e)})


@app.route("/api/calendar/oauth/start", methods=["GET"])
@login_required
def calendar_oauth_start():
    try:
        from google_calendar import build_flow, SCOPES  # noqa
    except Exception as e:
        return jsonify({"error": f"dependencia_ausente: {e}"}), 500

    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        return jsonify({"error": "google_oauth_nao_configurado"}), 503

    state = secrets.token_urlsafe(24)
    session["google_oauth_state"] = state
    try:
        from google_calendar import build_flow
        flow = build_flow(_calendar_redirect_uri(), state=state)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        # PKCE — precisa do mesmo code_verifier no callback
        if getattr(flow, "code_verifier", None):
            session["google_oauth_code_verifier"] = flow.code_verifier
        return redirect(auth_url)
    except Exception as e:
        print(f"[calendar] oauth start erro: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/calendar/oauth/callback", methods=["GET"])
@login_required
def calendar_oauth_callback():
    code = request.args.get("code")
    state_retornado = request.args.get("state")
    state_esperado = session.pop("google_oauth_state", None)
    erro = request.args.get("error")

    html_fechamento = """<!doctype html><meta charset="utf-8"><title>Google Calendar</title>
<style>body{font-family:system-ui;background:#0b1220;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.card{background:#111827;border:1px solid #1f2937;border-radius:14px;padding:32px;max-width:420px;text-align:center}
.ok{color:#22c55e}.err{color:#ef4444}</style>
<div class="card">{corpo}<p style="margin-top:16px;font-size:.82rem;color:#94a3b8">Pode fechar esta janela.</p></div>
<script>setTimeout(()=>{try{window.opener&&window.opener.postMessage({type:'google-calendar-connected',success:{sucesso}},'*')}catch(e){}window.close()},1500)</script>"""

    if erro:
        return html_fechamento.replace("{corpo}", f'<h3 class="err">Autorização recusada</h3><p>{erro}</p>').replace("{sucesso}", "false")
    if not code or not state_retornado or state_retornado != state_esperado:
        return html_fechamento.replace("{corpo}", '<h3 class="err">Falha na autorização</h3><p>State inválido ou ausente.</p>').replace("{sucesso}", "false")

    try:
        from google_calendar import build_flow, salvar_credentials
        flow = build_flow(_calendar_redirect_uri(), state=state_retornado)
        code_verifier = session.pop("google_oauth_code_verifier", None)
        if code_verifier:
            flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        creds = flow.credentials

        email = ""
        try:
            id_token = (creds.id_token or "")
            if id_token:
                import base64 as _b64
                partes = id_token.split(".")
                if len(partes) >= 2:
                    payload = partes[1] + "=" * (-len(partes[1]) % 4)
                    email = json.loads(_b64.urlsafe_b64decode(payload)).get("email", "")
        except Exception:
            pass

        salvar_credentials(supabase_admin, creds, email=email)
        print(f"[calendar] Conta conectada: {email or '(sem id_token)'}")
        return html_fechamento.replace("{corpo}", '<h3 class="ok">Google Calendar conectado!</h3><p>Token salvo com segurança.</p>').replace("{sucesso}", "true")
    except Exception as e:
        print(f"[calendar] callback erro: {e}")
        return html_fechamento.replace("{corpo}", f'<h3 class="err">Erro ao salvar token</h3><p>{e}</p>').replace("{sucesso}", "false")


@app.route("/api/calendar/disconnect", methods=["POST"])
@login_required
def calendar_disconnect():
    try:
        from google_calendar import desconectar
        desconectar(supabase_admin)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/calendar/disponibilidade", methods=["POST"])
@login_required
def api_calendar_disponibilidade():
    """Checa conflitos de agenda no intervalo informado."""
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        return jsonify({"error": "google_oauth_nao_configurado"}), 503

    payload = request.json or {}
    inicio_raw = (payload.get("inicio") or "").strip()
    duracao = int(payload.get("duracao_min") or 60)
    if not inicio_raw or duracao < 5:
        return jsonify({"error": "parametros_invalidos"}), 400

    try:
        if inicio_raw.endswith("Z"):
            inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
        else:
            inicio = datetime.fromisoformat(inicio_raw)
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone(timedelta(hours=-3)))
    except Exception:
        return jsonify({"error": "inicio_invalido"}), 400
    fim = inicio + timedelta(minutes=duracao)

    try:
        from google_calendar import listar_eventos_periodo
        eventos = listar_eventos_periodo(supabase_admin, _calendar_redirect_uri(), inicio, fim)
    except RuntimeError as e:
        if str(e) == "google_calendar_desconectado":
            return jsonify({"error": "google_calendar_desconectado"}), 401
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[calendar] check disponibilidade: {e}")
        return jsonify({"error": "falha_ao_consultar"}), 502

    conflitos = [e for e in eventos if e.get("transparencia") != "transparent"]
    return jsonify({
        "livre": len(conflitos) == 0,
        "conflitos": conflitos,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    })


@app.route("/api/operacao-local/agendar", methods=["POST"])
@login_required
def api_agendar_reuniao_operacao():
    """Cria evento no Google Calendar a partir do contexto de um chamado de campo.

    Payload:
      - atualizacao_id (int, opcional)
      - inicio (ISO 8601 com timezone ou naive em America/Sao_Paulo)
      - duracao_min (int, default 60)
      - titulo (str, opcional)
      - local (str, opcional)
      - descricao (str, opcional)
      - mensagem_whatsapp (str, opcional — se presente, envia ao operador com link)
    """
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        return jsonify({"error": "google_oauth_nao_configurado"}), 503

    data = request.json or {}
    inicio_raw = (data.get("inicio") or "").strip()
    if not inicio_raw:
        return jsonify({"error": "inicio_obrigatorio"}), 400

    try:
        if inicio_raw.endswith("Z"):
            inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
        else:
            inicio = datetime.fromisoformat(inicio_raw)
        if inicio.tzinfo is None:
            # assume horario de Sao Paulo
            inicio = inicio.replace(tzinfo=timezone(timedelta(hours=-3)))
    except Exception:
        return jsonify({"error": "inicio_invalido"}), 400

    duracao = int(data.get("duracao_min") or 60)
    if duracao < 15 or duracao > 480:
        return jsonify({"error": "duracao_invalida"}), 400
    fim = inicio + timedelta(minutes=duracao)

    atualizacao = None
    if data.get("atualizacao_id"):
        atualizacao = buscar_atualizacao_campo_por_id(data.get("atualizacao_id"))

    cidade = (atualizacao or {}).get("cidade") or data.get("cidade") or ""
    tema = (atualizacao or {}).get("tema_principal") or data.get("tema") or ""
    operador_nome = (atualizacao or {}).get("operador_nome") or ""

    titulo_padrao = f"Reunião em {cidade}" + (f" — {tema}" if tema else "")
    titulo = (data.get("titulo") or titulo_padrao or "Reunião de campo").strip()[:200]
    local = (data.get("local") or (f"{cidade}, MG" if cidade else "")).strip()[:200]

    descricao_partes = []
    if data.get("descricao"):
        descricao_partes.append(data["descricao"].strip())
    if atualizacao:
        descricao_partes.append(f"Chamado de campo · Operador: {operador_nome}")
        resumo = atualizacao.get("resumo") or atualizacao.get("mensagem_original") or ""
        if resumo:
            descricao_partes.append(resumo[:600])
        proxima = atualizacao.get("proxima_acao") or ""
        if proxima:
            descricao_partes.append(f"Próxima ação: {proxima}")
    descricao = "\n\n".join(descricao_partes)[:3000]

    convidados_brutos = data.get("convidados") or ""
    if isinstance(convidados_brutos, list):
        convidados_lista = [str(e).strip() for e in convidados_brutos]
    else:
        convidados_lista = [e.strip() for e in str(convidados_brutos).split(",")]
    convidados_padrao = [e.strip() for e in (os.getenv("GOOGLE_CALENDAR_CONVIDADOS_PADRAO") or "").split(",")]
    convidados_final = []
    for email in convidados_lista + convidados_padrao:
        if email and "@" in email and email not in convidados_final:
            convidados_final.append(email)

    try:
        from google_calendar import criar_evento
        evento = criar_evento(
            supabase_admin,
            _calendar_redirect_uri(),
            summary=titulo,
            inicio=inicio,
            fim=fim,
            descricao=descricao,
            local=local,
            convidados=convidados_final or None,
        )
    except RuntimeError as e:
        if str(e) == "google_calendar_desconectado":
            return jsonify({"error": "google_calendar_desconectado"}), 401
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[calendar] criar evento erro: {e}")
        return jsonify({"error": "falha_ao_criar_evento"}), 502

    link_evento = evento.get("html_link") or ""
    enviou_whatsapp = False
    mensagem_texto = (data.get("mensagem_whatsapp") or "").strip()
    if mensagem_texto and atualizacao:
        destino_raw = atualizacao.get("operador_jid") or ""
        destino = _jid_para_envio(destino_raw)
        if destino and len(destino) >= 10 and EVOLUTION_API_URL and EVOLUTION_API_KEY and EVOLUTION_INSTANCE_NAME:
            corpo = mensagem_texto
            if link_evento:
                corpo += f"\n\n📅 Agenda confirmada: {link_evento}"
            try:
                send_whatsapp_message(destino, corpo)
                enviou_whatsapp = True
                salvar_mensagem_operacao({
                    "atualizacao_id": atualizacao.get("id"),
                    "destinatario_jid": destino,
                    "destinatario_nome": operador_nome or "Operador",
                    "cidade": cidade,
                    "direcao": "enviada",
                    "canal": "whatsapp",
                    "texto": corpo,
                    "autor": session.get("user") or "gabinete",
                    "enviada_em": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                print(f"[calendar] Falha ao enviar WhatsApp com link: {e}")

    print(f"[calendar] Evento criado id={evento.get('id')} cidade={cidade} operador={operador_nome}")
    return jsonify({
        "success": True,
        "evento": evento,
        "whatsapp_enviado": enviou_whatsapp,
    }), 201


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5004))
    print(f"🏛️ Política Node Data running on port {port}")
    if supabase:
        print("📦 Using Supabase database")
    else:
        print("📁 Using local JSON files")
    app.run(host="0.0.0.0", port=port)
