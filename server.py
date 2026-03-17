import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import os
import requests
import json
import hashlib
import csv
import re
from io import StringIO
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from functools import wraps
import feedparser
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter, defaultdict
from time import time as time_now

# Absolute path based on this file's location — prevents loading wrong .env
# when server is started from a different working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.getenv("SECRET_KEY", "politica-nodedata-secret-2024")

# Credenciais de acesso
APP_USERNAME = os.getenv("APP_USERNAME", "matheuslima")
APP_PASSWORD = os.getenv("APP_PASSWORD", "2702")

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
    public_routes = {"login_page", "logout", "static", "service_worker", "manifest"}
    if request.endpoint in public_routes:
        return
    if not session.get("logged_in"):
        if request.path.startswith("/api/") or request.path.startswith("/webhook"):
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
            supabase_admin.table('feedbacks').insert(data).execute()
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
  "regiao": "Centro" | "Zona Norte" | "Zona Sul" | "Zona Leste" | "Zona Oeste" | "Distrito Industrial" | "Zona Rural" | "N/A"
}}

Regras de categoria:
- Propostas & Projetos: votações, projetos de lei, mandatos, gestão pública, transparência
- Desenvolvimento Econômico: emprego, empresa, comércio, investimento, polo industrial
- Saúde & Educação: hospital, UBS, escola, creche, professor, medicamento
- Segurança Pública: crime, violência, polícia, guarda municipal, tráfico
- Critico = corrupção comprovada, emergências, denúncias graves
- Urgente = promessas não cumpridas, descaso, problemas graves sem solução
- Positivo = elogios, projetos aprovados, agradecimentos
- Neutro = perguntas, sugestões, informações neutras'''

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

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == APP_USERNAME and password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Usuário ou senha incorretos."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/")
def index():
    return render_template("data_node.html")


@app.route("/api/events")
def get_events():
    feedbacks = get_feedbacks()

    categoria = request.args.get('categoria')
    regiao = request.args.get('regiao')
    prioridade = request.args.get('prioridade')
    status_filter = request.args.get('status')

    if categoria:
        feedbacks = [f for f in feedbacks if f.get('category') == categoria]
    if regiao:
        feedbacks = [f for f in feedbacks if f.get('region') == regiao]
    if prioridade:
        feedbacks = [f for f in feedbacks if f.get('urgency') == prioridade]
    if status_filter:
        feedbacks = [f for f in feedbacks if f.get('status', 'aberto') == status_filter]

    return jsonify(feedbacks)


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
    writer = csv.DictWriter(output, fieldnames=['id', 'message', 'category', 'urgency', 'timestamp', 'status', 'sender', 'name', 'region'])
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
            'region': fb.get('region')
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

    for fb in feedbacks:
        cat = fb.get('category', '')
        reg = fb.get('region', '')
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        if reg and reg != 'N/A':
            region_counts[reg] = region_counts.get(reg, 0) + 1

    for cat in config.get('categories', []):
        cat['count'] = category_counts.get(cat['name'], 0)

    for reg in config.get('regions', []):
        reg['count'] = region_counts.get(reg['name'], 0)

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


def _classificar_chunk(textos, politico):
    """Classifica um chunk de até 30 comentários em 1 chamada OpenAI."""
    default = {"sentimento": "Neutro", "categoria": "Propostas & Projetos"}
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not textos:
        return [default] * len(textos)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        items_text = "\n".join([f"{i+1}. \"{t[:300]}\"" for i, t in enumerate(textos)])
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"Classifique cada comentário sobre {politico}. "
                    "Responda SOMENTE com JSON array compacto (sem espaços extras), "
                    "um objeto por linha, na mesma ordem dos comentários:\n"
                    '[{"sentimento":"Positivo|Negativo|Neutro","categoria":"..."}]\n'
                    "Categorias: Propostas & Projetos | Infraestrutura & Obras | "
                    "Saúde & Educação | Segurança Pública | Transporte & Mobilidade | "
                    "Meio Ambiente | Desenvolvimento Econômico | Assistência Social\n\n"
                    f"Comentários:\n{items_text}"
                )
            }],
            max_tokens=len(textos) * 40 + 200,
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
            categoria = item.get("categoria", "Propostas & Projetos")
            if sentimento not in ("Positivo", "Negativo", "Neutro"):
                sentimento = "Neutro"
            results.append({"sentimento": sentimento, "categoria": categoria})
        while len(results) < len(textos):
            results.append(default)
        return results[:len(textos)]
    except Exception as e:
        print(f"❌ Batch classify error: {e}")
        return [default] * len(textos)


def _classificar_batch(textos, politico, chunk_size=30):
    """
    Classifica comentários em batch, dividindo em chunks de 30 para não truncar tokens.
    Retorna lista de dicts: [{sentimento, categoria}, ...]
    """
    if not textos:
        return []
    results = []
    for i in range(0, len(textos), chunk_size):
        chunk = textos[i:i + chunk_size]
        print(f"🤖 Classificando chunk {i//chunk_size + 1} ({len(chunk)} comentários)...")
        results.extend(_classificar_chunk(chunk, politico))
    return results


def fetch_instagram_comments(username, politico, n_posts=5, comments_per_post=200):
    """
    Fluxo dois passos:
      1. apify~instagram-scraper  → pega os N posts mais recentes do perfil
         (latestComments é só preview de 3-5, ignoramos — usamos só shortCode/url/timestamp)
      2. apify~instagram-comment-scraper → pega TODOS os comentários de cada post
         (directUrls=[post_url_1,...], resultsLimit=comments_per_post por post)
    Resultado cacheado por 1h para economizar crédito Apify.
    """
    if not APIFY_TOKEN:
        return None

    username_clean = username.lstrip("@").strip()
    chave = f"ig2_{username_clean}_{n_posts}"  # ig2_ para não conflitar com cache antigo
    agora_ts = time_now()

    if chave in _instagram_cache:
        if agora_ts - _instagram_cache[chave]["ts"] < CACHE_TTL:
            print(f"📸 Cache hit Instagram @{username_clean}")
            return _instagram_cache[chave]["data"]

    profile_url = f"https://www.instagram.com/{username_clean}/"
    print(f"📸 [1/2] Buscando posts de @{username_clean}...")

    try:
        # ── PASSO 1: pegar posts do perfil ─────────────────────────────────
        posts = _apify_run("apify~instagram-scraper", {
            "directUrls": [profile_url],
            "resultsType": "posts",
            "resultsLimit": n_posts,
            "proxy": {"useApifyProxy": True}
        })

        if not posts:
            print(f"⚠️ Nenhum post encontrado para @{username_clean}")
            return None

        # Ordenar por timestamp — mais recente primeiro
        def _ts(p):
            t = p.get("timestamp") or p.get("taken_at_timestamp") or 0
            return t if isinstance(t, (int, float)) else 0

        posts_sorted = sorted(posts, key=_ts, reverse=True)[:n_posts]

        # Extrair URLs dos posts
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

        # ── PASSO 2: buscar TODOS os comentários dos posts ──────────────────
        # Retorna: text, ownerUsername, timestamp, postUrl
        raw_comments = _apify_run("apify~instagram-comment-scraper", {
            "directUrls": post_urls,
            "resultsLimit": comments_per_post,  # por URL/post
        })

        if not raw_comments:
            print("⚠️ Nenhum comentário encontrado nos posts")
            return None

        print(f"✅ {len(raw_comments)} comentários brutos. Classificando em batch...")

        # ── PASSO 3: batch classify — UMA chamada OpenAI para todos ────────
        textos = [(c.get("text") or "").strip() for c in raw_comments]
        indices_validos = [i for i, t in enumerate(textos) if len(t) >= 5]
        textos_validos = [textos[i] for i in indices_validos]

        classificacoes = _classificar_batch(textos_validos, politico)
        cl_map = {indices_validos[i]: classificacoes[i] for i in range(len(indices_validos))}
        default_cl = {"sentimento": "Neutro", "categoria": "Propostas & Projetos"}

        # ── PASSO 4: montar resultados ──────────────────────────────────────
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
                "sentimento": cl["sentimento"],
                "categoria": cl["categoria"],
                "post_url": c.get("postUrl") or "",
                "data": data_c,
            })

        print(f"✅ {len(resultados)} comentários prontos para @{username_clean}")
        _instagram_cache[chave] = {"ts": agora_ts, "data": resultados}
        # Persistir em disco para sobreviver a reloads de página e reinícios do servidor
        save_json(LAST_COMMENTS_FILE, {
            "username": username_clean,
            "politico": politico,
            "comentarios": resultados
        })
        # Persistir no Supabase (permanente)
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
    Com APIFY_TOKEN + username: busca comentários reais do Instagram.
    Sem token ou username: retorna dados mock.
    """
    from datetime import timedelta, timezone
    periodo  = request.args.get('periodo', '7d')
    politico = request.args.get('politico', '')
    username = request.args.get('username', '')

    # Dados reais do Instagram
    if APIFY_TOKEN and username:
        real_data = fetch_instagram_comments(username, politico or username)
        if real_data is not None:
            # Não filtramos por data: já buscamos os N posts mais recentes,
            # filtrar por período cortaria comentários de posts mais antigos
            return jsonify(real_data)

    # Fallback: último scrape real salvo em disco (nunca dados fictícios)
    saved = load_json(LAST_COMMENTS_FILE, {})
    return jsonify(saved.get("comentarios", []))


@app.route("/api/radar-comentarios/cache")
def radar_comentarios_cache():
    """Retorna comentários salvos no Supabase SEM disparar Apify."""
    if supabase:
        try:
            resp = supabase.table('comentarios_politicos') \
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
    Body: { "urls": ["https://instagram.com/p/..."], "contexto": "Nikolas Ferreira" }
    """
    data = request.get_json(force=True) or {}
    urls = data.get("urls", [])
    contexto = data.get("contexto", "político")

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

        # Passo 3: Classificar com IA
        textos = [(c.get("text") or "").strip() for c in filtrados]
        classificacoes = _classificar_batch(textos, contexto)

        # Passo 4: Montar resultados
        resultados = []
        for i, c in enumerate(filtrados):
            texto = (c.get("text") or "").strip()
            data_c = c.get("timestamp") or datetime.utcnow().isoformat()
            if isinstance(data_c, (int, float)):
                from datetime import timezone as tz
                data_c = datetime.fromtimestamp(data_c, tz=tz.utc).isoformat()

            cl = classificacoes[i] if i < len(classificacoes) else {"sentimento": "Neutro", "categoria": "Outro"}
            resultados.append({
                "id": i + 1,
                "usuario": c.get("ownerUsername", ""),
                "texto": texto[:400],
                "sentimento": cl["sentimento"],
                "categoria": cl["categoria"],
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

    if not comentarios:
        return jsonify({"error": "Sem comentários para analisar"}), 400

    total  = len(comentarios)
    pos    = sum(1 for c in comentarios if c.get("sentimento") == "Positivo")
    neg    = sum(1 for c in comentarios if c.get("sentimento") == "Negativo")
    neutro = total - pos - neg

    cat_count = {}
    for c in comentarios:
        cat = c.get("categoria", "Outros")
        cat_count[cat] = cat_count.get(cat, 0) + 1
    top_cats = sorted(cat_count.items(), key=lambda x: x[1], reverse=True)[:5]

    neg_samples = [c["trecho"] for c in comentarios if c.get("sentimento") == "Negativo"][:8]
    pos_samples = [c["trecho"] for c in comentarios if c.get("sentimento") == "Positivo"][:5]

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

        prompt = f"""Você é um estrategista político sênior. Analise os dados de comentários do Instagram do político {politico}.

MÉTRICAS:
- Total: {total} comentários  |  Positivos: {pos} ({pct_pos}%)  |  Negativos: {neg} ({pct_neg}%)  |  Neutros: {neutro} ({pct_neutro}%)

Top categorias mencionadas:
{cats_text}

Amostras de comentários negativos:
{neg_text}

Amostras de comentários positivos:
{pos_text}

Gere uma análise estratégica respondendo SOMENTE em JSON:
{{
  "situacao": "análise da situação atual em 2 frases objetivas",
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
                print(f"[AI-FIRST] Classified: {categoria} / {sentimento} / {regiao}")
            else:
                print(f"[FALLBACK] AI failed, using keywords...")
                sentimento = classificar_sentimento(text)
                categoria = classificar_categoria(text)
                regiao = classificar_regiao(text)

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
                "status": "aberto"
            }

            save_feedback(new_report)

            # Reply via Marcos persona
            reply = generate_ai_response(text, categoria, sentimento, protocol_num)
            send_whatsapp_message(remote_jid, reply)

            return jsonify({"status": "processed", "protocol": protocol_num}), 200

    return jsonify({"status": "ignored"}), 200


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


# ============================================================
# RADAR MG — Inteligência por cidade de Minas Gerais
# ============================================================

@app.route('/radar-mg')
def radar_mg():
    return render_template('data_node.html', active_page='radar_mg')


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

        # ── OPENAI — análise com duas fontes ──────────────────────────────────
        openai_client = __import__('openai').OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        textos_google = "\n---\n".join([p['conteudo'] for p in posts_google[:15]]) or \
                        f"Nenhuma notícia encontrada sobre {cidade} MG."
        textos_facebook = "\n---\n".join([p['conteudo'] for p in posts_facebook[:30]]) or \
                          f"Nenhum post público de grupos do Facebook encontrado sobre {cidade} MG."

        prompt_analise = f"""Você é um analista político especializado em Minas Gerais.

Analise os dados coletados de duas fontes sobre a cidade de {cidade} - MG:

NOTÍCIAS DA MÍDIA LOCAL:
{textos_google}

OPINIÃO DA POPULAÇÃO (Facebook):
{textos_facebook}

Retorne um JSON com esta estrutura exata:
{{
  "resumo": "Resumo executivo em 3 linhas. Se houver divergência entre o que a mídia reporta e o que a população fala, destaque isso.",
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
            'resumo': ai_data.get('resumo', ''),
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5004))
    print(f"🏛️ Política Node Data running on port {port}")
    if supabase:
        print("📦 Using Supabase database")
    else:
        print("📁 Using local JSON files")
    app.run(host="0.0.0.0", port=port)
