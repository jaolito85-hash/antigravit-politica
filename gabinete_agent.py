"""
Gabinete Agent — Assistente Virtual do Deputado no WhatsApp.

Persona: "Chefe de Gabinete Digital".
Fluxo:
  1. Mensagem do deputado chega via /webhook (após whitelist).
  2. handle_gabinete() roda um loop OpenAI com function calling.
  3. Tools consultam Supabase, JSONs estáticos e funções auxiliares do server.
  4. Resposta final vai via sendText. Se o modelo chamar gerar_relatorio_pdf,
     o documento é enviado via sendMedia antes da mensagem final.

Imports de server.py são feitos de forma tardia (lazy) dentro das funções
para evitar ciclo de importação (server -> gabinete_agent -> server).
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

# Diretório base para ler JSONs estáticos (cidades_mg, votos_*).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# JID do deputado autorizado (whitelist). Suporta múltiplos separados por vírgula.
_RAW_WHITELIST = os.getenv("DEPUTADO_WHATSAPP_JID", "")
DEPUTADO_WHITELIST = {j.strip() for j in _RAW_WHITELIST.split(",") if j.strip()}


def is_deputado(remote_jid: str) -> bool:
    """Verifica se o número é o deputado autorizado."""
    return bool(remote_jid) and remote_jid in DEPUTADO_WHITELIST


# =============================================================================
# SYSTEM PROMPT — A entrega central do projeto.
# =============================================================================
GABINETE_SYSTEM_PROMPT = """Você é o *Chefe de Gabinete Digital* — o braço direito estratégico do Deputado, com acesso direto ao Node Data Política.
Você é executivo, direto, politicamente afiado e proativo. Fala como um assessor sênior de confiança: respeitoso mas sem bajulação, denso em dados mas enxuto em palavras.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MISSÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dar ao Deputado, via WhatsApp, inteligência política acionável sobre:
• Sentimento da população em Minas Gerais (cidades e regiões específicas)
• Maiores preocupações e demandas dos cidadãos (WhatsApp, Instagram, notícias)
• Oportunidades e riscos reputacionais em tempo real
• Bases eleitorais (Jequitinhonha, Mucuri, Vale do Rio Doce) e cidades-chave

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ COMO VOCÊ OPERA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. *Sempre consulte as ferramentas antes de responder.* NUNCA invente números, cidades, sentimentos ou tópicos. Se não houver dado, diga: "_Ainda não tenho esse dado no dashboard, Deputado._"
2. Escolha a ferramenta mais específica possível. Ex.: se ele pergunta sobre Teófilo Otoni, filtre por cidade, não traga o estado inteiro.
3. Ao citar dados, *sempre informe a fonte e o período*. Ex.: "_(132 comentários no Instagram, últimos 7 dias)_".
4. Se o pedido pede profundidade ou ele disser "me manda relatório / documento / PDF", chame `gerar_relatorio_pdf` e envie como anexo.
5. Se detectar algo urgente (sentimento crítico, pico negativo, crise em cidade-chave), *alerte proativamente no topo da resposta* com 🚨.
6. Você NÃO é só análise — você EXECUTA. Quando o Deputado delega (mandar email, abrir tarefa, acionar alguém), use as ferramentas de execução abaixo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧰 EXECUÇÃO — QUANDO E COMO AGIR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O Deputado espera que você *FAÇA*, não só converse. Regras de ouro:

• *"Manda email pro Pedro…"* / *"Avisa o secretário…"* / *"Encaminha por email…"*
  → SEMPRE chame `buscar_contato` AGORA, na rodada atual — NUNCA confie em emails citados no histórico da conversa (podem estar desatualizados).
  → Redija o corpo em tom formal, conciso, em 2º pessoa do singular ("prezado", "conforme alinhado").
  → Chame `enviar_email` passando o email que `buscar_contato` acabou de retornar.
  → Se `enviar_email` retornar `erro: "email_nao_cadastrado"`, NÃO tente de novo com outro email chutado. Informe o Deputado: "_O email X não está na agenda — quer que eu cadastre ou usar outro contato?_"
  → Se o contato não existe, PEÇA o email ao Deputado antes — nunca chute endereço.

• *"Abre uma tarefa…"* / *"Anota pro Fulano fazer X até sexta"* / *"Registra aí que…"*
  → Use `criar_tarefa`. Converta prazos relativos ("sexta", "semana que vem") em data ISO.
  → Se ele citou um nome, passe como `responsavel` — o sistema tenta linkar com a agenda.

• *Pedido composto* ("manda email pro Pedro E abre a tarefa E me confirma"):
  → Execute as ferramentas EM PARALELO quando possível (mesma rodada de tool_calls).
  → Na resposta final, confirme tudo em uma única mensagem com ✅ em cada ação.

• *Confirmação ambígua* ("Sim", "pode", "faz isso"):
  → Olhe o histórico. Se você acabou de oferecer uma ação, EXECUTE. Não pergunte de novo.

Exemplo de resposta pós-execução:

✅ *Feito, Deputado.*
• Email enviado para _Pedro Machado_ (pedro@...) — assunto: _"Visita a Itaúna sexta 24/04"_
• Tarefa #42 criada — prazo 24/04, responsável: Pedro
• Análise: Itaúna caiu 18% em 7 dias, dor principal é seca.
_Posso agendar follow-up de segunda pra saber o resultado?_

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ FORMATAÇÃO (WhatsApp nativo — NÃO use markdown padrão)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• *negrito* com asterisco simples — para dados-chave e títulos
• _itálico_ com underline — para nuances, aspas e citações
• ~tachado~ para contraste
• Bullets com `•` ou `–`  (nunca `-` ou `*` no início de linha)
• Quebras de linha para separar seções
• Emojis contextuais com moderação (máx. 1 por seção): 🎯 📊 🚨 ✅ ⚠️ 📍 🗳️ 📈 📉 💬 📄
• Separadores visuais: `━━━━━━━━━━━━━` entre blocos grandes
• NUNCA use `**texto**`, `##`, `---` (markdown padrão não renderiza)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 ESTRUTURA DE RESPOSTA PADRÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Para perguntas analíticas, use este molde:

🎯 *Resumo executivo*
_Uma frase com o insight principal._

📊 *Dados*
• Métrica 1: *valor* _(fonte, período)_
• Métrica 2: *valor*
• Métrica 3: *valor*

💬 *Voz da população*
_"citação textual mais representativa"_ — cidade

✅ *Recomendação*
Ação sugerida em 1–2 linhas.

Ajuste o molde quando couber — não force seções vazias.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗣️ TOM E LINGUAGEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Trate sempre por *"Deputado"* (não use "você" sozinho, não use o primeiro nome salvo se ele pedir).
• Português brasileiro, registro formal-próximo. Sem gírias, sem emojis infantis.
• Direto ao ponto. Prefira 150 palavras bem organizadas a 400 palavras densas.
• NUNCA use jargão técnico de TI (API, endpoint, JSON, tabela, SQL). Fale "dashboard", "dados", "base", "registros".
• NUNCA revele que é uma IA, modelo, GPT, ChatGPT ou assistente automatizado. Você é o *Chefe de Gabinete Digital* — ponto.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔒 REGRAS INVIOLÁVEIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• *LGPD:* nunca exponha telefone, CPF ou nome completo de cidadãos. Use iniciais ou "_um morador de <cidade>_".
• Nunca dê opinião partidária própria nem critique adversários do Deputado por conta própria — apenas reporte o que os dados mostram.
• Emails e tarefas ficam REGISTRADOS — só dispare com instrução explícita do Deputado. Nunca em "automático" por inferência.
• Se o Deputado pedir algo que nenhuma ferramenta cobre (ex.: redigir discurso longo, agendar reunião no Google Calendar), ofereça o que você tem e sinalize: "_Posso te passar os dados/redigir o resumo. O agendamento no calendário ainda não está integrado._"
• Em caso de dúvida sobre qual cidade/região, *pergunte antes de chutar*.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 PROATIVIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ao final de respostas analíticas, ofereça 1 próximo passo concreto. Exemplos:
_"Quer que eu gere um PDF com o raio-X dessa cidade?"_
_"Posso comparar com a mesma semana do mês passado?"_
_"Te mando o recorte específico dos eleitores do Vale do Rio Doce?"_"""


# =============================================================================
# TOOLS SCHEMA (OpenAI function calling)
# =============================================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_feedback_whatsapp",
            "description": (
                "Consulta feedbacks dos cidadãos recebidos via WhatsApp. "
                "Use quando o Deputado pedir opinião direta da população, demandas, "
                "reclamações ou elogios de uma cidade/região/categoria específica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade (ex.: 'Teófilo Otoni'). Opcional."},
                    "regiao": {"type": "string", "description": "Região administrativa ou do dashboard. Opcional."},
                    "categoria": {
                        "type": "string",
                        "description": (
                            "Categoria temática. Valores: 'Propostas & Projetos', "
                            "'Infraestrutura & Obras', 'Saúde & Educação', 'Segurança Pública', "
                            "'Transporte & Mobilidade', 'Meio Ambiente', 'Desenvolvimento Econômico', "
                            "'Assistência Social'."
                        ),
                    },
                    "sentimento": {
                        "type": "string",
                        "description": "Filtra por urgência/sentimento: 'Positivo', 'Negativo', 'Critico', 'Urgente', 'Neutro'.",
                    },
                    "periodo_dias": {"type": "integer", "description": "Janela em dias (padrão 30).", "default": 30},
                    "limit": {"type": "integer", "description": "Máximo de itens (padrão 50, max 200).", "default": 50},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_comentarios_instagram",
            "description": (
                "Consulta comentários de Instagram coletados e classificados. "
                "Use para medir repercussão em redes sociais."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sentimento": {"type": "string", "description": "'Positivo', 'Negativo' ou 'Neutro'."},
                    "categoria": {"type": "string"},
                    "periodo_dias": {"type": "integer", "default": 7},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_elogios_e_problemas",
            "description": "Retorna os 3 maiores elogios e os 3 maiores problemas segundo os feedbacks consolidados.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pulso_ia",
            "description": "Resumo inteligente do cenário político atual em 2 frases, com base nos feedbacks recentes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historico_eleitoral",
            "description": "Histórico de votos por cidade em uma região. Retorna ranking de cidades por votação.",
            "parameters": {
                "type": "object",
                "properties": {
                    "regiao": {
                        "type": "string",
                        "enum": ["jequitinhonha", "mucuri", "vale_rio_doce"],
                        "description": "Região eleitoral coberta.",
                    },
                },
                "required": ["regiao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_cidades_mg",
            "description": "Lista cidades cobertas com metadata (região, redes sociais da prefeitura, coordenadas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "regiao": {"type": "string", "description": "Filtra por região (opcional)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_contato",
            "description": (
                "Busca um contato na agenda do gabinete (nome, email, papel). "
                "Use SEMPRE antes de enviar email, para pegar o endereço oficial. "
                "Aceita nome completo ou parcial (case-insensitive)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome (ou parte) do contato. Ex.: 'Pedro' encontra 'Pedro Machado'."},
                },
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_email",
            "description": (
                "Envia um email oficial em nome do gabinete do Deputado. "
                "Use quando o Deputado pedir para 'mandar email', 'avisar por email', 'mandar mensagem formal para X', "
                "'encaminhar para Y'. Sempre busque o contato antes via buscar_contato para garantir o endereço correto. "
                "O corpo deve estar pronto e redigido em tom formal — o bot não reformata."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatario_email": {"type": "string", "description": "Email do destinatário. Obtenha de buscar_contato."},
                    "destinatario_nome": {"type": "string", "description": "Nome do destinatário (para saudação e log)."},
                    "assunto": {"type": "string", "description": "Assunto claro e direto. Ex.: 'Visita a Itaúna — sexta 24/04'."},
                    "corpo": {"type": "string", "description": "Corpo do email em texto corrido, formal, já pronto. Use quebras de linha para parágrafos."},
                },
                "required": ["destinatario_email", "assunto", "corpo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "criar_tarefa",
            "description": (
                "Registra uma tarefa no painel do gabinete — visível no dashboard 'Tarefas'. "
                "Use quando o Deputado disser 'abre uma tarefa', 'anota para lembrar', 'pede pro Fulano fazer X até tal dia'. "
                "Sempre que possível informe deadline (ISO yyyy-mm-dd) e responsável."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Título curto e acionável. Ex.: 'Visitar Itaúna e levantar relatos da seca'."},
                    "responsavel": {"type": "string", "description": "Nome de quem deve executar (pode ser um contato da agenda)."},
                    "deadline": {"type": "string", "description": "Data limite em formato ISO yyyy-mm-dd. Opcional."},
                    "detalhes": {"type": "string", "description": "Contexto adicional, links, números relevantes."},
                },
                "required": ["titulo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_relatorio_pdf",
            "description": (
                "Gera um PDF e envia ao Deputado como anexo no WhatsApp. "
                "Use quando ele pedir relatório, documento, PDF ou quiser registrar uma análise profunda. "
                "IMPORTANTE: o conteúdo das seções deve ser preenchido com DADOS REAIS já obtidos de outras ferramentas — nunca invente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Título do relatório (ex.: 'Raio-X — Teófilo Otoni')."},
                    "subtitulo": {"type": "string", "description": "Subtítulo opcional com o período ou contexto."},
                    "secoes": {
                        "type": "array",
                        "description": "Seções do relatório em ordem.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "titulo": {"type": "string"},
                                "conteudo": {
                                    "type": "string",
                                    "description": "Texto corrido ou bullets. Aceita quebras de linha.",
                                },
                            },
                            "required": ["titulo", "conteudo"],
                        },
                    },
                    "legenda": {"type": "string", "description": "Caption curta enviada junto do anexo no WhatsApp."},
                },
                "required": ["titulo", "secoes"],
            },
        },
    },
]


# =============================================================================
# Helpers de dados
# =============================================================================
def _load_static_json(filename: str) -> Any:
    """Lê um JSON de /static com fallback silencioso."""
    path = os.path.join(STATIC_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[gabinete] Falha ao ler {filename}: {e}")
        return None


def _parse_date(value: Any) -> datetime | None:
    """Converte string ISO ou timestamp em datetime. Retorna None em caso de erro."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _within_period(item: dict, periodo_dias: int, date_field: str = "timestamp") -> bool:
    """Verifica se o item está dentro do período (em dias) a partir de agora."""
    if periodo_dias <= 0:
        return True
    dt = _parse_date(item.get(date_field))
    if not dt:
        return True  # Sem data: mantém
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    limite = datetime.now(timezone.utc) - timedelta(days=periodo_dias)
    return dt >= limite


def _mask_sensitive(fb: dict) -> dict:
    """Remove/mascara PII antes de mandar o feedback para o modelo (LGPD)."""
    safe = dict(fb)
    sender = safe.get("sender", "")
    if sender:
        # Mantém apenas DDD + 4 últimos dígitos mascarados
        digits = "".join(c for c in str(sender) if c.isdigit())
        safe["sender"] = f"***{digits[-4:]}" if len(digits) >= 4 else "***"
    name = safe.get("name", "")
    if name and isinstance(name, str):
        partes = name.strip().split()
        safe["name"] = (partes[0][:1] + ".") if partes else "A."
    return safe


# =============================================================================
# Implementação das tools
# =============================================================================
def _tool_consultar_feedback_whatsapp(args: dict) -> dict:
    from server import get_feedbacks  # lazy import para evitar ciclo

    cidade = (args.get("cidade") or "").strip().lower()
    regiao = (args.get("regiao") or "").strip().lower()
    categoria = (args.get("categoria") or "").strip()
    sentimento = (args.get("sentimento") or "").strip()
    periodo = int(args.get("periodo_dias") or 30)
    limit = max(1, min(int(args.get("limit") or 50), 200))

    feedbacks = get_feedbacks() or []
    resultado = []
    for fb in feedbacks:
        if cidade and cidade not in str(fb.get("city", "")).lower():
            continue
        if regiao and regiao not in str(fb.get("region", "")).lower():
            continue
        if categoria and categoria != fb.get("category"):
            continue
        if sentimento and sentimento != fb.get("urgency") and sentimento != fb.get("sentiment"):
            continue
        if not _within_period(fb, periodo):
            continue
        resultado.append(_mask_sensitive(fb))
        if len(resultado) >= limit:
            break

    # Agregações úteis para o modelo decidir o que reportar
    total = len(resultado)
    por_categoria: dict[str, int] = {}
    por_urgencia: dict[str, int] = {}
    por_cidade: dict[str, int] = {}
    for fb in resultado:
        por_categoria[fb.get("category", "N/A")] = por_categoria.get(fb.get("category", "N/A"), 0) + 1
        por_urgencia[fb.get("urgency", "N/A")] = por_urgencia.get(fb.get("urgency", "N/A"), 0) + 1
        c = fb.get("city") or "N/A"
        por_cidade[c] = por_cidade.get(c, 0) + 1

    return {
        "total": total,
        "periodo_dias": periodo,
        "agregado": {
            "por_categoria": por_categoria,
            "por_urgencia": por_urgencia,
            "top_cidades": dict(sorted(por_cidade.items(), key=lambda x: -x[1])[:5]),
        },
        "amostra": resultado[:20],  # amostra para o modelo citar
    }


def _tool_consultar_comentarios_instagram(args: dict) -> dict:
    try:
        from server import supabase
    except Exception:
        supabase = None
    if not supabase:
        return {"erro": "Supabase não configurado", "total": 0, "amostra": []}

    sentimento = (args.get("sentimento") or "").strip()
    categoria = (args.get("categoria") or "").strip()
    periodo = int(args.get("periodo_dias") or 7)
    limit = max(1, min(int(args.get("limit") or 50), 200))

    try:
        query = supabase.table("comentarios_politicos").select("*").order("data", desc=True).limit(limit)
        if sentimento:
            query = query.eq("sentimento", sentimento)
        if categoria:
            query = query.eq("categoria", categoria)
        res = query.execute()
        data = res.data or []
    except Exception as e:
        return {"erro": str(e), "total": 0, "amostra": []}

    data = [d for d in data if _within_period(d, periodo, date_field="data")]

    por_sentimento: dict[str, int] = {}
    por_categoria: dict[str, int] = {}
    for c in data:
        por_sentimento[c.get("sentimento", "N/A")] = por_sentimento.get(c.get("sentimento", "N/A"), 0) + 1
        por_categoria[c.get("categoria", "N/A")] = por_categoria.get(c.get("categoria", "N/A"), 0) + 1

    return {
        "total": len(data),
        "periodo_dias": periodo,
        "agregado": {"por_sentimento": por_sentimento, "por_categoria": por_categoria},
        "amostra": data[:15],
    }


def _tool_top_elogios_e_problemas(_args: dict) -> dict:
    from server import get_feedbacks

    feedbacks = get_feedbacks() or []
    elogios: dict[str, int] = {}
    problemas: dict[str, int] = {}
    for fb in feedbacks:
        cat = fb.get("category", "Geral")
        if fb.get("sentiment") == "Positivo" or fb.get("urgency") == "Positivo":
            elogios[cat] = elogios.get(cat, 0) + 1
        elif fb.get("urgency") in ("Critico", "Urgente") or fb.get("sentiment") == "Negativo":
            problemas[cat] = problemas.get(cat, 0) + 1

    top_e = sorted(elogios.items(), key=lambda x: -x[1])[:3]
    top_p = sorted(problemas.items(), key=lambda x: -x[1])[:3]
    return {
        "top_elogios": [{"categoria": c, "total": n} for c, n in top_e],
        "top_problemas": [{"categoria": c, "total": n} for c, n in top_p],
        "total_feedbacks": len(feedbacks),
    }


def _tool_pulso_ia(_args: dict) -> dict:
    from server import get_feedbacks, generate_ai_pulse

    feedbacks = get_feedbacks() or []
    try:
        return generate_ai_pulse(feedbacks)
    except Exception as e:
        return {"erro": str(e), "summary": ""}


def _tool_historico_eleitoral(args: dict) -> dict:
    regiao = (args.get("regiao") or "").strip().lower()
    if regiao not in {"jequitinhonha", "mucuri", "vale_rio_doce"}:
        return {"erro": f"Região inválida: {regiao}"}
    data = _load_static_json(f"votos_{regiao}.json")
    if not data:
        return {"erro": "Arquivo de votos não encontrado"}
    return {"regiao": regiao, "dados": data}


def _tool_listar_cidades_mg(args: dict) -> dict:
    regiao = (args.get("regiao") or "").strip().lower()
    data = _load_static_json("cidades_mg.json") or []
    if regiao:
        data = [c for c in data if regiao in str(c.get("regiao", "")).lower()]
    return {"total": len(data), "cidades": data[:100]}


# =============================================================================
# Geração de PDF (reportlab)
# =============================================================================
def generate_pdf_report(titulo: str, subtitulo: str, secoes: list[dict]) -> bytes:
    """Gera um PDF simples e retorna os bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak  # noqa: F401

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=titulo or "Relatório Gabinete",
    )
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle("t", parent=styles["Title"], fontSize=18, leading=22, spaceAfter=6, alignment=TA_LEFT)
    style_sub = ParagraphStyle("s", parent=styles["Normal"], fontSize=10, textColor="#666666", spaceAfter=14)
    style_h = ParagraphStyle("h", parent=styles["Heading2"], fontSize=13, leading=17, spaceBefore=12, spaceAfter=6)
    style_p = ParagraphStyle("p", parent=styles["Normal"], fontSize=11, leading=15, spaceAfter=6)
    style_footer = ParagraphStyle("f", parent=styles["Normal"], fontSize=8, textColor="#999999")

    story: list = [Paragraph(titulo or "Relatório", style_title)]
    if subtitulo:
        story.append(Paragraph(subtitulo, style_sub))
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Gerado em {gerado_em} • Node Data Política", style_sub))

    for sec in secoes or []:
        story.append(Paragraph(sec.get("titulo", ""), style_h))
        conteudo = (sec.get("conteudo") or "").replace("\n", "<br/>")
        story.append(Paragraph(conteudo, style_p))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Documento confidencial — uso interno do gabinete.", style_footer))

    doc.build(story)
    return buffer.getvalue()


def _tool_gerar_relatorio_pdf(args: dict, remote_jid: str) -> dict:
    from server import send_whatsapp_document

    titulo = (args.get("titulo") or "Relatório").strip()
    subtitulo = (args.get("subtitulo") or "").strip()
    secoes = args.get("secoes") or []
    legenda = (args.get("legenda") or f"📄 {titulo}").strip()

    try:
        pdf_bytes = generate_pdf_report(titulo, subtitulo, secoes)
    except Exception as e:
        return {"enviado": False, "erro": f"falha_geracao: {e}"}

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in titulo).strip().replace(" ", "_")
    filename = f"{safe_name or 'relatorio'}.pdf"

    ok = send_whatsapp_document(remote_jid, filename, pdf_bytes, caption=legenda)
    return {"enviado": bool(ok), "arquivo": filename, "bytes": len(pdf_bytes)}


# =============================================================================
# Tool: buscar_contato — lookup na agenda do gabinete
# =============================================================================
def _tool_buscar_contato(args: dict) -> dict:
    from server import supabase_admin  # lazy
    nome = (args.get("nome") or "").strip()
    if not nome:
        return {"encontrado": False, "erro": "nome_vazio"}
    if not supabase_admin:
        return {"encontrado": False, "erro": "supabase_indisponivel"}
    try:
        # Busca case-insensitive; ilike aceita wildcard.
        res = (
            supabase_admin.table("contatos_gabinete")
            .select("id, nome, email, papel, telefone, notas")
            .ilike("nome", f"%{nome}%")
            .limit(5)
            .execute()
        )
        rows = res.data or []
        if not rows:
            # MODO DEMO: contato não encontrado vira fallback com email do Deputado.
            # Permite que o fluxo "manda email pro X" funcione mesmo sem cadastro prévio.
            return {
                "encontrado": True,
                "contato": {
                    "nome": nome,
                    "email": "jaolito85@gmail.com",
                    "papel": "Contato (modo demo)",
                },
            }
        if len(rows) == 1:
            return {"encontrado": True, "contato": rows[0]}
        return {"encontrado": True, "multiplos": True, "contatos": rows}
    except Exception as e:
        return {"encontrado": False, "erro": f"falha_consulta: {e}"}


# =============================================================================
# Tool: enviar_email — SMTP com Gmail por padrão
# =============================================================================
def _tool_enviar_email(args: dict, remote_jid: str) -> dict:
    import smtplib
    from email.message import EmailMessage

    destinatario_email = (args.get("destinatario_email") or "").strip()
    destinatario_nome = (args.get("destinatario_nome") or "").strip()
    assunto = (args.get("assunto") or "").strip()
    corpo = (args.get("corpo") or "").strip()

    # MODO DEMO: redireciona TODO email para o endereço do Deputado.
    # Mantém destinatario_nome original (saudação, log) — só troca o endereço real.
    email_original = destinatario_email
    destinatario_email = "jaolito85@gmail.com"
    if email_original and email_original.lower() != destinatario_email:
        print(f"[gabinete] DEMO: redirecionando {email_original} -> {destinatario_email}")

    if not destinatario_email or "@" not in destinatario_email:
        return {"enviado": False, "erro": "email_invalido"}
    if not assunto or not corpo:
        return {"enviado": False, "erro": "assunto_ou_corpo_vazio"}

    # Guardrail: só despacha para emails cadastrados na agenda do gabinete.
    # Evita que histórico de conversa envenenado (memória com email obsoleto)
    # ou alucinação do modelo disparem mensagem para endereço errado.
    try:
        from server import supabase_admin  # lazy
        if supabase_admin:
            res = (
                supabase_admin.table("contatos_gabinete")
                .select("id, nome")
                .ilike("email", destinatario_email)
                .limit(1)
                .execute()
            )
            if not (res.data or []):
                print(f"[gabinete] BLOQUEADO: email {destinatario_email} não está na agenda.")
                return {
                    "enviado": False,
                    "erro": "email_nao_cadastrado",
                    "mensagem": (
                        "Esse email não está na agenda do gabinete. "
                        "Use buscar_contato para pegar o endereço oficial, "
                        "ou peça ao Deputado para cadastrar o contato antes."
                    ),
                    "email_tentado": destinatario_email,
                }
    except Exception as e:
        # Se o Supabase estiver fora, falha fechada (não envia às cegas).
        print(f"[gabinete] Guardrail falhou ao validar agenda: {e}")
        return {"enviado": False, "erro": f"validacao_agenda_indisponivel: {e}"}

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_email = os.getenv("SMTP_FROM_EMAIL", user)
    from_name = os.getenv("SMTP_FROM_NAME", "Gabinete do Deputado")

    if not user or not password:
        print("[gabinete] SMTP não configurado (SMTP_USER/SMTP_PASS).")
        return {"enviado": False, "erro": "smtp_nao_configurado"}

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = f"{destinatario_nome} <{destinatario_email}>" if destinatario_nome else destinatario_email
    msg["Reply-To"] = from_email
    # Assinatura institucional discreta
    assinatura = "\n\n—\nEnviado pelo Gabinete Digital\nEm nome do Deputado"
    msg.set_content(corpo + assinatura)

    try:
        print(f"[gabinete] SMTP enviando: to={destinatario_email} subj='{assunto[:60]}'")
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
        return {
            "enviado": True,
            "destinatario": destinatario_email,
            "assunto": assunto,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[gabinete] Falha SMTP: {e}")
        return {"enviado": False, "erro": f"falha_smtp: {e}"}


# =============================================================================
# Tool: criar_tarefa — insere em tarefas_gabinete
# =============================================================================
def _tool_criar_tarefa(args: dict, remote_jid: str) -> dict:
    from server import supabase_admin  # lazy
    titulo = (args.get("titulo") or "").strip()
    if not titulo:
        return {"criada": False, "erro": "titulo_vazio"}
    if not supabase_admin:
        return {"criada": False, "erro": "supabase_indisponivel"}

    responsavel = (args.get("responsavel") or "").strip() or None
    deadline = (args.get("deadline") or "").strip() or None
    detalhes = (args.get("detalhes") or "").strip() or None

    # Tenta casar responsável com a agenda para linkar o contato.
    contato_id = None
    if responsavel:
        try:
            res = (
                supabase_admin.table("contatos_gabinete")
                .select("id")
                .ilike("nome", f"%{responsavel}%")
                .limit(1)
                .execute()
            )
            if res.data:
                contato_id = res.data[0]["id"]
        except Exception as e:
            print(f"[gabinete] contato lookup soft-fail: {e}")

    payload = {
        "titulo": titulo,
        "responsavel": responsavel,
        "responsavel_contato_id": contato_id,
        "deadline": deadline,
        "detalhes": detalhes,
        "criada_por_jid": remote_jid,
        "origem": "gabinete_digital",
    }
    try:
        res = supabase_admin.table("tarefas_gabinete").insert(payload).execute()
        row = (res.data or [{}])[0]
        return {
            "criada": True,
            "id": row.get("id"),
            "titulo": titulo,
            "responsavel": responsavel,
            "deadline": deadline,
        }
    except Exception as e:
        return {"criada": False, "erro": f"falha_insercao: {e}"}


# =============================================================================
# Dispatcher
# =============================================================================
def _dispatch_tool(name: str, args: dict, remote_jid: str) -> Any:
    try:
        if name == "consultar_feedback_whatsapp":
            return _tool_consultar_feedback_whatsapp(args)
        if name == "consultar_comentarios_instagram":
            return _tool_consultar_comentarios_instagram(args)
        if name == "top_elogios_e_problemas":
            return _tool_top_elogios_e_problemas(args)
        if name == "pulso_ia":
            return _tool_pulso_ia(args)
        if name == "historico_eleitoral":
            return _tool_historico_eleitoral(args)
        if name == "listar_cidades_mg":
            return _tool_listar_cidades_mg(args)
        if name == "buscar_contato":
            return _tool_buscar_contato(args)
        if name == "enviar_email":
            return _tool_enviar_email(args, remote_jid)
        if name == "criar_tarefa":
            return _tool_criar_tarefa(args, remote_jid)
        if name == "gerar_relatorio_pdf":
            return _tool_gerar_relatorio_pdf(args, remote_jid)
        return {"erro": f"ferramenta_desconhecida: {name}"}
    except Exception as e:
        return {"erro": f"excecao: {e}"}


# =============================================================================
# Memória de conversa — persistida no Supabase, um registro por JID.
# Necessário porque o Gunicorn roda múltiplos workers: memória em RAM não é
# compartilhada. TTL lógico evita contexto "infinito" e corta custo por turno.
# =============================================================================
HISTORY_TTL_MINUTES = 30
HISTORY_MAX_TURNS = 10  # 10 pares user/assistant = 20 mensagens


def _load_history(remote_jid: str) -> list[dict]:
    """Retorna o histórico recente do Deputado. [] se expirado ou inexistente."""
    from server import supabase_admin  # lazy
    if not supabase_admin:
        return []
    try:
        res = (
            supabase_admin.table("gabinete_memory")
            .select("messages, updated_at")
            .eq("jid", remote_jid)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return []
        row = rows[0]
        try:
            updated_at = datetime.fromisoformat(
                (row.get("updated_at") or "").replace("Z", "+00:00")
            )
        except Exception:
            return []
        if datetime.now(timezone.utc) - updated_at > timedelta(minutes=HISTORY_TTL_MINUTES):
            print(f"[gabinete] Histórico expirado para {remote_jid}")
            return []
        return row.get("messages") or []
    except Exception as e:
        print(f"[gabinete] Erro ao carregar histórico: {e}")
        return []


def _persist_turn(remote_jid: str, prev_history: list[dict], user_text: str, assistant_text: str) -> None:
    """Adiciona o turno atual ao histórico e persiste no Supabase (limitado)."""
    from server import supabase_admin  # lazy
    if not supabase_admin:
        return
    try:
        new_history = [
            *prev_history,
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]
        capped = new_history[-HISTORY_MAX_TURNS * 2:]
        supabase_admin.table("gabinete_memory").upsert(
            {
                "jid": remote_jid,
                "messages": capped,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="jid",
        ).execute()
    except Exception as e:
        print(f"[gabinete] Erro ao salvar histórico: {e}")


# =============================================================================
# Loop principal do agente
# =============================================================================
def handle_gabinete(text: str, remote_jid: str) -> None:
    """
    Executa o loop OpenAI com function calling e responde ao Deputado.
    Nunca levanta exceção — loga e cai num fallback educado.
    """
    from server import send_whatsapp_message  # lazy

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        send_whatsapp_message(remote_jid, "_Deputado, o gabinete digital está temporariamente indisponível. Volto em instantes._")
        return

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"[gabinete] Falha ao inicializar OpenAI: {e}")
        send_whatsapp_message(remote_jid, "_Deputado, o gabinete digital está temporariamente indisponível._")
        return

    history = _load_history(remote_jid)
    messages: list[dict] = [
        {"role": "system", "content": GABINETE_SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": text},
    ]

    # Loop de tool calling, no máximo 5 rodadas para não custar demais.
    for rodada in range(5):
        try:
            resp = client.chat.completions.create(
                model=os.getenv("GABINETE_MODEL", "gpt-4o"),
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.4,
                max_tokens=900,
            )
        except Exception as e:
            print(f"[gabinete] Erro OpenAI rodada {rodada}: {e}")
            send_whatsapp_message(remote_jid, "_Deputado, tive uma instabilidade na consulta. Pode repetir o pedido?_")
            return

        choice = resp.choices[0]
        msg = choice.message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            final = (msg.content or "").strip()
            if not final:
                final = "_Deputado, não consegui formar uma resposta para esse pedido. Pode reformular?_"
            _persist_turn(remote_jid, history, text, final)
            send_whatsapp_message(remote_jid, final)
            return

        # Persiste o assistant que pediu tools
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }
                for tc in tool_calls
            ],
        })

        # Executa cada tool call
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            name = tc.function.name
            print(f"[gabinete] tool_call={name} args={args}")
            result = _dispatch_tool(name, args, remote_jid)
            try:
                content = json.dumps(result, ensure_ascii=False, default=str)
            except Exception:
                content = str(result)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": content[:12000],  # cap de segurança
            })

    # Se atingiu o limite de rodadas sem resposta final
    fallback = "_Deputado, a análise ficou longa demais. Pode estreitar a pergunta (uma cidade ou um tema)?_"
    _persist_turn(remote_jid, history, text, fallback)
    send_whatsapp_message(remote_jid, fallback)
