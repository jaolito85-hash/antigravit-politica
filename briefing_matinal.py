"""
Briefing Matinal Automático — gera e envia o resumo das 7h.

Fluxo (uma vez por dia, 07:00 America/Sao_Paulo):
  1. coletar_noticias_do_dia() — Google News RSS público, 4 buckets:
     deputado, adversários, partido, contexto MG.
  2. analisar_com_gpt() — GPT-4o organiza, escreve resumo executivo,
     sugere 2 ações concretas e gera rascunhos de post (Twitter + Instagram).
  3. salvar_briefing() — persiste em briefings_matinais (1 registro/dia).
  4. enviar_briefing_whatsapp() — fatia em 4 mensagens e dispara via Evolution.

Configuração via env (defaults sensatos):
  DEPUTADO_NOME           — nome usado nas buscas e na voz do Marcos
  DEPUTADO_PARTIDO        — partido (PT, etc.)
  DEPUTADO_ESTADO         — estado (Minas Gerais)
  DEPUTADO_WHATSAPP_JID   — destino do briefing (já existente)
  ADVERSARIOS_PADRAO      — CSV de adversários a monitorar
  BRIEFING_MODEL          — modelo OpenAI (default gpt-4o)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from zoneinfo import ZoneInfo
    TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    TZ_BR = timezone(timedelta(hours=-3))

DEPUTADO_NOME = os.getenv("DEPUTADO_NOME", "Pedro Rousseff")
DEPUTADO_PARTIDO = os.getenv("DEPUTADO_PARTIDO", "PT")
DEPUTADO_ESTADO = os.getenv("DEPUTADO_ESTADO", "Minas Gerais")
BRIEFING_MODEL = os.getenv("BRIEFING_MODEL", "gpt-5.4-mini")

WHATSAPP_MSG_MAX = 4000  # limite ~4096 com folga


def _adversarios() -> list[str]:
    raw = os.getenv("ADVERSARIOS_PADRAO", "Nikolas Ferreira")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _queries_de_busca() -> dict[str, list[str]]:
    """Queries do Google News organizadas em 4 buckets."""
    nome = DEPUTADO_NOME
    estado = DEPUTADO_ESTADO
    partido = DEPUTADO_PARTIDO
    advs = _adversarios()
    return {
        "sobre_deputado": [
            f'"{nome}"',
            f'"deputado {nome}"',
            f'"{nome}" {partido}',
        ],
        "sobre_adversarios": [f'"{adv}"' for adv in advs],
        "sobre_partido": [
            f'"{partido}" "{estado}"',
            f'{partido} {estado}',
            'Lula PT',
        ],
        "contexto_mg": [
            f'política "{estado}"',
            'ALMG Assembleia Legislativa Minas',
            'Zema governador Minas Gerais',
        ],
    }


def coletar_noticias_do_dia(data_alvo=None) -> dict[str, list[dict]]:
    """Coleta notícias do dia alvo (default: ontem) em 4 buckets, deduplicadas por URL.

    Retorna: {bucket_key: [{titulo, resumo, url, veiculo, sentimento, data}, ...]}.
    """
    from server import _buscar_google_news  # lazy: evita ciclo de import

    if data_alvo is None:
        agora_br = datetime.now(TZ_BR)
        data_alvo = (agora_br - timedelta(days=1)).date()
    elif isinstance(data_alvo, datetime):
        data_alvo = data_alvo.date()

    data_alvo_str = data_alvo.strftime("%Y-%m-%d")
    queries = _queries_de_busca()
    resultado: dict[str, list[dict]] = {b: [] for b in queries}
    urls_globais: set[str] = set()  # dedup global (uma notícia aparece num bucket só)

    for bucket, lista_queries in queries.items():
        for q in lista_queries:
            try:
                items = _buscar_google_news(q, max_items=20)
            except Exception as e:
                print(f"[briefing] erro buscando '{q}': {e}")
                continue
            for item in items:
                if item.get("data") != data_alvo_str:
                    continue
                url = item.get("url") or item.get("link")
                if not url or url in urls_globais:
                    continue
                urls_globais.add(url)
                resultado[bucket].append({
                    "titulo": item.get("titulo", "")[:300],
                    "resumo": item.get("resumo", "")[:400],
                    "url": url,
                    "veiculo": item.get("veiculo", ""),
                    "sentimento": item.get("sentimento"),
                    "data": item.get("data"),
                })

    return resultado


PROMPT_ANALISE = """Você é o chefe de gabinete digital do deputado {nome} ({partido}/{estado}).
Analise as notícias do dia anterior e produza um briefing EXECUTIVO, denso e acionável.

REGRAS DE OURO:
1. Cite SEMPRE a fonte (veículo) e parafraseie — não invente.
2. Se nenhuma notícia bater num campo, diga "_Sem registros relevantes._" — nunca invente.
3. Tom: profissional, direto, sem bajulação. Trate por "Deputado".
4. As ações recomendadas devem ser CONCRETAS (mencionar tema, formato, prazo).
5. Os rascunhos de post devem soar como falaria um deputado experiente do {partido} em {estado}. Twitter no máximo 280 caracteres. Instagram com gancho forte na primeira linha.
6. Português brasileiro impecável.

NOTÍCIAS COLETADAS (dia {data_alvo}):
{noticias_json}

Devolva APENAS um JSON válido com este formato exato:
{{
  "data_cobertura": "{data_alvo}",
  "resumo_executivo": "2-3 frases com o panorama do dia para o deputado.",
  "fatos_do_dia": [
    {{
      "titulo": "Manchete curta",
      "explicacao": "1-2 frases parafraseando.",
      "veiculo": "Veículo",
      "url": "https://...",
      "categoria": "deputado|adversario|partido|contexto_mg"
    }}
  ],
  "sobre_deputado": {{
    "tom_geral": "positivo|negativo|neutro|misto|sem_mencoes",
    "destaques": ["bullet 1", "bullet 2"],
    "alerta": "Algo que merece atenção, ou null."
  }},
  "sobre_adversarios": [
    {{
      "nome": "Nome",
      "o_que_disse_ou_fez": "Resumo do movimento dele.",
      "como_afeta": "Como impacta o deputado.",
      "url": "https://..."
    }}
  ],
  "sobre_partido": {{
    "movimentos": ["bullet 1", "bullet 2"],
    "implicacao_estadual": "Como repercute em {estado}, ou null."
  }},
  "contexto_mg": ["bullet 1 sobre política estadual", "bullet 2"],
  "acoes_recomendadas": [
    {{
      "acao": "O que fazer.",
      "justificativa": "Por que agora.",
      "prazo": "Hoje|Esta semana|Próxima oportunidade"
    }}
  ],
  "rascunho_twitter": "Post até 280 chars, sem hashtag genérica.",
  "rascunho_instagram": "Caption longa com gancho na primeira linha, 3-5 parágrafos, sem emoji infantil. Termina com chamada à ação."
}}
"""


def analisar_com_gpt(noticias: dict[str, list[dict]], data_alvo: str) -> dict | None:
    """Chama GPT-4o pra organizar e analisar. Retorna dict estruturado ou None se falhar."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[briefing] OPENAI_API_KEY ausente")
        return None

    # Limita o volume enviado ao GPT (top 8 por bucket — qualidade > quantidade)
    noticias_resumidas = {
        bucket: items[:8] for bucket, items in noticias.items()
    }
    noticias_json = json.dumps(noticias_resumidas, ensure_ascii=False, indent=2)

    prompt = PROMPT_ANALISE.format(
        nome=DEPUTADO_NOME,
        partido=DEPUTADO_PARTIDO,
        estado=DEPUTADO_ESTADO,
        data_alvo=data_alvo,
        noticias_json=noticias_json,
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=BRIEFING_MODEL,
            messages=[
                {"role": "system", "content": "Você é um chefe de gabinete sênior. Responde sempre em JSON válido."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=2500,
        )
        content = resp.choices[0].message.content or "{}"
        analise = json.loads(content)
        analise["tokens_in"] = resp.usage.prompt_tokens
        analise["tokens_out"] = resp.usage.completion_tokens
        return analise
    except Exception as e:
        print(f"[briefing] análise GPT falhou: {e}")
        return None


def formatar_para_whatsapp(briefing: dict) -> list[str]:
    """Quebra o briefing em 4 mensagens fatiadas para o WhatsApp."""
    data_cob = briefing.get("data_cobertura", "")
    try:
        data_fmt = datetime.strptime(data_cob, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        data_fmt = data_cob

    # MENSAGEM 1 — Abertura + resumo executivo
    msg1 = (
        f"🌅 *Bom dia, Deputado.*\n"
        f"_Briefing de {data_fmt}_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 *Panorama*\n"
        f"{briefing.get('resumo_executivo', '_(sem resumo)_')}\n"
    )

    # MENSAGEM 2 — Fatos do dia + sobre você + adversários
    partes2 = []
    fatos = briefing.get("fatos_do_dia") or []
    if fatos:
        partes2.append("📊 *Fatos do dia*")
        for i, f in enumerate(fatos[:5], 1):
            tit = (f.get("titulo") or "").strip()
            exp = (f.get("explicacao") or "").strip()
            veic = f.get("veiculo") or ""
            partes2.append(f"\n*{i}.* {tit}\n_{exp}_\n📰 {veic}")
        partes2.append("")

    sd = briefing.get("sobre_deputado") or {}
    if sd.get("destaques") or sd.get("alerta"):
        partes2.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        tom = sd.get("tom_geral", "")
        partes2.append(f"\n👤 *Sobre o senhor* _(tom: {tom})_")
        for d in (sd.get("destaques") or [])[:3]:
            partes2.append(f"• {d}")
        if sd.get("alerta"):
            partes2.append(f"\n⚠️ *Atenção:* {sd['alerta']}")
        partes2.append("")

    advs = briefing.get("sobre_adversarios") or []
    if advs:
        partes2.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        partes2.append("\n🎭 *O que os adversários fizeram*")
        for a in advs[:3]:
            nome = a.get("nome", "")
            disse = a.get("o_que_disse_ou_fez", "")
            afeta = a.get("como_afeta", "")
            partes2.append(f"\n*{nome}*")
            partes2.append(f"_{disse}_")
            if afeta:
                partes2.append(f"➜ Impacto: {afeta}")

    msg2 = "\n".join(partes2).strip() or "_(Sem fatos relevantes do dia.)_"

    # MENSAGEM 3 — Partido + contexto MG + ações
    partes3 = []
    sp = briefing.get("sobre_partido") or {}
    if sp.get("movimentos"):
        partes3.append(f"🌹 *{DEPUTADO_PARTIDO} no dia*")
        for m in (sp.get("movimentos") or [])[:3]:
            partes3.append(f"• {m}")
        if sp.get("implicacao_estadual"):
            partes3.append(f"\n_Em {DEPUTADO_ESTADO}: {sp['implicacao_estadual']}_")
        partes3.append("")

    cmg = briefing.get("contexto_mg") or []
    if cmg:
        partes3.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        partes3.append(f"\n🏛️ *Contexto {DEPUTADO_ESTADO}*")
        for c in cmg[:3]:
            partes3.append(f"• {c}")
        partes3.append("")

    acoes = briefing.get("acoes_recomendadas") or []
    if acoes:
        partes3.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        partes3.append("\n✅ *Ações recomendadas*")
        for i, a in enumerate(acoes[:3], 1):
            ac = a.get("acao", "")
            por = a.get("justificativa", "")
            pz = a.get("prazo", "")
            partes3.append(f"\n*{i}.* {ac}")
            partes3.append(f"_Por quê:_ {por}")
            if pz:
                partes3.append(f"_Prazo:_ {pz}")

    msg3 = "\n".join(partes3).strip() or "_(Sem recomendações específicas hoje.)_"

    # MENSAGEM 4 — Rascunhos de post
    rt = (briefing.get("rascunho_twitter") or "").strip()
    ri = (briefing.get("rascunho_instagram") or "").strip()
    msg4 = (
        "📝 *Rascunhos para hoje*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🐦 *Twitter / X*\n"
        f"```{rt or '(sem rascunho)'}```\n\n"
        "📸 *Instagram*\n"
        f"```{ri or '(sem rascunho)'}```\n\n"
        "_Posso ajustar o tom, encurtar, ou refazer. É só pedir._"
    )

    # Garantir limite por mensagem
    todas = [msg1, msg2, msg3, msg4]
    truncadas = []
    for m in todas:
        if len(m) > WHATSAPP_MSG_MAX:
            truncadas.append(m[: WHATSAPP_MSG_MAX - 20] + "\n_(...truncado)_")
        else:
            truncadas.append(m)
    return truncadas


def salvar_briefing(data_alvo: str, briefing: dict) -> int | None:
    """Upsert por data. Retorna o id do registro ou None se falhar."""
    from server import supabase_admin  # lazy
    if not supabase_admin:
        return None
    try:
        payload = {"data": data_alvo, "conteudo": briefing}
        res = supabase_admin.table("briefings_matinais") \
            .upsert(payload, on_conflict="data") \
            .execute()
        return ((res.data or [{}])[0]).get("id")
    except Exception as e:
        print(f"[briefing] erro ao salvar: {e}")
        return None


def marcar_enviado(briefing_id: int) -> None:
    from server import supabase_admin
    if not supabase_admin or not briefing_id:
        return
    try:
        supabase_admin.table("briefings_matinais") \
            .update({"enviado_em": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", briefing_id).execute()
    except Exception as e:
        print(f"[briefing] erro ao marcar enviado: {e}")


def enviar_briefing_whatsapp(briefing: dict, jid: str) -> bool:
    """Fatia em mensagens e envia em sequência. True se ao menos a primeira saiu."""
    from server import send_whatsapp_message
    import time as _time
    mensagens = formatar_para_whatsapp(briefing)
    sucesso = False
    for i, msg in enumerate(mensagens):
        try:
            send_whatsapp_message(jid, msg)
            sucesso = True
            # Pequena pausa entre mensagens pra manter ordem no app
            if i < len(mensagens) - 1:
                _time.sleep(1.2)
        except Exception as e:
            print(f"[briefing] envio msg {i} falhou: {e}")
    return sucesso


def gerar_briefing_completo(data_alvo=None, enviar: bool = True) -> dict:
    """Orquestra o pipeline. Retorna o dict do briefing (com chave 'erro' se falhou)."""
    if data_alvo is None:
        agora_br = datetime.now(TZ_BR)
        data_alvo_date = (agora_br - timedelta(days=1)).date()
    elif isinstance(data_alvo, str):
        data_alvo_date = datetime.strptime(data_alvo, "%Y-%m-%d").date()
    else:
        data_alvo_date = data_alvo

    data_alvo_str = data_alvo_date.strftime("%Y-%m-%d")
    print(f"[briefing] iniciando para data {data_alvo_str}")

    noticias = coletar_noticias_do_dia(data_alvo_date)
    total_noticias = sum(len(v) for v in noticias.values())
    print(f"[briefing] coletadas {total_noticias} notícias "
          f"({', '.join(f'{k}={len(v)}' for k,v in noticias.items())})")

    if total_noticias == 0:
        return {"erro": "Nenhuma notícia coletada para o dia.", "data_cobertura": data_alvo_str}

    briefing = analisar_com_gpt(noticias, data_alvo_str)
    if not briefing:
        return {"erro": "Análise GPT falhou.", "data_cobertura": data_alvo_str}

    # Garante a data correta
    briefing["data_cobertura"] = data_alvo_str
    briefing["_noticias_coletadas"] = total_noticias

    briefing_id = salvar_briefing(data_alvo_str, briefing)
    if briefing_id:
        briefing["_id"] = briefing_id

    if enviar:
        jid_raw = os.getenv("DEPUTADO_WHATSAPP_JID", "")
        jids = [j.strip() for j in jid_raw.split(",") if j.strip()]
        if not jids:
            print("[briefing] DEPUTADO_WHATSAPP_JID não configurado, pulando envio")
        else:
            for jid in jids:
                if enviar_briefing_whatsapp(briefing, jid):
                    if briefing_id:
                        marcar_enviado(briefing_id)

    print(f"[briefing] concluído data={data_alvo_str} id={briefing_id}")
    return briefing
