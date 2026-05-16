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
2. Escolha a ferramenta mais específica possível. Ex.: se ele pergunta sobre Teófilo Otoni, filtre por cidade, não traga o estado inteiro. Para perguntas sobre 'liderança', 'prefeito', 'vereador' ou 'operador' de uma cidade/região, use `buscar_operador_campo` — NÃO `buscar_contato` (essa é só para a agenda institucional do gabinete).
3. Ao citar dados, *sempre informe a fonte e o período*. Ex.: "_(132 comentários no Instagram, últimos 7 dias)_".
4. Se o pedido pede profundidade ou ele disser "me manda relatório / documento / PDF", chame `gerar_relatorio_pdf` e envie como anexo.
5. Se detectar algo urgente (sentimento crítico, pico negativo, crise em cidade-chave), *alerte proativamente no topo da resposta* com 🚨.
6. Você NÃO é só análise — você EXECUTA. Quando o Deputado delega (mandar email, abrir tarefa, acionar alguém), use as ferramentas de execução abaixo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧰 EXECUÇÃO — QUANDO E COMO AGIR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O Deputado espera que você *FAÇA*, não só converse. Regras de ouro:

• *"Manda whatsapp pro Eduardo…"* / *"Avisa o prefeito de X pelo zap…"* / *"Fala com o vereador…"*
  → Use `enviar_mensagem_operador`. Só funciona com operadores cadastrados (prefeitos, vereadores, lideranças, voluntários do painel).
  → Se nome for ambíguo, passe `cidade` para desambiguar. Se vier `multiplos_operadores`, peça ao Deputado pra escolher.
  → Texto direto, em nome do gabinete (sem "Olá, sou o Marcos"). Não mande email + whatsapp pra mesma coisa.
  → Se o erro for `operador_nao_encontrado`, NÃO chute número — informe ao Deputado e pergunte se quer cadastrar.

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
🎬 ANÁLISE DE VÍDEOS E PODCASTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Quando o Deputado mandar uma URL do YouTube, Spotify ou Apple Podcasts:

• *Pedido inicial* ("Marcos, analisa esse vídeo", URL colada solta, "rebata isso aí"):
  → Use `analisar_video_url`. Se ele não disse, assuma `tipo: adversario`.
  → Responda CURTO: "_Tá rodando. Leva 2-4 minutos. Te aviso quando ficar pronto, ou me chama de novo daqui a pouco._" — NÃO espere o resultado.

• *Cobrar resultado* ("Já ficou pronto?", "Cadê aquele resumo?"):
  → Use `consultar_video_analise`. Se ainda não terminou, informe o progresso. Se terminou, traga:
    – Tese central em 1 linha
    – Top 3 pontos de atenção com timestamp e severidade
    – Sentimento e tom do entrevistado

• *Pedido de munição* ("Me dá um tweet", "story sobre isso", "como rebato?"):
  → Use `consultar_video_analise` e entregue diretamente UM tweet pronto + UM story pronto + UM contra-argumento curto.
  → Tweet máximo 280 caracteres, sem hashtags genéricas.

• *Histórico* ("Lista o que a gente analisou", "Vídeos do Caporezzo?"):
  → Use `listar_videos_analisados` com filtros de candidato/tipo/periodo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗓️ PLANEJAMENTO SEMANAL E POR CIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• *"Briefing agora", "panorama da semana", "o que tá pegando"*:
  → Use `briefing_radar_completo`. NÃO use `pulso_ia` que é mais raso.
  → Cite os 3 a 5 temas quentes com sentimento e ação concreta.
  → Se infiltração de adversário > 10%, *destaque no topo* da resposta.

• *"Qual cidade visitar?", "onde tá pegando fogo?", "prioridade da semana"*:
  → Use `prioridades_semana` com limit 3.
  → Apresente como ranking enxuto: cidade, score, motivo principal, ação.

• *"Vou em X amanhã, me passa um pitch", "discurso pra evento em Y"*:
  → Use `pitch_estrategico_cidade`. Combine, se útil, com `dados_cidade` (IBGE).
  → Foque em: frase de abertura + 3 temas que ele DEVE tocar + o que evitar.

• *"Dados de X", "população de Y", "PIB de Z"*:
  → Use `dados_cidade`. Mostre população, PIB per capita, IDHM, prefeito atual.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 OPERAÇÃO DE CAMPO (cabos eleitorais, lideranças)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• *"Quem é o cara mais importante em X?", "operador top em Y", "com quem falar em Z?"*:
  → Use `operador_prioritario_cidade`. Apresente os top 3 com função, score e
    telefone mascarado.

• *"Manda pro Carlos da Itaúna...", "diz pro José que...", "avisa o vereador X..."*:
  → ATENÇÃO CRÍTICA: ANTES de invocar `enviar_mensagem_operador`, peça
    confirmação ao Deputado mostrando:
       1) Quem é o destinatário identificado (nome, função, cidade)
       2) O texto exato que será enviado
    Aguarde resposta "confirma", "manda", "pode mandar" ou similar.
    SÓ ENTÃO chame a ferramenta. Se houver ambiguidade no nome, peça que
    ele escolha qual operador antes de continuar.

• *"O que tá rolando em X cidade?", "panorama de Y", "como tá o sentimento em Z"*:
  → Use `pesquisar_cidade`. Traz o último resumo Radar dessa cidade (mídia +
    redes + temas). Se a pesquisa estiver muito antiga (>30 dias), avise que
    o Radar pode ser atualizado pela aba do painel.

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
                "Aceita nome completo ou parcial (case-insensitive). "
                "NÃO use para encontrar prefeitos/vereadores/lideranças locais — para isso use buscar_operador_campo."
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
            "name": "buscar_operador_campo",
            "description": (
                "Busca operadores de campo cadastrados no painel: prefeitos, vereadores, secretários, "
                "lideranças comunitárias, cabos eleitorais, voluntários, influenciadores. "
                "Use sempre que o Deputado perguntar 'quem é a liderança em X', 'qual o prefeito de X', "
                "'temos alguém em X cidade/região', 'me liste os operadores em X'. "
                "Aceita combinação de filtros — todos opcionais. Sem filtros, retorna os operadores de maior score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome ou parte do nome do operador. Ex.: 'Eduardo'."},
                    "cidade": {"type": "string", "description": "Cidade-base do operador. Ex.: 'Governador Valadares'."},
                    "regiao": {"type": "string", "description": "Região do operador. Ex.: 'Vale do Rio Doce'."},
                    "funcao_chave": {
                        "type": "string",
                        "description": "Função no município. Valores aceitos: 'prefeito', 'vice-prefeito', 'vereador', 'secretario', 'lideranca-comunitaria', 'cabo-eleitoral', 'influenciador', 'voluntario'.",
                    },
                    "apenas_ativos": {"type": "boolean", "description": "Se true (padrão), filtra status='ativo'.", "default": True},
                    "limit": {"type": "integer", "description": "Máximo de operadores retornados (padrão 10, max 30).", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_mensagem_operador",
            "description": (
                "Envia mensagem de WhatsApp para um operador de campo cadastrado em operadores_campo "
                "(prefeitos, vereadores, lideranças, voluntários etc). "
                "Use quando o Deputado disser 'manda whatsapp pro X', 'avisa o Y no zap', 'fala com o prefeito de Z'. "
                "O destinatário PRECISA estar cadastrado no painel — bot não envia para número solto. "
                "Sempre confirme antes ao Deputado o que vai enviar quando o pedido for ambíguo. "
                "Mensagens enviadas ficam registradas em operacao_local_mensagens para auditoria."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operador_id": {"type": "integer", "description": "ID do operador (preferencial se já obtido via buscar_operador_campo)."},
                    "nome": {"type": "string", "description": "Nome (ou parte) do operador. Use se não tiver o ID. Ex.: 'Eduardo'."},
                    "cidade": {"type": "string", "description": "Cidade-base para desambiguar quando o nome for comum. Ex.: 'Governador Valadares'."},
                    "mensagem": {"type": "string", "description": "Texto da mensagem em português, tom institucional e direto. SEM cumprimentos como 'Olá Marcos aqui' — o destinatário recebe como se fosse do gabinete."},
                },
                "required": ["mensagem"],
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
    # =========================================================================
    # COMMIT 1 — Vídeos & Podcasts via Marcos
    # =========================================================================
    {
        "type": "function",
        "function": {
            "name": "analisar_video_url",
            "description": (
                "Enfileira a análise estratégica de um vídeo ou podcast (YouTube, "
                "Spotify, Apple Podcasts). Use quando o Deputado mandar uma URL e "
                "pedir resumo, análise, munição, ou rebater conteúdo. O processamento "
                "leva 2-4 minutos — avise isso. Depois use `consultar_video_analise` "
                "para buscar o resultado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa do vídeo (https://...)."},
                    "tipo": {
                        "type": "string",
                        "enum": ["adversario", "proprio"],
                        "description": "'adversario' para extrair munição contra opositor; 'proprio' para auditoria do candidato.",
                    },
                    "candidato": {"type": "string", "description": "Nome do CANDIDATO da campanha (não o entrevistado). Se omitido, usa o configurado."},
                    "contexto_extra": {"type": "string", "description": "Contexto opcional (programa, data, foco esperado)."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_video_analise",
            "description": (
                "Consulta o resultado de uma análise de vídeo já enfileirada. "
                "Use quando o Deputado perguntar 'já ficou pronto?', pedir resumo, "
                "tweet, story, contra-argumento ou pontos de atenção sobre um vídeo. "
                "Se omitir id e url, retorna o último vídeo analisado pelo Deputado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID da análise (se conhecido)."},
                    "url": {"type": "string", "description": "URL do vídeo (alternativa ao id)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_videos_analisados",
            "description": (
                "Lista análises de vídeo já feitas, com filtros opcionais. "
                "Use para 'lista os vídeos do Caporezzo', 'o que analisamos essa semana', "
                "'mostra as análises pendentes'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "candidato": {"type": "string", "description": "Filtra pelo candidato da campanha."},
                    "tipo": {"type": "string", "enum": ["adversario", "proprio"]},
                    "periodo": {"type": "string", "enum": ["hoje", "7d", "30d"], "description": "Janela de tempo."},
                    "limit": {"type": "integer", "default": 10, "description": "Máximo de itens (max 20)."},
                },
            },
        },
    },
    # =========================================================================
    # COMMIT 2 — Inteligência semanal e cidade
    # =========================================================================
    {
        "type": "function",
        "function": {
            "name": "briefing_radar_completo",
            "description": (
                "Briefing executivo rico cruzando imprensa + redes sociais. "
                "Use quando o Deputado pedir 'briefing agora', 'panorama da semana', "
                "'o que tá pegando nas redes', 'como tá meu cenário'. Mais profundo "
                "que pulso_ia — tem temas quentes, evidências, recomendações."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "politico": {"type": "string", "description": "Nome do candidato (default = configurado)."},
                    "instagram": {"type": "string", "description": "Handle do Instagram do candidato (sem @)."},
                    "adversarios": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de adversários a monitorar.",
                    },
                    "periodo": {"type": "string", "default": "7d", "description": "Janela: 7d, 14d, 30d."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prioridades_semana",
            "description": (
                "Ranking de cidades prioritárias para o Deputado essa semana. "
                "Combina base eleitoral, feedbacks negativos, Radar local e "
                "movimentos de campo. Use para 'qual cidade visitar?', "
                "'onde tá pegando fogo?', 'prioridade da semana'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 3, "description": "Máximo de cidades (default 3, max 10)."},
                    "nivel_minimo": {
                        "type": "string",
                        "enum": ["alta", "media", "monitorar"],
                        "description": "Filtra por nível mínimo de prioridade.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pitch_estrategico_cidade",
            "description": (
                "Gera pitch personalizado para o Deputado visitar uma cidade. "
                "Combina dados socioeconômicos + feedbacks + Radar local. "
                "Use para 'vou em X amanhã, me dá um pitch', 'discurso pra evento em Y', "
                "'o que falar em Z'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade (ex.: 'Montes Claros')."},
                },
                "required": ["cidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dados_cidade",
            "description": (
                "Retorna dados socioeconômicos do IBGE (população, PIB per capita, "
                "IDHM, área, densidade, prefeito) + contagem de feedbacks recentes "
                "naquela cidade. Use para 'dados de X', 'população e PIB de Y', "
                "'qual o IDHM de Z'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade (estado MG por padrão)."},
                },
                "required": ["cidade"],
            },
        },
    },
    # =========================================================================
    # COMMIT 3 — Operação Local via WhatsApp
    # =========================================================================
    {
        "type": "function",
        "function": {
            "name": "operador_prioritario_cidade",
            "description": (
                "Lista operadores de campo (cabos, vereadores, lideranças) de uma "
                "cidade, ordenados por score de prioridade. Use para 'quem é o cara "
                "mais importante em X?', 'operador top de Y', 'com quem falar em Z?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade."},
                    "funcao": {
                        "type": "string",
                        "description": "Filtra por função (opcional): prefeito, vereador, lideranca-comunitaria, cabo-eleitoral, influenciador, voluntario.",
                    },
                    "limit": {"type": "integer", "default": 3, "description": "Máximo de operadores (max 10)."},
                },
                "required": ["cidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_mensagem_operador",
            "description": (
                "Envia mensagem direta via WhatsApp para um operador de campo e "
                "registra no histórico da Operação Local. Use quando o Deputado "
                "disser 'manda pro Carlos da Itaúna', 'diz pro José que vou amanhã'. "
                "ATENÇÃO: SEMPRE peça confirmação ao Deputado antes de invocar esta "
                "ferramenta — mostre o destinatário identificado e o texto exato "
                "que será enviado, e só dispare após receber 'confirma' ou similar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operador_id": {"type": "integer", "description": "ID do operador (se conhecido). Opcional."},
                    "operador_nome": {"type": "string", "description": "Nome do operador (parcial ou completo). Pelo menos um entre id e nome é obrigatório."},
                    "cidade": {"type": "string", "description": "Cidade do operador (ajuda a desambiguar nomes comuns)."},
                    "texto": {"type": "string", "description": "Texto exato que será enviado por WhatsApp. Já redigido."},
                },
                "required": ["texto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pesquisar_cidade",
            "description": (
                "Consulta a última pesquisa Radar da cidade (mídia + redes sociais + "
                "Voz do Povo). Mostra resumo executivo, temas top, sentimento, "
                "oportunidades políticas. Use para 'o que tá rolando em X?', "
                "'panorama atual de Y', 'como tá o sentimento em Z?'. "
                "Se não houver pesquisa recente, oriente o Deputado a usar a aba Radar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade."},
                },
                "required": ["cidade"],
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
            return {"encontrado": False, "nome_buscado": nome}
        if len(rows) == 1:
            return {"encontrado": True, "contato": rows[0]}
        return {"encontrado": True, "multiplos": True, "contatos": rows}
    except Exception as e:
        return {"encontrado": False, "erro": f"falha_consulta: {e}"}


# =============================================================================
# Tool: buscar_operador_campo — lookup em operadores_campo (prefeitos, vereadores, etc)
# =============================================================================
def _tool_buscar_operador_campo(args: dict) -> dict:
    from server import supabase_admin  # lazy

    if not supabase_admin:
        return {"encontrado": False, "erro": "supabase_indisponivel"}

    nome = (args.get("nome") or "").strip()
    cidade = (args.get("cidade") or "").strip()
    regiao = (args.get("regiao") or "").strip()
    funcao_chave = (args.get("funcao_chave") or "").strip().lower()
    apenas_ativos = args.get("apenas_ativos")
    apenas_ativos = True if apenas_ativos is None else bool(apenas_ativos)
    limit = max(1, min(int(args.get("limit") or 10), 30))

    try:
        query = (
            supabase_admin.table("operadores_campo")
            .select(
                "id, nome, telefone, funcao, funcao_chave, cidade_base, regiao, "
                "status, especificacao, influencia, votos_cidade, score, notas"
            )
            .order("score", desc=True)
        )
        if apenas_ativos:
            query = query.eq("status", "ativo")
        if nome:
            query = query.ilike("nome", f"%{nome}%")
        if cidade:
            query = query.ilike("cidade_base", f"%{cidade}%")
        if regiao:
            query = query.ilike("regiao", f"%{regiao}%")
        if funcao_chave:
            query = query.eq("funcao_chave", funcao_chave)
        res = query.limit(limit).execute()
        rows = res.data or []
    except Exception as e:
        return {"encontrado": False, "erro": f"falha_consulta: {e}"}

    if not rows:
        return {
            "encontrado": False,
            "filtros": {"nome": nome, "cidade": cidade, "regiao": regiao, "funcao_chave": funcao_chave},
        }

    return {
        "encontrado": True,
        "total": len(rows),
        "operadores": rows,
    }


# =============================================================================
# Tool: enviar_mensagem_operador — WhatsApp via Evolution para operadores cadastrados
# =============================================================================
def _tool_enviar_mensagem_operador(args: dict, remote_jid: str) -> dict:
    from server import supabase_admin, send_whatsapp_message, _jid_para_envio  # lazy

    operador_id = args.get("operador_id")
    nome = (args.get("nome") or "").strip()
    cidade = (args.get("cidade") or "").strip()
    mensagem = (args.get("mensagem") or "").strip()

    if not mensagem:
        return {"enviado": False, "erro": "mensagem_vazia"}
    if not (operador_id or nome):
        return {"enviado": False, "erro": "destinatario_nao_especificado"}
    if not supabase_admin:
        return {"enviado": False, "erro": "supabase_indisponivel"}

    # Localiza o operador (guardrail: só envia pra quem está cadastrado)
    try:
        query = supabase_admin.table("operadores_campo").select(
            "id, nome, telefone, jid, cidade_base, regiao, status, funcao_chave"
        )
        if operador_id:
            query = query.eq("id", operador_id)
        else:
            query = query.ilike("nome", f"%{nome}%")
            if cidade:
                query = query.ilike("cidade_base", f"%{cidade}%")
        res = query.limit(5).execute()
        rows = res.data or []
    except Exception as e:
        return {"enviado": False, "erro": f"falha_consulta: {e}"}

    if not rows:
        return {
            "enviado": False,
            "erro": "operador_nao_encontrado",
            "filtros": {"nome": nome, "cidade": cidade, "operador_id": operador_id},
        }
    if len(rows) > 1:
        return {
            "enviado": False,
            "erro": "multiplos_operadores",
            "mensagem": "Mais de um operador bate com esse filtro. Especifique a cidade ou use operador_id.",
            "candidatos": [
                {"id": r["id"], "nome": r["nome"], "cidade_base": r.get("cidade_base"), "funcao_chave": r.get("funcao_chave")}
                for r in rows
            ],
        }

    operador = rows[0]
    if operador.get("status") != "ativo":
        return {
            "enviado": False,
            "erro": "operador_inativo",
            "operador_nome": operador.get("nome"),
            "status": operador.get("status"),
        }

    destino_raw = operador.get("jid") or operador.get("telefone")
    if not destino_raw:
        return {"enviado": False, "erro": "operador_sem_telefone", "operador_nome": operador.get("nome")}

    destino_jid = _jid_para_envio(destino_raw)
    if "@" not in destino_jid:
        destino_jid = f"{destino_jid}@s.whatsapp.net"

    print(f"[gabinete] WhatsApp para operador: {operador.get('nome')} ({destino_jid[:6]}***) — '{mensagem[:50]}...'")

    try:
        send_whatsapp_message(destino_jid, mensagem)
    except Exception as e:
        return {"enviado": False, "erro": f"falha_envio: {e}"}

    # Registra em operacao_local_mensagens para auditoria (soft-fail)
    try:
        supabase_admin.table("operacao_local_mensagens").insert({
            "destinatario_jid": destino_jid,
            "destinatario_nome": operador.get("nome"),
            "cidade": operador.get("cidade_base"),
            "direcao": "enviada",
            "canal": "whatsapp",
            "texto": mensagem,
            "autor": "gabinete_digital",
        }).execute()
    except Exception as e:
        print(f"[gabinete] Falha ao registrar mensagem em operacao_local_mensagens: {e}")

    return {
        "enviado": True,
        "destinatario": operador.get("nome"),
        "cidade": operador.get("cidade_base"),
        "funcao": operador.get("funcao_chave"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
# COMMIT 1 — Tools de Vídeos & Podcasts
# =============================================================================
def _tool_analisar_video_url(args: dict, remote_jid: str) -> dict:
    """Enfileira análise de vídeo. Dispara pipeline em thread, não bloqueia."""
    import threading
    from server import (
        supabase_admin,
        validar_url_video,
        _custo_mensal_videos_usd,
        _processar_video_pipeline,
        VIDEOS_BUDGET_USD_MONTH,
    )  # lazy
    url = (args.get("url") or "").strip()
    if not url:
        return {"ok": False, "erro": "url_obrigatoria"}
    if not supabase_admin:
        return {"ok": False, "erro": "supabase_indisponivel"}

    ok, motivo = validar_url_video(url)
    if not ok:
        return {"ok": False, "erro": f"url_invalida: {motivo}"}

    tipo = (args.get("tipo") or "adversario").strip()
    if tipo not in ("adversario", "proprio"):
        tipo = "adversario"
    candidato = (args.get("candidato") or "").strip() or os.getenv("CANDIDATO_PADRAO", "Candidato")
    contexto_extra = (args.get("contexto_extra") or "").strip()[:2000] or None

    # Dedup
    try:
        existe = (
            supabase_admin.table("videos_analises")
            .select("id, status")
            .eq("url", url)
            .limit(1)
            .execute()
        )
        if existe.data:
            row = existe.data[0]
            return {
                "ok": True,
                "id": row["id"],
                "status": row["status"],
                "duplicado": True,
                "mensagem": f"Esse vídeo já está como '{row['status']}'. Use consultar_video_analise para ver o resultado.",
            }
    except Exception as e:
        print(f"[gabinete] dedup video soft-fail: {e}")

    # Cap mensal
    if VIDEOS_BUDGET_USD_MONTH > 0:
        try:
            gasto = _custo_mensal_videos_usd()
            if gasto >= VIDEOS_BUDGET_USD_MONTH:
                return {
                    "ok": False,
                    "erro": "limite_mensal_atingido",
                    "mensagem": "Limite mensal de análises atingido. Tente no próximo mês.",
                }
        except Exception as e:
            print(f"[gabinete] cap mensal soft-fail: {e}")

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
        "criado_por": f"gabinete:{remote_jid[:40]}",
    }
    try:
        res = supabase_admin.table("videos_analises").insert(payload).execute()
        criado = (res.data or [{}])[0]
        video_id = criado.get("id")
        if not video_id:
            return {"ok": False, "erro": "falha_criar_registro"}
    except Exception as e:
        return {"ok": False, "erro": f"erro_supabase: {e}"}

    threading.Thread(
        target=_processar_video_pipeline,
        args=(video_id, url),
        daemon=True,
        name=f"video-pipeline-gabinete-{video_id}",
    ).start()

    return {
        "ok": True,
        "id": video_id,
        "status": "queued",
        "duplicado": False,
        "duracao_estimada": "2 a 4 minutos",
        "mensagem": f"Análise enfileirada (id={video_id}). Me chama de novo daqui a pouco que eu te passo o resumo.",
    }


def _tool_consultar_video_analise(args: dict, remote_jid: str) -> dict:
    """Consulta resultado de análise. Por id, url ou último do gabinete."""
    from server import supabase_admin  # lazy
    if not supabase_admin:
        return {"ok": False, "erro": "supabase_indisponivel"}

    video_id = args.get("id")
    url = (args.get("url") or "").strip()

    try:
        q = supabase_admin.table("videos_analises").select("*")
        if video_id:
            q = q.eq("id", int(video_id))
        elif url:
            q = q.eq("url", url)
        else:
            # Último vídeo enfileirado por esse JID
            q = q.eq("criado_por", f"gabinete:{remote_jid[:40]}").order("criado_em", desc=True)
        res = q.limit(1).execute()
        if not res.data:
            return {"ok": False, "erro": "nao_encontrado", "mensagem": "Não achei essa análise."}
        v = res.data[0]
    except Exception as e:
        return {"ok": False, "erro": f"erro_supabase: {e}"}

    status = v.get("status")
    if status != "done":
        return {
            "ok": True,
            "id": v.get("id"),
            "status": status,
            "progresso": v.get("progresso", 0),
            "erro": v.get("erro"),
            "titulo": v.get("titulo"),
            "mensagem": f"Status atual: {status}. Tenta de novo em alguns minutos." if status != "error" else f"Deu erro: {v.get('erro')}",
        }

    resumo = v.get("resumo") or {}
    pontos = v.get("pontos_atencao") or []
    promessas = v.get("promessas") or []
    contradicoes = v.get("contradicoes") or []
    respostas = v.get("respostas_sugeridas") or []

    # Top 3 pontos com maior severidade
    pontos_ordenados = sorted(
        pontos,
        key=lambda p: int(p.get("severidade") or 0),
        reverse=True,
    )[:3]
    top_pontos = [
        {
            "timestamp": p.get("timestamp"),
            "citacao": (p.get("citacao") or "")[:300],
            "severidade": p.get("severidade"),
            "categoria": p.get("categoria"),
            "risco": (p.get("risco") or "")[:200],
        }
        for p in pontos_ordenados
    ]

    # Top 3 respostas (com tweet e story prontos)
    top_respostas = []
    for r in respostas[:3]:
        top_respostas.append({
            "tom": r.get("tom"),
            "tweet": (r.get("tweet") or "")[:280],
            "story_instagram": (r.get("story_instagram") or "")[:300],
            "contra_argumento_curto": (r.get("contra_argumento_curto") or "")[:300],
        })

    return {
        "ok": True,
        "id": v.get("id"),
        "status": "done",
        "titulo": v.get("titulo"),
        "canal": v.get("canal"),
        "duracao_minutos": round((v.get("duracao_segundos") or 0) / 60.0, 1),
        "tipo": v.get("tipo"),
        "candidato": v.get("candidato"),
        "tese_central": (resumo.get("tese_central") or "")[:500],
        "bullets": (resumo.get("bullets") or [])[:5],
        "sentimento_geral": resumo.get("sentimento_geral"),
        "tom_emocional": resumo.get("tom_emocional"),
        "top_3_pontos_atencao": top_pontos,
        "top_3_respostas_sugeridas": top_respostas,
        "total_promessas": len(promessas),
        "primeiras_promessas": [
            {"timestamp": p.get("timestamp"), "texto": (p.get("texto") or "")[:200]}
            for p in promessas[:3]
        ],
        "tem_contradicoes": len(contradicoes) > 0,
        "total_contradicoes": len(contradicoes),
        "url": v.get("url"),
    }


def _tool_listar_videos_analisados(args: dict, remote_jid: str) -> dict:
    """Lista vídeos com filtros. Resposta enxuta para WhatsApp."""
    from server import supabase_admin  # lazy
    if not supabase_admin:
        return {"ok": False, "erro": "supabase_indisponivel"}

    candidato = (args.get("candidato") or "").strip()
    tipo = (args.get("tipo") or "").strip()
    periodo = (args.get("periodo") or "").strip().lower()
    try:
        limit = min(int(args.get("limit") or 10), 20)
    except (TypeError, ValueError):
        limit = 10

    try:
        cols = "id, titulo, canal, candidato, tipo, status, duracao_segundos, criado_em, sentimento_geral"
        q = supabase_admin.table("videos_analises").select(cols)
        if candidato:
            q = q.eq("candidato", candidato)
        if tipo in ("adversario", "proprio"):
            q = q.eq("tipo", tipo)
        if periodo in ("hoje", "7d", "30d"):
            agora = datetime.now(timezone.utc)
            if periodo == "hoje":
                inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
            elif periodo == "7d":
                inicio = agora - timedelta(days=7)
            else:
                inicio = agora - timedelta(days=30)
            q = q.gte("criado_em", inicio.isoformat())
        q = q.order("criado_em", desc=True).limit(limit)
        res = q.execute()
        items = res.data or []
    except Exception as e:
        return {"ok": False, "erro": f"erro_supabase: {e}"}

    enxuto = []
    for v in items:
        enxuto.append({
            "id": v.get("id"),
            "titulo": (v.get("titulo") or "")[:120],
            "canal": v.get("canal"),
            "candidato": v.get("candidato"),
            "tipo": v.get("tipo"),
            "status": v.get("status"),
            "duracao_min": round((v.get("duracao_segundos") or 0) / 60.0, 1),
            "criado_em": v.get("criado_em"),
            "sentimento": v.get("sentimento_geral"),
        })
    return {"ok": True, "total": len(enxuto), "videos": enxuto}


# =============================================================================
# COMMIT 2 — Tools de inteligência semanal e cidade
# =============================================================================
def _tool_briefing_radar_completo(args: dict, remote_jid: str) -> dict:
    """Chama _radar_briefing_internal com defaults sensatos."""
    from server import _radar_briefing_internal  # lazy
    politico = (args.get("politico") or os.getenv("CANDIDATO_PADRAO") or "").strip()
    instagram = (args.get("instagram") or os.getenv("CANDIDATO_INSTAGRAM_PADRAO") or "").strip()
    adversarios = args.get("adversarios")
    if not adversarios:
        env_adv = os.getenv("ADVERSARIOS_PADRAO", "")
        adversarios = [a.strip() for a in env_adv.split(",") if a.strip()]
    periodo = (args.get("periodo") or "7d").strip()

    if not politico:
        return {"ok": False, "erro": "politico_nao_configurado", "mensagem": "Não tenho o nome do candidato. Configure CANDIDATO_PADRAO no .env ou passe o parâmetro."}

    try:
        data = _radar_briefing_internal(
            politico=politico,
            instagram=instagram,
            periodo=periodo,
            adversarios=adversarios,
            force_refresh=False,
        )
    except ValueError as ve:
        msg = str(ve)
        if msg == "dados_insuficientes":
            return {"ok": False, "erro": "dados_insuficientes", "mensagem": "Sem cobertura na imprensa nem comentários no Instagram para gerar briefing."}
        return {"ok": False, "erro": msg}
    except Exception as e:
        return {"ok": False, "erro": f"falha: {e}"}

    # Resposta enxuta para o GPT-4o
    meta = data.get("meta") or {}
    temas = data.get("temas_quentes") or []
    temas_enxutos = []
    for t in temas[:5]:
        temas_enxutos.append({
            "tema": t.get("tema"),
            "relevancia": t.get("relevancia"),
            "sentimento": t.get("sentimento_popular"),
            "o_que_falar": (t.get("o_que_falar") or "")[:200],
            "o_que_evitar": (t.get("o_que_evitar") or "")[:150],
        })
    return {
        "ok": True,
        "panorama": data.get("panorama"),
        "temperatura": data.get("temperatura"),
        "infiltracao_adversario": data.get("infiltracao_adversario") or {},
        "temas_quentes": temas_enxutos,
        "stats": {
            "noticias_total": meta.get("total_noticias"),
            "comentarios_total": meta.get("total_comentarios"),
            "pct_infiltracao_adversario": meta.get("pct_infiltracao"),
            "adversarios_citados": meta.get("adversarios_citados") or {},
        },
        "cached": data.get("cached", False),
    }


def _tool_prioridades_semana(args: dict, remote_jid: str) -> dict:
    """Chama _prioridades_semana_internal e devolve resposta enxuta para WhatsApp."""
    from server import _prioridades_semana_internal  # lazy
    try:
        limit_int = int(args.get("limit") or 3)
    except (TypeError, ValueError):
        limit_int = 3
    limit_int = max(1, min(limit_int, 10))

    nivel_min = (args.get("nivel_minimo") or "").lower()
    ordem_nivel = {"alta": 3, "media": 2, "monitorar": 1}

    try:
        data = _prioridades_semana_internal(limit=max(limit_int * 3, 15))
    except Exception as e:
        return {"ok": False, "erro": f"falha: {e}"}

    prioridades = data.get("prioridades") or []
    if nivel_min and nivel_min in ordem_nivel:
        minimo = ordem_nivel[nivel_min]
        prioridades = [p for p in prioridades if ordem_nivel.get(p.get("nivel"), 0) >= minimo]

    enxuto = []
    for p in prioridades[:limit_int]:
        enxuto.append({
            "cidade": p.get("cidade"),
            "regiao": p.get("regiao") or "",
            "score": p.get("score"),
            "nivel": p.get("nivel"),
            "motivos": (p.get("motivos") or [])[:3],
            "acao": p.get("acao_recomendada"),
            "feedbacks_recentes": p.get("feedbacks"),
            "urgentes": p.get("urgentes"),
            "movimentos_campo": p.get("movimentos_campo"),
        })
    return {
        "ok": True,
        "total_cidades_analisadas": (data.get("kpis") or {}).get("total_cidades", 0),
        "alta_prioridade_total": (data.get("kpis") or {}).get("alta_prioridade", 0),
        "top_prioridades": enxuto,
    }


def _tool_pitch_estrategico_cidade(args: dict, remote_jid: str) -> dict:
    """Chama _pitch_estrategico_internal e formata pra Marcos."""
    from server import _pitch_estrategico_internal  # lazy
    cidade = (args.get("cidade") or "").strip()
    if not cidade:
        return {"ok": False, "erro": "cidade_obrigatoria"}

    try:
        pitch = _pitch_estrategico_internal(cidade)
    except ValueError as ve:
        msg = str(ve)
        if msg == "openai_key_ausente":
            return {"ok": False, "erro": "openai_nao_configurado"}
        return {"ok": False, "erro": msg}
    except Exception as e:
        return {"ok": False, "erro": f"falha: {e}"}

    temas = pitch.get("temas_quentes") or []
    return {
        "ok": True,
        "cidade": cidade,
        "titulo": pitch.get("titulo"),
        "panorama": pitch.get("panorama"),
        "frase_de_abertura": pitch.get("frase_de_abertura"),
        "tom_recomendado": pitch.get("tom_recomendado"),
        "top_temas": [
            {
                "tema": t.get("tema"),
                "o_que_falar": (t.get("o_que_falar") or "")[:200],
                "cuidado": (t.get("cuidado") or "")[:150],
                "sentimento": t.get("sentimento_popular"),
            }
            for t in temas[:5]
        ],
        "dados_impacto": (pitch.get("dados_impacto") or [])[:3],
        "oportunidades": (pitch.get("oportunidades") or [])[:3],
        "riscos": (pitch.get("riscos") or [])[:3],
        "total_feedbacks": (pitch.get("meta") or {}).get("total_feedbacks", 0),
    }


def _tool_dados_cidade(args: dict, remote_jid: str) -> dict:
    """Chama _ibge_cidade_internal e enriquece com contagem de feedbacks."""
    from server import _ibge_cidade_internal, get_feedbacks  # lazy
    cidade = (args.get("cidade") or "").strip()
    if not cidade:
        return {"ok": False, "erro": "cidade_obrigatoria"}

    try:
        dados = _ibge_cidade_internal(cidade)
    except Exception as e:
        return {"ok": False, "erro": f"falha_ibge: {e}"}

    if dados is None:
        return {"ok": False, "erro": "cidade_nao_encontrada", "mensagem": f"Não achei {cidade} no IBGE."}

    # Conta feedbacks recentes (últimos 30 dias)
    try:
        feedbacks = get_feedbacks() or []
        nome_oficial = dados.get("cidade", cidade)
        nome_lower = nome_oficial.lower()
        fb_cidade = [f for f in feedbacks if (f.get("city") or "").lower() == nome_lower]
        agora = datetime.now(timezone.utc)
        recentes = []
        for f in fb_cidade:
            dt = _parse_date(f.get("created_at") or f.get("timestamp"))
            if not dt:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (agora - dt) <= timedelta(days=30):
                recentes.append(f)
        total_30d = len(recentes)
        sentimentos = [f.get("sentiment") for f in recentes if f.get("sentiment")]
        negativos = sum(1 for s in sentimentos if "Negativo" in str(s))
    except Exception as e:
        print(f"[gabinete] feedback count soft-fail: {e}")
        total_30d = None
        negativos = None

    return {
        "ok": True,
        "cidade": dados.get("cidade"),
        "estado": dados.get("estado"),
        "populacao": dados.get("populacao"),
        "populacao_ano": dados.get("populacao_ano"),
        "pib_per_capita_reais": dados.get("pib_per_capita"),
        "pib_ano": dados.get("pib_ano"),
        "idhm": dados.get("idh"),
        "idhm_ano": dados.get("idh_ano"),
        "area_km2": dados.get("area_km2"),
        "densidade_hab_km2": dados.get("densidade"),
        "prefeito_atual": dados.get("prefeito"),
        "total_feedbacks_30d": total_30d,
        "feedbacks_negativos_30d": negativos,
    }


# =============================================================================
# COMMIT 3 — Tools de Operação Local via WhatsApp
# =============================================================================
def _tool_operador_prioritario_cidade(args: dict, remote_jid: str) -> dict:
    """Lista operadores top de uma cidade por score."""
    from server import listar_operadores_campo, _normalizar_telefone_jid  # lazy
    cidade = (args.get("cidade") or "").strip()
    if not cidade:
        return {"ok": False, "erro": "cidade_obrigatoria"}

    funcao_filtro = (args.get("funcao") or "").strip().lower()
    try:
        limit = min(int(args.get("limit") or 3), 10)
    except (TypeError, ValueError):
        limit = 3

    try:
        todos = listar_operadores_campo(incluir_demo=False) or []
    except Exception as e:
        return {"ok": False, "erro": f"falha_listar: {e}"}

    cidade_lower = cidade.lower()
    candidatos = []
    for op in todos:
        op_cidade = (op.get("cidade") or "").lower()
        if not op_cidade or cidade_lower not in op_cidade:
            continue
        if funcao_filtro:
            op_funcao = (op.get("funcao_chave") or op.get("funcao") or "").lower()
            if funcao_filtro not in op_funcao:
                continue
        candidatos.append(op)

    if not candidatos:
        return {
            "ok": True,
            "cidade": cidade,
            "total": 0,
            "mensagem": f"Não encontrei operador cadastrado em {cidade}.",
            "operadores": [],
        }

    candidatos.sort(key=lambda o: int(o.get("score") or 0), reverse=True)
    enxuto = []
    for op in candidatos[:limit]:
        tel = op.get("telefone") or op.get("jid") or ""
        digitos = _normalizar_telefone_jid(tel)
        if len(digitos) >= 6:
            tel_masc = f"{digitos[:4]}***{digitos[-2:]}"
        else:
            tel_masc = "***"
        enxuto.append({
            "id": op.get("id"),
            "nome": op.get("nome"),
            "funcao": op.get("funcao_label") or op.get("funcao"),
            "cidade": op.get("cidade"),
            "score": int(op.get("score") or 0),
            "nivel_prioridade": op.get("nivel_prioridade") or op.get("nivel"),
            "telefone_mascarado": tel_masc,
            "influencia": op.get("influencia"),
        })
    return {
        "ok": True,
        "cidade": cidade,
        "total_encontrados": len(candidatos),
        "operadores": enxuto,
    }


def _tool_enviar_mensagem_operador(args: dict, remote_jid: str) -> dict:
    """Envia mensagem direta ao operador via WhatsApp. Requer confirmação prévia
    do Deputado (system prompt instrui o modelo a confirmar antes de invocar)."""
    from server import (
        listar_operadores_campo,
        send_whatsapp_message,
        salvar_mensagem_operacao,
        _jid_para_envio,
        _normalizar_telefone_jid,
        _mascarar_telefone,
    )  # lazy

    operador_id = args.get("operador_id")
    operador_nome = (args.get("operador_nome") or "").strip()
    cidade_filtro = (args.get("cidade") or "").strip()
    texto = (args.get("texto") or "").strip()

    if not texto:
        return {"ok": False, "erro": "texto_obrigatorio"}
    if not operador_id and not operador_nome:
        return {"ok": False, "erro": "identificacao_operador_obrigatoria",
                "mensagem": "Preciso de id ou nome do operador para identificar o destinatário."}

    try:
        todos = listar_operadores_campo(incluir_demo=False) or []
    except Exception as e:
        return {"ok": False, "erro": f"falha_listar: {e}"}

    # Identificação
    if operador_id:
        try:
            op_id_int = int(operador_id)
        except (TypeError, ValueError):
            return {"ok": False, "erro": "operador_id_invalido"}
        candidatos = [op for op in todos if int(op.get("id") or 0) == op_id_int]
    else:
        nome_lower = operador_nome.lower()
        candidatos = [op for op in todos if nome_lower in (op.get("nome") or "").lower()]
        if cidade_filtro:
            cidade_lower = cidade_filtro.lower()
            candidatos = [op for op in candidatos if cidade_lower in (op.get("cidade") or "").lower()]

    if not candidatos:
        return {
            "ok": False,
            "erro": "operador_nao_encontrado",
            "mensagem": f"Não achei operador com esses dados.",
        }
    if len(candidatos) > 1:
        opcoes = [
            {"id": op.get("id"), "nome": op.get("nome"), "cidade": op.get("cidade"), "funcao": op.get("funcao_label")}
            for op in candidatos[:5]
        ]
        return {
            "ok": False,
            "erro": "operador_ambiguo",
            "mensagem": f"Encontrei {len(candidatos)} operadores com esse nome. Qual deles?",
            "opcoes": opcoes,
        }

    op = candidatos[0]
    telefone_op = op.get("telefone") or op.get("jid") or ""
    jid_envio = _jid_para_envio(telefone_op)
    if not jid_envio or len(_normalizar_telefone_jid(jid_envio)) < 10:
        return {"ok": False, "erro": "telefone_invalido"}

    # Envio real
    try:
        send_whatsapp_message(jid_envio, texto)
    except Exception as e:
        return {"ok": False, "erro": f"falha_envio_whatsapp: {e}"}

    # Registro na operação local
    try:
        salvar_mensagem_operacao({
            "destinatario_jid": jid_envio,
            "destinatario_nome": op.get("nome") or "",
            "cidade": op.get("cidade") or "",
            "direcao": "enviada",
            "canal": "whatsapp",
            "texto": texto,
            "autor": f"gabinete:{remote_jid[:40]}",
            "enviada_em": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        print(f"[gabinete] envio ok mas log falhou: {e}")

    return {
        "ok": True,
        "enviado_para": op.get("nome"),
        "cidade": op.get("cidade"),
        "telefone_mascarado": _mascarar_telefone(telefone_op),
        "texto_enviado": texto[:200],
        "ts": datetime.utcnow().isoformat(),
    }


def _tool_pesquisar_cidade(args: dict, remote_jid: str) -> dict:
    """Consulta a última pesquisa do Radar MG de uma cidade (sem disparar nova
    coleta — apenas lê o que já está cacheado na base)."""
    from server import supabase_admin, get_feedbacks  # lazy
    cidade = (args.get("cidade") or "").strip()
    if not cidade:
        return {"ok": False, "erro": "cidade_obrigatoria"}
    if not supabase_admin:
        return {"ok": False, "erro": "supabase_indisponivel"}

    # Última pesquisa concluída para essa cidade
    try:
        resp = (
            supabase_admin.table("radar_cidades_pesquisas")
            .select("id, cidade, resumo_ia, sentimento_predominante, total_posts, created_at, periodo_dias")
            .ilike("cidade", cidade)
            .eq("status", "concluido")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
    except Exception as e:
        return {"ok": False, "erro": f"falha_supabase: {e}"}

    if not rows:
        return {
            "ok": False,
            "erro": "sem_pesquisa",
            "mensagem": (
                f"Ainda não há pesquisa do Radar MG para {cidade}. "
                "Sugira ao Deputado acessar a aba Radar do painel para disparar uma coleta nova."
            ),
        }

    pesquisa = rows[0]
    pesq_id = pesquisa.get("id")

    # Temas top dessa pesquisa
    temas_top = []
    try:
        temas_resp = (
            supabase_admin.table("radar_cidades_temas")
            .select("tema, categoria, mencoes, sentimento_predominante")
            .eq("pesquisa_id", pesq_id)
            .order("mencoes", desc=True)
            .limit(5)
            .execute()
        )
        temas_top = temas_resp.data or []
    except Exception as e:
        print(f"[gabinete] temas radar soft-fail: {e}")

    # Contagem rápida de feedbacks WhatsApp dessa cidade
    total_feedbacks_locais = 0
    try:
        feedbacks = get_feedbacks() or []
        cidade_lower = cidade.lower()
        total_feedbacks_locais = sum(
            1 for f in feedbacks if (f.get("city") or "").lower() == cidade_lower
        )
    except Exception as e:
        print(f"[gabinete] feedback count soft-fail: {e}")

    # Idade da pesquisa
    idade_dias = None
    created_at = pesquisa.get("created_at")
    if created_at:
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            idade_dias = (datetime.now(timezone.utc) - dt).days
        except Exception:
            pass

    return {
        "ok": True,
        "cidade": pesquisa.get("cidade") or cidade,
        "resumo_radar": (pesquisa.get("resumo_ia") or "")[:1500],
        "sentimento_predominante": pesquisa.get("sentimento_predominante"),
        "total_posts_radar": pesquisa.get("total_posts") or 0,
        "periodo_pesquisa_dias": pesquisa.get("periodo_dias"),
        "idade_pesquisa_dias": idade_dias,
        "temas_top": [
            {
                "tema": t.get("tema"),
                "categoria": t.get("categoria"),
                "mencoes": t.get("mencoes"),
                "sentimento": t.get("sentimento_predominante"),
            }
            for t in temas_top
        ],
        "total_feedbacks_voz_povo": total_feedbacks_locais,
    }


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
        if name == "buscar_operador_campo":
            return _tool_buscar_operador_campo(args)
        if name == "enviar_email":
            return _tool_enviar_email(args, remote_jid)
        if name == "enviar_mensagem_operador":
            return _tool_enviar_mensagem_operador(args, remote_jid)
        if name == "criar_tarefa":
            return _tool_criar_tarefa(args, remote_jid)
        if name == "gerar_relatorio_pdf":
            return _tool_gerar_relatorio_pdf(args, remote_jid)
        # Commit 1 — Vídeos & Podcasts
        if name == "analisar_video_url":
            return _tool_analisar_video_url(args, remote_jid)
        if name == "consultar_video_analise":
            return _tool_consultar_video_analise(args, remote_jid)
        if name == "listar_videos_analisados":
            return _tool_listar_videos_analisados(args, remote_jid)
        # Commit 2 — Inteligência semanal e cidade
        if name == "briefing_radar_completo":
            return _tool_briefing_radar_completo(args, remote_jid)
        if name == "prioridades_semana":
            return _tool_prioridades_semana(args, remote_jid)
        if name == "pitch_estrategico_cidade":
            return _tool_pitch_estrategico_cidade(args, remote_jid)
        if name == "dados_cidade":
            return _tool_dados_cidade(args, remote_jid)
        # Commit 3 — Operação Local
        if name == "operador_prioritario_cidade":
            return _tool_operador_prioritario_cidade(args, remote_jid)
        if name == "enviar_mensagem_operador":
            return _tool_enviar_mensagem_operador(args, remote_jid)
        if name == "pesquisar_cidade":
            return _tool_pesquisar_cidade(args, remote_jid)
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

    # Loop de tool calling, no máximo 8 rodadas para não custar demais.
    for rodada in range(8):
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
