# Provisionamento de Cliente — Opção A (Deploy Isolado)

> Este documento descreve o processo completo para entregar uma instância
> dedicada do Node Data Política para um novo cliente (candidato).
> A Opção A é a estratégia de **um Supabase e um container Coolify por
> cliente**, com isolamento total de dados e nenhuma alteração no código.

---

## 1. Visão geral do fluxo

```
Lead fechado
   |
   v
[Etapa 1] Documentação e dados                (1 dia)
[Etapa 2] Provisionamento de infraestrutura   (2 horas)
[Etapa 3] Deploy do aplicativo                (1 hora)
[Etapa 4] Configuração específica do cliente  (2 horas)
[Etapa 5] Validação técnica                   (1 hora)
[Etapa 6] Onboarding e treinamento            (4 horas)
   |
   v
Cliente em produção
```

**Tempo total**: ~2 dias úteis (sem contar tempo legal/comercial).
**Quem executa**: você (founder) ou um operador técnico treinado.

---

## 2. Pré-requisitos da sua empresa

Antes de provisionar o primeiro cliente, deixe pronto:

- [ ] Conta no Supabase com acesso à criação de projetos (plano Pro para suportar múltiplos projetos)
- [ ] VPS com Coolify instalado e funcionando (recomendado: Hetzner CX22 ou DigitalOcean Premium, ~R$ 200/mês, suporta ~20 clientes)
- [ ] Domínio próprio comprado (ex: `seudominio.com.br`)
- [ ] DNS configurado com wildcard (`*.app.seudominio.com.br`) apontando para o IP da VPS
- [ ] Conta na OpenAI com cartão cadastrado e cota mensal suficiente
- [ ] Conta no Apify (tier gratuito serve para 5 clientes pequenos)
- [ ] Conta de WhatsApp Business com Evolution API para cada cliente (ou agrupar instâncias)
- [ ] Repositório Git privado com o código do projeto (este repositório)
- [ ] Cofre de senhas (1Password, Bitwarden, KeePassXC) para guardar credenciais geradas
- [ ] Modelo de contrato LGPD pronto (ver `CONTRATO_LGPD_MODELO.md`)

---

## 3. Etapa 1 — Documentação e dados do cliente

Antes de criar qualquer recurso técnico, colete e arquive:

### 3.1 Documentação assinada
- [ ] Contrato comercial assinado (com prazo, valor, escopo)
- [ ] Termo de tratamento de dados (LGPD) assinado pelo candidato como controlador
- [ ] Procuração ou autorização para acesso ao WhatsApp da campanha

### 3.2 Dados do candidato (formulário de onboarding)
```
Nome completo do candidato:
Nome fantasia / como aparece em redes:
Partido:
Cargo pretendido:
Estado / município / região:
CPF do candidato:
CNPJ da campanha (quando houver):
Nome do responsável técnico pela campanha:
E-mail do responsável:
WhatsApp do responsável:
Adversários conhecidos (lista):
Bairros / cidades prioritárias:
Cores e identidade visual (se houver branding):
```

### 3.3 Subdomínio escolhido
- Padrão sugerido: primeiro nome + último sobrenome em minúsculas, sem acentos
  - `pedro-rousseff.app.seudominio.com.br`
  - `caporezzo.app.seudominio.com.br`
- Reserve já no DNS antes de seguir.

---

## 4. Etapa 2 — Provisionamento de infraestrutura

### 4.1 Criar projeto no Supabase

1. Acessar https://supabase.com/dashboard
2. **New project** dentro da sua organização Pro
3. Nome do projeto: `nodedata-<slug-cliente>` (ex: `nodedata-pedro-rousseff`)
4. Database password: gerar senha forte (32+ caracteres) e salvar no cofre
5. Region: `South America (São Paulo)` para reduzir latência com Brasil
6. Plano: Pro (necessário para suporte profissional e backups diários)
7. Aguardar provisionamento (2–3 minutos)

### 4.2 Coletar credenciais do Supabase

Em **Project Settings → API**:
- `SUPABASE_URL` (Project URL)
- `SUPABASE_KEY` (anon public key)
- `SUPABASE_SERVICE_KEY` (service_role secret — NUNCA expor)

Em **Project Settings → Database**:
- Connection string (para rodar migrations via psql ou pelo SQL Editor)

Salvar tudo no cofre, em uma entrada chamada `<slug-cliente> — Supabase`.

### 4.3 Rodar todas as migrations

No SQL Editor do Supabase, rodar em ordem os arquivos da pasta `execution/`:

```sql
-- Em uma única sessão de SQL Editor, ou separadas:
\i execution/seed.sql
\i execution/migration_usuarios_painel.sql
\i execution/contatos_e_tarefas.sql
\i execution/operacao_local.sql
\i execution/gabinete_memory.sql
\i execution/integracao_google.sql
\i execution/migration_alinhamento.sql
\i execution/migration_operadores_score.sql
\i execution/populate_cidades_mg.sql
\i execution/videos_analises.sql
```

> No SQL Editor do Supabase você cola o conteúdo de cada arquivo e clica
> Run. Não há suporte ao comando `\i` do psql via interface web.

### 4.4 Provisionar instância no Coolify

1. Acessar painel Coolify
2. **New Resource → Application**
3. Source: Git repository (mesmo repo do projeto, branch `main`)
4. Build pack: **Dockerfile**
5. Nome: `<slug-cliente>`
6. Subdomínio: `<slug-cliente>.app.seudominio.com.br`
7. Em **Environment Variables**, preencher tudo de uma vez (modelo abaixo)
8. **Deploy** e aguardar build (~5 minutos na primeira vez)

### 4.5 Modelo de variáveis de ambiente

```bash
# Supabase do cliente (NUNCA reutilizar entre clientes)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbG...
SUPABASE_SERVICE_KEY=eyJhbG...

# OpenAI (pode ser compartilhada, mas é melhor uma chave por cliente
# para rastrear custos no painel da OpenAI)
OPENAI_API_KEY=sk-...

# Evolution API (WhatsApp do cliente)
EVOLUTION_API_URL=https://evolution.seudominio.com.br
EVOLUTION_API_KEY=...
EVOLUTION_INSTANCE_NAME=<slug-cliente>

# Apify (pode ser compartilhada — tier gratuito)
APIFY_TOKEN=apify_api_...

# Segurança
SECRET_KEY=<gerar com: python -c "import secrets; print(secrets.token_hex(32))">
SESSION_COOKIE_SECURE=true

# Configurações específicas
DEPUTADO_WHATSAPP_JID=<jid do candidato>
GABINETE_MODEL=gpt-4o
VIDEOS_BUDGET_USD_MONTH=200
VIDEOS_TMP_DIR=/tmp/nodedata_videos

# SMTP (e-mails do gabinete, opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=campanha-<slug>@seudominio.com.br
SMTP_PASS=<app password>
SMTP_FROM_EMAIL=campanha-<slug>@seudominio.com.br
SMTP_FROM_NAME=Campanha <Nome do Candidato>

# Google Calendar (opcional, Fase 2 da operação local)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

---

## 5. Etapa 3 — Deploy do aplicativo

### 5.1 Validar build

No Coolify, acompanhe os logs do build. Deve terminar com algo como:
```
Successfully tagged <slug-cliente>:latest
Application is running on port 5004
```

### 5.2 Validar healthcheck

Acessar `https://<slug-cliente>.app.seudominio.com.br`:
- Deve abrir a tela de login do Node Data Política
- Logo do sistema deve carregar
- HTTPS deve estar funcionando (cadeado verde)

Se aparecer erro 502, esperar 1 minuto e tentar de novo (Coolify ainda subindo).

### 5.3 Validar conexão com Supabase

Acessar o container Coolify (Terminal) e rodar:
```bash
python -c "from server import supabase_admin; print(supabase_admin.table('feedbacks').select('id').limit(1).execute())"
```

Deve retornar uma lista (vazia ou com dados) sem erro de autenticação.

---

## 6. Etapa 4 — Configuração específica do cliente

### 6.1 Criar usuário admin do cliente

Pelo terminal do Coolify:
```bash
python execution/criar_usuario_painel.py \
  --username <slug-cliente>-admin \
  --role admin
```

A senha será mostrada **uma única vez** no terminal. Copiar para o cofre imediatamente e enviar pelo canal seguro acordado com o cliente.

### 6.2 Configurar 2FA para o admin

Solicitar que o cliente acesse `/setup-2fa` logo no primeiro acesso. Documentar isso no e-mail de boas-vindas.

### 6.3 Cadastrar contas dos operadores de campo

Para cada operador (cabos eleitorais, lideranças, etc.):
```bash
python execution/criar_usuario_painel.py \
  --username <nome-operador>-<slug-cliente> \
  --role operador
```

Manter planilha do cliente com usuário/senha (que ele distribui internamente).

### 6.4 Importar dados iniciais do cliente

Dependendo do escopo contratado:

- **Cidades / municípios**: o seed já vem com MG. Para outros estados, gerar SQL específico ou rodar `populate_cidades_<estado>.sql`.
- **Adversários conhecidos**: cadastrar via interface web na aba Radar → Configurações.
- **Histórico de votações** (se prometido em contrato): subir CSV via SQL Editor.
- **Mapa eleitoral regional**: ajustar arquivos `static/jequitinhonha_votos.json` etc., ou criar específicos do cliente.

### 6.5 Configurar Evolution API do cliente

1. Criar instância no Evolution API com nome `<slug-cliente>`
2. Conectar ao WhatsApp do cliente (QR code)
3. Configurar webhook apontando para `https://<slug-cliente>.app.seudominio.com.br/webhook`
4. Testar com mensagem de exemplo

### 6.6 Personalização visual (se contratada)

Se o cliente pagou pelo branding personalizado:
- Substituir logo em `static/logo.png`
- Ajustar cores no CSS de `templates/data_node.html` (variáveis `--cor-primaria` etc.)
- Salvar como branch específica do cliente (não mergear na main)

---

## 7. Etapa 5 — Validação técnica

Antes de entregar, rodar a seguinte bateria de testes na instância do cliente:

- [ ] Login com 2FA funciona
- [ ] Dashboard carrega o mapa de MG (ou estado do cliente)
- [ ] Enviar mensagem ao WhatsApp do bot e receber classificação automática
- [ ] Aba Voz do Povo lista o feedback recém-criado
- [ ] Aba Radar dispara coleta de comentários e retorna resultado
- [ ] Aba Vídeos & Podcasts processa um vídeo curto sem erro
- [ ] Aba Tarefas do Gabinete cria tarefa via assistente
- [ ] Logout encerra a sessão corretamente
- [ ] Acessar pelo celular funciona (responsividade)
- [ ] HTTPS válido (Coolify gera automaticamente via Let's Encrypt)
- [ ] Backup automático do Supabase está ativo (Pro inclui)

Anotar em ata cada item validado, com print de tela e horário.

---

## 8. Etapa 6 — Onboarding e treinamento

### 8.1 Material de entrega

Preparar pasta no Google Drive compartilhada com o cliente contendo:
- Credenciais (em formato 1Password compartilhado, NÃO em PDF)
- Manual de uso em PDF (~30 páginas, com prints de cada aba)
- Vídeo-tutorial gravado (15 minutos cobrindo os principais fluxos)
- Contato de suporte (WhatsApp + e-mail)

### 8.2 Reunião de kickoff (online, 2h)

Roteiro:
1. Demonstração ao vivo de cada aba (60 min)
2. Treinamento do admin do cliente (30 min)
3. Treinamento de até 3 operadores (20 min)
4. Plano de implantação WhatsApp do feedback (10 min)

### 8.3 Acompanhamento da primeira semana

- Dia 1: contato proativo para confirmar primeiro login
- Dia 3: revisar primeiros feedbacks classificados
- Dia 7: ajustar prompts da IA se necessário (alguns clientes preferem tom mais conservador, outros mais ofensivo)

---

## 9. Script automatizado de provisionamento

Quando você passar de 5 clientes, vale automatizar com um script. Estrutura sugerida (Bash + Supabase Management API + Coolify API):

```bash
#!/usr/bin/env bash
# provisionar.sh — uso: ./provisionar.sh pedro-rousseff "Pedro Rousseff"
set -euo pipefail

SLUG="$1"
NOME="$2"
DOMINIO="seudominio.com.br"

echo "[1/6] Criando projeto Supabase..."
PROJECT_ID=$(curl -s -X POST "https://api.supabase.com/v1/projects" \
  -H "Authorization: Bearer $SUPABASE_MGMT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"nodedata-$SLUG\", \"region\": \"sa-east-1\", \"plan\": \"pro\"}" \
  | jq -r '.id')

echo "[2/6] Aguardando provisionamento..."
sleep 90

echo "[3/6] Coletando credenciais..."
SUPABASE_URL=$(curl -s "https://api.supabase.com/v1/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $SUPABASE_MGMT_TOKEN" | jq -r '.endpoint')
# (extrair também ANON e SERVICE_ROLE)

echo "[4/6] Rodando migrations..."
for sql in execution/*.sql; do
  curl -s -X POST "$SUPABASE_URL/database/query" \
    -H "Authorization: Bearer $SUPABASE_SERVICE" \
    -d "{\"query\": $(jq -Rs . < $sql)}"
done

echo "[5/6] Criando aplicação no Coolify..."
COOLIFY_APP=$(curl -s -X POST "https://coolify.$DOMINIO/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -d "{\"name\": \"$SLUG\", \"git_repository\": \"$GIT_REPO\", \"git_branch\": \"main\", \"fqdn\": \"$SLUG.app.$DOMINIO\"}" \
  | jq -r '.uuid')

echo "[6/6] Configurando variáveis e deployando..."
# (loop setando cada env var via API do Coolify, depois trigger deploy)

echo "Pronto! Acesse https://$SLUG.app.$DOMINIO em ~5 minutos."
```

Esse script reduz o trabalho manual de ~2 horas para ~10 minutos. Vale a pena escrever em Python (mais legível e testável) quando você passar de 10 clientes.

---

## 10. Tabela de custos por cliente (referência)

| Item | Custo mensal | Observação |
|---|---|---|
| Supabase Pro | USD 25 (~R$ 125) | Por projeto isolado |
| Fatia de VPS Coolify | ~R$ 10 | VPS R$ 200 dividida por ~20 apps |
| OpenAI (Whisper + GPT-4o) | R$ 30–500 | Depende do uso de vídeos e radar |
| Evolution API (WhatsApp) | R$ 30–80 | Compartilhada entre clientes |
| Domínio e DNS | R$ 5 | Rateio anual |
| **Total infra** | **R$ 200–700** | Variável conforme uso |

**Preço sugerido ao cliente**:
- Plano básico (feedbacks + radar): R$ 800–1.500/mês
- Plano completo (com vídeos, gabinete, operação local): R$ 2.000–3.500/mês
- Implantação (one-time): R$ 3.000–6.000

**Margem média**: 60–75%, suficiente para escalar com agência pequena (2–3 pessoas).

---

## 11. Checklist final por cliente

Imprimir e marcar para cada provisionamento:

- [ ] Contrato comercial assinado em PDF arquivado
- [ ] Termo LGPD assinado em PDF arquivado
- [ ] Formulário de onboarding preenchido
- [ ] Projeto Supabase criado e migrations aplicadas
- [ ] Coolify app deployado e acessível via HTTPS
- [ ] Variáveis de ambiente preenchidas e salvas no cofre
- [ ] Usuário admin criado e 2FA configurado
- [ ] Operadores adicionais criados conforme necessário
- [ ] Evolution API conectada ao WhatsApp do cliente
- [ ] Webhook funcionando (teste com mensagem)
- [ ] Bateria de testes técnicos passou
- [ ] Reunião de kickoff agendada
- [ ] Material de entrega preparado
- [ ] Acompanhamento da primeira semana agendado
- [ ] Lançamento de NF/recibo de implantação
- [ ] Cobrança recorrente configurada (Stripe / Pagar.me)

---

## 12. Quando migrar para Opção B

Sinais de que vale parar de usar Opção A e refazer para multi-tenant compartilhado:

- Mais de 10 clientes ativos simultaneamente
- Tempo gasto com manutenção (atualizações, bugs) > 50% do seu tempo
- Custo de infra por cliente passou de 20% do preço cobrado
- Você quer oferecer trial gratuito (impossível na Opção A por custo)
- Clientes pedem features que exigem dados compartilhados (benchmarking entre campanhas, por exemplo)

Quando isso acontecer, planeje um refactor de 3–4 semanas para introduzir `tenant_id` em todas as tabelas e adaptar o login e as queries. Manter os clientes antigos da Opção A em paralelo até migração completa.
