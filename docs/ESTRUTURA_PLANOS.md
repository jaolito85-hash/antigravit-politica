# Estrutura de Planos — Node Data Política

> Este documento define os três planos comerciais oferecidos a candidatos,
> com escopo detalhado de funcionalidades, limites operacionais e add-ons.
> Os valores monetários ficam em planilha separada do comercial.

---

## 1. Filosofia da segmentação

A divisão dos planos segue **dois eixos**:

1. **Porte do cargo disputado** — quanto maior o cargo, mais dados a campanha
gera e mais sofisticação ela exige.
2. **Quantidade de operadores em campo** — quanto mais cabos eleitorais e
lideranças, mais usuários e mais carga no painel.

Os planos foram projetados para ter sobreposição mínima. Cada um atende um
arquétipo de cliente claramente diferente.

---

## 2. Plano BÁSICO — Voz do Povo

**Posicionamento**: campanha enxuta, foco em escuta da base.
**Cliente ideal**: vereador, prefeito de cidade pequena, deputado estadual
estreante, pré-candidato, mandato ativo sem campanha.
**Promessa central**: nunca mais perder uma demanda do eleitor.

### Funcionalidades incluídas

#### Coleta e atendimento ao cidadão
- WhatsApp único da campanha com bot inteligente
- Resposta automática personalizada com IA (GPT-4o)
- Classificação automática por:
  - Sentimento (positivo, neutro, negativo)
  - Categoria (saúde, educação, infraestrutura, segurança, etc.)
  - Urgência (baixa, média, alta)
  - Região / município
- Detecção de spam e mensagens off-topic
- Identificação de feedbacks duplicados do mesmo cidadão
- Histórico completo por número

#### Painel
- Dashboard com mapa de calor do estado configurado
- Listagem de feedbacks com filtros
- Status de atendimento (aberto, em andamento, concluído)
- Anotações internas por feedback
- Exportação em CSV

#### Radar básico
- Monitoramento de **1 perfil próprio** no Instagram
- Coleta automática a cada 24h
- Classificação automática de comentários

#### Mapa Eleitoral
- Visualização histórica por região (Jequitinhonha, Mucuri, Vale do Rio
Doce — para MG; outras regiões mediante implantação)

### Limites operacionais

- **1 usuário admin**
- **Até 3 operadores adicionais**
- **Até 2.000 feedbacks/mês recebidos**
- **1 perfil monitorado no Radar**
- **Armazenamento: 1 GB de dados**

### O que NÃO está incluído

- Vídeos & Podcasts (módulo de análise estratégica)
- Operação Local (gestão de cabos eleitorais)
- Tarefas do Gabinete (assistente digital)
- Pitch Estratégico e Talking Points
- Google Calendar
- Múltiplos perfis no Radar
- Análise de adversários no Radar
- Treinamento presencial

---

## 3. Plano INTERMEDIÁRIO — Operação de Campo

**Posicionamento**: campanha estruturada, operação ativa em campo.
**Cliente ideal**: prefeito de cidade média/grande, deputado estadual com
mandato, deputado federal estreante, vice-prefeito candidato a prefeito.
**Promessa central**: transforme escuta em ação coordenada com seus operadores.

### Funcionalidades incluídas

#### Tudo do Plano Básico, mais:

#### Radar avançado
- Monitoramento de **até 5 perfis** no total (próprios + adversários)
- Cobertura de Instagram, X/Twitter e YouTube
- Análise de **alinhamento** dos comentários (pró-cliente, neutro,
pró-adversário, anti-adversário)
- Identificação de adversários mencionados nos comentários
- Histórico de coletas com cache local
- Reclassificação em massa do histórico

#### Operação Local (gestão de cabos eleitorais)
- Cadastro de operadores de campo (cabos, vereadores aliados, lideranças)
- Score automático de prioridade por operador
- Função, influência, peso eleitoral por cidade
- Histórico de mensagens trocadas com cada operador
- Atualizações de campo categorizadas
- Listagem de operadores sem contato recente
- Mapeamento de prioridade por município

#### Prioridades
- Lista semanal de prioridades estratégicas, gerada por IA
- Combinação de dados do Radar + Operação Local + Feedbacks
- Sugestões de ação por nível de urgência

#### Simulador de Conquista
- Simulação de conquista de bairros / municípios
- Cálculo de viabilidade com base em histórico eleitoral
- Sugestões de prioridade

#### Briefing IA
- Resumo executivo diário do que está acontecendo
- Cache de 1 hora para reduzir custos
- Geração sob demanda

### Limites operacionais

- **1 usuário admin + 1 coordenador**
- **Até 10 operadores adicionais**
- **Até 8.000 feedbacks/mês recebidos**
- **5 perfis monitorados no Radar**
- **Armazenamento: 5 GB de dados**

### O que NÃO está incluído

- Vídeos & Podcasts (módulo de análise estratégica)
- Tarefas do Gabinete (assistente digital de WhatsApp do candidato)
- Pitch Estratégico personalizado
- Google Calendar integrado
- API para integrações externas
- Branding visual customizado
- Treinamento presencial

---

## 4. Plano PREMIUM — Inteligência de Campanha Completa

**Posicionamento**: campanha de alto investimento com necessidade
estratégica.
**Cliente ideal**: deputado federal, senador, governador, prefeito de
capital, candidato a presidente da câmara estadual.
**Promessa central**: terceirize a inteligência estratégica da sua
campanha com IA de última geração.

### Funcionalidades incluídas

#### Tudo dos planos anteriores, mais:

#### Vídeos & Podcasts
- Análise estratégica de vídeos longos (YouTube, Spotify, Apple Podcasts)
- Transcrição completa em português com timestamps
- 5 análises por vídeo via GPT-4o:
  1. Resumo executivo (tese central, bullets, tom)
  2. Pontos de atenção (gaffes, ataques, contradições com severidade)
  3. Promessas e dados verificáveis
  4. Contradições internas
  5. Respostas sugeridas (tweets, stories, contra-argumentos)
- Modo Adversário (extrair munição) ou Próprio (auditoria)
- Re-geração de respostas sem retranscrever
- Filtros por período, tipo e status
- Exclusão administrativa de análises antigas

#### Tarefas do Gabinete
- Assistente digital pessoal via WhatsApp do candidato
- Cria, atualiza e fecha tarefas via linguagem natural
- Integração com Operação Local (transforma atualização de campo em
tarefa)
- KPIs de tarefas abertas, em andamento, concluídas, vencidas
- Memória contextual entre conversas

#### Pitch Estratégico
- Pitch personalizado por cidade, baseado em:
  - Dados IBGE da cidade (população, PIB, IDHM)
  - Sentimento atual nas redes
  - Demandas mais frequentes nos feedbacks
  - Histórico eleitoral
  - Oportunidades políticas identificadas
- Talking points segmentados por tema

#### Google Calendar (Fase 2 da Operação Local)
- Conexão OAuth com agenda do candidato
- Agendamento de reuniões com operadores diretamente do painel
- Convites automáticos via WhatsApp
- Convidados padrão (chefe de gabinete, sócio, etc.)

#### Briefing IA avançado
- Geração ilimitada sob demanda
- Cache estendido para grupos de stakeholders
- Comparativo entre períodos

#### Talking Points
- Roteiros de fala personalizados por evento
- Adaptação ao público (jovens, idosos, classe trabalhadora, etc.)
- Bordões e frases-chave sugeridas

### Limites operacionais

- **1 admin + 1 coordenador + até 30 operadores**
- **Feedbacks ilimitados via WhatsApp**
- **Perfis monitorados no Radar: 10**
- **Vídeos analisados/mês: 80** (suficiente para acompanhar grandes
agendas; cap mensal pode ser ajustado mediante negociação)
- **Armazenamento: 25 GB de dados**

### Recursos exclusivos

- Branding visual personalizado (cores, logo)
- Subdomínio customizado opcional (`painel.candidato.com.br`)
- Treinamento presencial de equipe (até 8h, sede do cliente ou online)
- DPO/Encarregado terceirizado disponível como serviço opcional

---

## 5. Comparativo rápido

| Funcionalidade | Básico | Intermediário | Premium |
|---|:---:|:---:|:---:|
| Painel + Mapa de calor | ✓ | ✓ | ✓ |
| Voz do Povo (feedbacks WhatsApp) | ✓ | ✓ | ✓ |
| Radar (1 perfil) | ✓ | — | — |
| Radar (até 5 perfis) | — | ✓ | — |
| Radar (até 10 perfis) | — | — | ✓ |
| Mapa Eleitoral histórico | ✓ | ✓ | ✓ |
| Operação Local (cabos eleitorais) | — | ✓ | ✓ |
| Prioridades semanais | — | ✓ | ✓ |
| Simulador de Conquista | — | ✓ | ✓ |
| Briefing IA | — | ✓ (limitado) | ✓ (ilimitado) |
| Pitch Estratégico por cidade | — | — | ✓ |
| Talking Points | — | — | ✓ |
| Vídeos & Podcasts | — | — | ✓ |
| Tarefas do Gabinete | — | — | ✓ |
| Google Calendar integrado | — | — | ✓ |
| Branding personalizado | — | — | ✓ |
| Treinamento presencial | — | — | ✓ |
| Operadores incluídos | 3 | 10 | 30 |
| Feedbacks/mês | 2.000 | 8.000 | Ilimitado |
| Armazenamento | 1 GB | 5 GB | 25 GB |

---

## 6. Add-ons (válidos para qualquer plano)

São contratados separadamente, com cobrança avulsa ou recorrente,
conforme item.

### Add-ons recorrentes (cobrança mensal)
- Pacote adicional de **+10 operadores**
- Pacote adicional de **+25 operadores**
- Aumento de cap de **vídeos** (pacote de +20 análises/mês)
- Aumento de cap de **feedbacks** (pacote de +2.000/mês)
- **Perfis adicionais no Radar** (pacote de +5)
- **Armazenamento adicional** (pacote de +10 GB)
- **DPO terceirizado** como serviço (acompanhamento mensal de
conformidade LGPD)
- **Backup duplicado** em provedor alternativo (Google Cloud, AWS)

### Add-ons one-time (cobrança única)
- **Implantação acelerada** (entrega em 48h em vez do prazo padrão)
- **Treinamento adicional** (blocos de 4h, presencial ou online)
- **Branding completo** com identidade visual customizada (cores, logo,
favicon, fontes, footer da página)
- **Importação de base histórica** do cliente (planilhas, CRM antigo,
extratos do TSE)
- **Integração customizada** com sistema do partido (CRM, ERP, mailing)
- **Relatórios PDF customizados** (até 3 modelos exclusivos)
- **Dashboard executivo** sob medida (BI customizado)
- **Auditoria técnica trimestral** com relatório formal de segurança

---

## 7. Implantação (cobrança one-time obrigatória)

Toda contratação inclui valor de implantação separado da mensalidade.
Esse valor cobre:

- Criação do ambiente isolado (Supabase + Coolify)
- Aplicação de migrations e seed de dados regionais
- Cadastro inicial de até 10 operadores
- Conexão com WhatsApp via Evolution API
- Configuração de SMTP para e-mails do gabinete (quando aplicável)
- Treinamento online de até 4h (admin + 3 operadores)
- Geração de credenciais e entrega segura via cofre compartilhado
- Bateria de testes técnicos com relatório de validação
- Acompanhamento técnico da primeira semana de uso
- Documentação de uso (PDF) e vídeo-tutorial

### Implantação acelerada (add-on)
Entrega em **48h úteis** mediante priorização da equipe. Útil para
campanhas em momentos críticos (lançamento de candidatura, debates,
crises). Cobrado como ajuste sobre o valor de implantação padrão.

---

## 8. Política de upgrade e downgrade

### Upgrade
- Pode ser solicitado a qualquer momento
- Cobrança proporcional ao mês corrente, ajustada na próxima fatura
- Migração técnica em até 48h úteis sem interrupção do serviço
- Treinamento adicional do novo módulo incluído

### Downgrade
- Pode ser solicitado com **30 dias de antecedência**
- Ajuste na fatura do mês seguinte
- Dados de funcionalidades removidas ficam preservados por 90 dias
(em modo somente leitura) antes da eliminação definitiva
- Recomendado avaliar add-ons antes de fazer downgrade

### Pausa temporária (período entre eleições)
- Plano "Modo Mandato": preserva o ambiente com leitura restrita,
sem coleta nova
- Disponível apenas para clientes ativos há mais de 6 meses
- Tem valor reduzido em relação ao plano contratado

---

## 9. Pacotes especiais para eleições

Período eleitoral (90 dias antes da eleição) tem demanda concentrada.
Oferecer pacotes específicos:

### Pacote "Reta Final"
- Plano Premium completo
- Vigência: 90 dias antes da eleição até 30 dias depois
- Inclui implantação acelerada
- Inclui acompanhamento técnico diário (não só primeira semana)

### Pacote "Segundo Turno"
- Ativação rápida em até 24h após confirmação de segundo turno
- Plano Premium
- Vigência: 30 dias até a eleição

### Pacote "Pré-campanha"
- Plano Intermediário
- Vigência: 6 meses antes do início oficial da campanha
- Foco em estruturação da base e diagnóstico territorial

---

## 10. O que NUNCA está incluído em nenhum plano

Itens fora do escopo do produto, para evitar promessas indevidas:

- Compra ou veiculação de mídia paga (Facebook Ads, Google Ads, etc.)
- Produção de conteúdo audiovisual (vídeos, posts, criação gráfica)
- Assessoria política ou estratégica (a plataforma fornece dados,
não substitui o estrategista)
- Defesa jurídica eleitoral
- Compra de listas de e-mail, telefone ou perfis em redes sociais
- Disparo em massa que viole termos do WhatsApp ou Marco Civil
- Garantia de resultado eleitoral
- Acesso a dados protegidos por sigilo (cadastro eleitoral, base de
dados privadas, etc.)
- Operação 24h por equipe humana (apenas o sistema fica disponível 24h)

---

## 11. Política de uso justo

Mesmo nos planos com limites "ilimitados", aplicam-se regras de bom uso:

- WhatsApp do candidato não pode ser usado para spam ou disparos em
massa não autorizados pelo destinatário
- Coleta no Radar respeita os termos de serviço das redes monitoradas
e a legislação vigente
- O sistema pode ser temporariamente limitado se houver detecção de uso
abusivo (mais de 500 mensagens/hora, por exemplo) com aviso ao cliente
- Conteúdo gerado pela IA é responsabilidade final do cliente — a
plataforma não revisa nem aprova publicações

---

## 12. Como precificar (notas internas)

> Estas observações são internas e não devem aparecer em material para
> cliente.

Critérios sugeridos:

1. **Custo de infra** por cliente (Supabase Pro + fatia de VPS + OpenAI +
Evolution + Apify) é o piso. Nunca cobre abaixo de 3x esse custo.
2. **Custo de operação** (implantação + suporte primeiros 3 meses)
absorvido nos primeiros meses de mensalidade.
3. **Margem alvo**: 60% líquido após custos diretos.
4. **Disposição a pagar** varia muito por cargo: vereador interior paga
muito menos que deputado federal. Estabeleça faixas mínima e máxima
por cargo.
5. **Tabela base + desconto comercial**: anuncie sempre o preço cheio e
ofereça desconto para fechar (5%, 10%, 15% conforme caso). Sensação de
vitória do cliente é importante.
6. **Pacotes anuais**: oferece desconto agressivo (15-20%) para clientes
que pagam o ano todo antecipado. Reduz churn e melhora caixa.
7. **Inflação anual** prevista no contrato (IPCA + 2% ou IGP-M).
