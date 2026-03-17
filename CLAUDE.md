# Node Data — Política — Instruções para o Claude Code

## Sobre o Projeto

Node Data Política é uma plataforma de monitoramento político que coleta feedback de cidadãos via WhatsApp, rastreia sentimento regional e agrega comentários de Instagram e feeds RSS para análise política em Minas Gerais.

Stack: Flask (Python), Supabase, Evolution API, OpenAI, Apify, Coolify/Docker.

**Porta:** 5004

## Estrutura do Repositório

```
server.py          — App Flask principal
Dockerfile         — Container (Gunicorn, porta 5004, timeout 300s para RSS)
requirements.txt   — Dependências Python (inclui feedparser)
.env.example       — Template de variáveis de ambiente
templates/         — Dashboard (data_node.html), login.html
static/            — cidades_mg.json, votos por região (jequitinhonha, mucuri, vale_rio_doce), sw.js
execution/         — Scripts SQL, dados de cidades MG
directives/        — SOPs em Markdown
PRODUCTION_CHECKLIST.md — Regras de qualidade e segurança
```

## Arquitetura de Trabalho

Siga a arquitetura de 3 camadas descrita no `AGENTE.md` (raiz) ou nos padrões desta vertical:
1. **Directive** (o que fazer) → arquivos em `directives/`
2. **Orchestration** (decisões) → você, o agente
3. **Execution** (fazer o trabalho) → scripts em `execution/`

## Funcionalidades Principais

- Coleta de feedback político via WhatsApp
- Monitoramento de comentários no Instagram (via Apify)
- Agregação de feeds RSS de notícias políticas
- Mapeamento geográfico por municípios de Minas Gerais
- Histórico de resultados eleitorais por região (Jequitinhonha, Mucuri, Vale do Rio Doce)
- Timeout estendido (300s) para operações de scraping e RSS

## Variáveis de Ambiente Críticas

Além das padrão (SUPABASE_URL, SUPABASE_KEY, EVOLUTION_API_*), esta vertical usa:
- `SUPABASE_SERVICE_ROLE_KEY` — chave com privilégios elevados para operações backend
- `APIFY_TOKEN` — token do Apify para scraping de Instagram (tier gratuito ~5000 posts/mês)

⚠️ Garantir que `SUPABASE_SERVICE_ROLE_KEY` e `APIFY_TOKEN` estão configurados no Coolify.

## Regras de Produção

Sempre siga as regras de qualidade e segurança descritas em `PRODUCTION_CHECKLIST.md` ao:
- Analisar código existente
- Sugerir mudanças
- Criar código novo
- Revisar antes de deploy

## Regras que Valem Sempre

### Segurança
- Nunca coloque chaves, tokens ou senhas no código — sempre em `.env`
- Sempre valide a origem dos webhooks recebidos
- Dados de cidadãos são protegidos por LGPD — nunca exponha em logs
- `SUPABASE_SERVICE_ROLE_KEY` nunca deve ser exposta em logs ou frontend

### Código
- Sempre use try/except em chamadas externas (Supabase, Evolution API, OpenAI, Apify, RSS)
- Sempre configure timeout nas requisições HTTP (mínimo 10s, máximo 300s para RSS)
- Sempre valide inputs antes de processar
- Sempre adicione logs nos pontos críticos
- Sempre mascare dados pessoais nos logs (telefone, CPF)
- Retorne 200 rápido nos webhooks e processe pesado em background

### Estilo
- Python com type hints quando possível
- Docstrings em português
- Nomes de variáveis descritivos em português ou inglês
- Comentários explicando o "porquê", não o "o quê"
