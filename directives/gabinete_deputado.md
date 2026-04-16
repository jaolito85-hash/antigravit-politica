# Directive — Gabinete Digital (Assistente WhatsApp do Deputado)

## Objetivo
Oferecer ao Deputado, pelo WhatsApp, um *chefe de gabinete digital* que consulta o Node Data Política em tempo real e devolve respostas executivas sobre sentimento da população, cidades, regiões e bases eleitorais. Inclui envio de relatórios em PDF sob demanda.

## Escopo
- Canal: Evolution API (mesma instância do fluxo "Marcos").
- Acesso: whitelist via `DEPUTADO_WHATSAPP_JID` (suporta múltiplos JIDs separados por vírgula).
- Dados: Supabase (`feedbacks`, `comentarios_politicos`), JSONs estáticos (`cidades_mg.json`, `votos_*.json`), helpers existentes em `server.py` (`get_feedbacks`, `generate_ai_pulse`).

## Arquitetura em 3 camadas

1. **Directive** (este arquivo): descreve persona, escopo e regras.
2. **Orchestration**: `gabinete_agent.handle_gabinete()` — loop OpenAI com function calling (até 5 rodadas) usando `gpt-4o` por padrão. Detecta tool calls, executa e devolve resposta final ao WhatsApp.
3. **Execution**: funções `_tool_*` em `gabinete_agent.py` + `send_whatsapp_message` / `send_whatsapp_document` em `server.py`.

## Roteamento no webhook
`server.py :: /webhook` ⇒ antes das regras de spam/threading para cidadão, verifica `is_deputado(remote_jid)`. Se for o deputado, delega a `handle_gabinete(text, remote_jid)` e retorna 200.

## Ferramentas expostas ao modelo
| Ferramenta | Quando usar |
|---|---|
| `consultar_feedback_whatsapp` | Demandas, reclamações ou elogios de cidadãos. Filtros: cidade, região, categoria, sentimento, período. |
| `consultar_comentarios_instagram` | Termômetro de redes sociais (sentimento/categoria por período). |
| `top_elogios_e_problemas` | Top 3 categorias positivas e negativas consolidadas. |
| `pulso_ia` | Resumo de 2 frases do cenário político atual (cacheado em `generate_ai_pulse`). |
| `historico_eleitoral` | Votação por cidade nas regiões Jequitinhonha, Mucuri e Vale do Rio Doce. |
| `listar_cidades_mg` | Metadata de cidades cobertas (região, redes da prefeitura, coordenadas). |
| `gerar_relatorio_pdf` | Gera PDF com `reportlab` e envia como anexo via `sendMedia`. Conteúdo deve vir de dados já obtidos por outras tools. |

## Regras que valem sempre
- **LGPD**: `_mask_sensitive()` aplica máscara em telefone e nome antes de enviar dados ao modelo.
- **Zero invenção**: o system prompt proíbe citar números/cidades/sentimentos sem consultar tool.
- **Formatação WhatsApp nativa**: `*negrito*` (asterisco simples), `_itálico_`, `~tachado~`, bullets com `•` ou `–`, emojis contextuais com moderação. NUNCA markdown padrão (`**`, `##`, `---`).
- **Persona**: sempre "Deputado" (nunca primeiro nome nem "você" solto), nunca revelar que é IA, nunca dar opinião partidária própria.
- **Limite de rodadas**: `handle_gabinete` para em 5 iterações de tool calling para proteger custo.
- **Timeouts**: `sendText` 10s, `sendMedia` 60s, conforme CLAUDE.md.

## Variáveis de ambiente
- `DEPUTADO_WHATSAPP_JID` — obrigatória. Sem isso nenhuma mensagem é roteada ao gabinete.
  - Valor `*` (ou `ALL`) ativa o **MODO DEMO**: qualquer remetente que mandar mensagem para a instância é tratado como o deputado. Útil para apresentações onde o convidado vai testar com o próprio celular.
  - Em produção, trocar pelo JID real do deputado (ex.: `5531999999999@s.whatsapp.net`).
- `GABINETE_MODEL` — opcional. Padrão `gpt-4o`. Pode trocar por `gpt-4o-mini` se custo importar mais que qualidade.
- Reaproveita: `OPENAI_API_KEY`, `EVOLUTION_API_*`, `SUPABASE_*`.

## Verificação manual (demo)
1. Defina `DEPUTADO_WHATSAPP_JID` no Coolify com o JID do número de demo.
2. `pip install reportlab>=4.0` (ou rebuild do container).
3. Envie pelo WhatsApp do deputado:
   - "Me dá um resumo geral do estado." → deve chamar `pulso_ia`.
   - "Quais as 3 maiores preocupações em Teófilo Otoni?" → `consultar_feedback_whatsapp` filtrando cidade.
   - "Como estou no Vale do Rio Doce?" → `historico_eleitoral`.
   - "Me manda isso em PDF." → `gerar_relatorio_pdf` + anexo.
4. Confirme no app que `*negrito*` renderiza negrito de verdade (se aparecer literal, revisar prompt).

## Fora do escopo (próxima iteração)
- Agendamento de envio proativo (push matinal com briefing).
- Comandos estruturados (ex.: `/relatorio cidade=X`).
- Multi-deputados com isolamento por tenant.
- Áudio de entrada no canal do gabinete (hoje só texto é tratado).
