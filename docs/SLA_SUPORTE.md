# Acordo de Nível de Serviço (SLA) — Node Data Política

> Este documento define os compromissos de disponibilidade, tempo de
> resposta e canais de suporte oferecidos por plano. Serve como anexo do
> contrato principal e como referência interna para a equipe de suporte
> mensurar performance.

---

## 1. Definições

- **Sistema**: a plataforma Node Data Política operada pela `[Sua empresa]`.
- **Disponibilidade**: período em que o sistema está acessível e responde
às requisições conforme o esperado.
- **Indisponibilidade**: período em que o sistema retorna erro técnico,
não responde, ou retorna dados incorretos por defeito da
infraestrutura ou software.
- **Janela de manutenção**: período pré-agendado para manutenção
programada, comunicado ao cliente com antecedência. Não conta como
indisponibilidade.
- **Severidade do incidente**: classificação do impacto, conforme item 4.
- **Tempo de resposta**: tempo entre a abertura do chamado pelo cliente
e o primeiro contato substantivo da equipe de suporte (não conta
auto-resposta).
- **Tempo de resolução**: tempo entre a abertura do chamado e a entrega
da solução definitiva ou workaround aceitável.
- **Horário comercial**: dias úteis, das 9h às 18h, fuso de Brasília
(GMT-3).
- **Horário estendido**: dias úteis das 8h às 22h, fuso de Brasília.
- **24x7**: ininterrupto, todos os dias do ano.

---

## 2. Disponibilidade do sistema

### 2.1 Compromisso de uptime

| Plano | Uptime mínimo garantido |
|---|---|
| Básico | 99,0% mensais |
| Intermediário | 99,5% mensais |
| Premium | 99,9% mensais |

### 2.2 Cálculo

Uptime mensal = (Tempo total do mês - Tempo de indisponibilidade) /
Tempo total do mês

Para um mês de 30 dias:
- 99,0% permite até **7h12min** de indisponibilidade
- 99,5% permite até **3h36min** de indisponibilidade
- 99,9% permite até **43min** de indisponibilidade

### 2.3 O que NÃO conta como indisponibilidade

- Janelas de manutenção programada com aviso de 48h ou mais
- Indisponibilidade causada por falhas em sistemas de terceiros (Supabase,
OpenAI, Evolution API, redes sociais consultadas pelo Radar) sem
infração de SLA por parte dos respectivos fornecedores
- Indisponibilidade causada por ação ou omissão do próprio cliente
(senha incorreta, ataque DDoS partindo de IPs do cliente, etc.)
- Indisponibilidade causada por força maior (catástrofe natural, ataque
em larga escala à infraestrutura nacional, etc.)
- Erros de uso do cliente (entrar URL inválida, esgotar cap mensal de
vídeos, etc.)
- Indisponibilidade do canal específico do cliente (instância Evolution
API conectada ao WhatsApp dele, se o problema for no WhatsApp)

### 2.4 Créditos por descumprimento do uptime

Se o uptime ficar abaixo do garantido, o cliente recebe crédito na
mensalidade seguinte:

| Uptime medido | Crédito sobre mensalidade do mês seguinte |
|---|---|
| Acima do garantido | Sem crédito |
| Até 1% abaixo do garantido | 5% |
| 1% a 3% abaixo do garantido | 10% |
| 3% a 5% abaixo do garantido | 20% |
| Mais de 5% abaixo do garantido | 30% |

O crédito é aplicado automaticamente. Para receber, o cliente não
precisa solicitar.

---

## 3. Janelas de manutenção

### 3.1 Manutenção programada

Atualizações de rotina (deploy de novas versões, ajustes de
infraestrutura) ocorrem em janelas pré-agendadas:

| Plano | Janela padrão |
|---|---|
| Básico | Quartas-feiras, 02h às 05h (Brasília) |
| Intermediário | Quartas-feiras, 02h às 04h (Brasília) |
| Premium | Domingos, 03h às 04h (Brasília), preferência por dias
não-eleitorais |

Aviso prévio: **48h** para Básico/Intermediário, **72h** para Premium.

### 3.2 Manutenção emergencial

Quando há vulnerabilidade crítica ou defeito grave detectado, podemos
executar manutenção emergencial fora da janela, com aviso mínimo de
30 minutos por e-mail e WhatsApp para o admin do cliente.

### 3.3 Período de defeso eleitoral

Nos 30 dias que antecedem a eleição até 7 dias após, não realizamos
manutenções não-emergenciais para clientes com candidato em disputa
ativa, salvo se requisitado pelo próprio cliente.

---

## 4. Severidade de incidentes

Toda solicitação de suporte é classificada em uma das 4 severidades:

### Severidade 1 — Crítica
- Sistema completamente indisponível
- Perda ou corrupção de dados
- Vazamento de dados pessoais ou de campanha
- Login totalmente bloqueado para todos os usuários
- Webhook do WhatsApp interrompido (campanha não recebe mensagens novas)

### Severidade 2 — Alta
- Sistema funcional mas com módulo principal inacessível (ex.: Voz do
Povo down)
- Múltiplos usuários reportando bug
- Análises de IA falhando para mais de 30% dos casos
- Lentidão extrema (carregamento > 10s)

### Severidade 3 — Média
- Bug ou inconsistência em funcionalidade secundária
- Erro intermitente que não impede uso
- Análise de IA com qualidade abaixo do esperado em casos pontuais
- Pequena lentidão (3-10s para carregar)

### Severidade 4 — Baixa
- Pedido de melhoria de funcionalidade
- Dúvida de uso
- Ajuste cosmético (cor, alinhamento, texto)
- Sugestão de nova feature

---

## 5. Tempos de resposta e resolução

### 5.1 Plano Básico

| Severidade | Resposta inicial | Resolução ou workaround |
|---|---|---|
| 1 — Crítica | 4h | 24h |
| 2 — Alta | 8h | 3 dias úteis |
| 3 — Média | 2 dias úteis | 7 dias úteis |
| 4 — Baixa | 5 dias úteis | Sem prazo formal (priorizado em roadmap) |

Atendimento em horário comercial.

### 5.2 Plano Intermediário

| Severidade | Resposta inicial | Resolução ou workaround |
|---|---|---|
| 1 — Crítica | 2h | 12h |
| 2 — Alta | 4h | 2 dias úteis |
| 3 — Média | 1 dia útil | 5 dias úteis |
| 4 — Baixa | 3 dias úteis | Sem prazo formal |

Atendimento em horário estendido.

### 5.3 Plano Premium

| Severidade | Resposta inicial | Resolução ou workaround |
|---|---|---|
| 1 — Crítica | 1h, 24x7 | 6h |
| 2 — Alta | 2h em horário estendido | 1 dia útil |
| 3 — Média | 4h em horário estendido | 3 dias úteis |
| 4 — Baixa | 1 dia útil | Priorização discutida em reunião mensal |

Atendimento 24x7 para Severidade 1.

### 5.4 Período eleitoral (30 dias antes da eleição até 7 dias depois)

Para clientes ativos no plano Intermediário e Premium, todos os tempos
de resposta são reduzidos pela metade durante o período eleitoral. Em
particular, Severidade 1 do Premium passa para resposta em até 30
minutos, 24x7.

---

## 6. Canais de suporte

### 6.1 Plano Básico

- **E-mail**: `suporte@[seudominio].com.br`
- **Base de conhecimento online** (FAQ + manuais em PDF e vídeo)
- **Formulário no painel** ("Reportar problema")

### 6.2 Plano Intermediário

Tudo do Básico, mais:
- **WhatsApp comercial** dedicado ao suporte (resposta dentro do SLA)
- **Reuniões mensais** de 30 min para revisão de uso e dúvidas

### 6.3 Plano Premium

Tudo do Intermediário, mais:
- **Gerente de conta dedicado** (atendimento personalizado)
- **Telefone direto** para Severidade 1 fora do horário
- **Reuniões quinzenais** de 30 min
- **Hotline 24x7** para Severidade 1 (número exclusivo do cliente)

---

## 7. Como abrir um chamado

### 7.1 Pelo e-mail

Enviar para `suporte@[seudominio].com.br` informando:

```
ASSUNTO: [Slug do cliente] - [Resumo do problema]

Cliente: [Nome do cliente]
Subdomínio: [pedro-rousseff.app.seudominio.com.br]
Usuário afetado: [admin / nome do operador]
Módulo: [Voz do Povo / Radar / Vídeos / etc.]
Descrição do problema:
[Descrição detalhada]

Passos para reproduzir:
1. [Ação 1]
2. [Ação 2]
3. [Resultado obtido vs. esperado]

Severidade percebida: [1 / 2 / 3 / 4]
Anexos: [prints de tela, log do navegador, etc.]
```

### 7.2 Pelo WhatsApp (Intermediário e Premium)

Mensagem inicial deve ter Severidade percebida e resumo. A equipe pede
detalhes se necessário.

### 7.3 Pelo painel ("Reportar problema")

Botão disponível em todas as páginas do sistema. Dados de contexto
(usuário logado, URL atual, navegador) são incluídos automaticamente.

### 7.4 Confirmação de abertura

Toda abertura de chamado gera uma confirmação automática com:
- Número do protocolo
- Severidade atribuída pela equipe
- Prazo estimado de resolução
- Link para acompanhamento

---

## 8. Procedimentos de escalação

Quando o tempo de resposta não é cumprido ou o cliente não está
satisfeito com o atendimento, há canais de escalação:

### Nível 1 — Suporte técnico
Atendimento padrão por equipe técnica.

### Nível 2 — Coordenação de suporte
Acionada automaticamente se o Nível 1 não cumprir o SLA, ou pelo
cliente se a resposta for insatisfatória.

### Nível 3 — Direção técnica
Acionada para casos críticos não resolvidos pelo Nível 2 em até 12h.

### Nível 4 — Direção comercial
Para casos comerciais (cobrança, contrato, escopo). Cliente pode
acionar diretamente em `[direcao-comercial@seudominio.com.br]`.

---

## 9. Relatórios e métricas

### 9.1 Mensal (todos os planos)

Enviado todo dia 10 do mês para o admin do cliente:
- Uptime do mês anterior
- Número de chamados abertos por severidade
- Tempo médio de resposta e resolução
- Status de pendências em aberto

### 9.2 Trimestral (Intermediário e Premium)

Reunião online de 45 min com gerente de conta:
- Revisão das métricas do trimestre
- Tendências de uso (feedbacks, vídeos analisados, etc.)
- Plano de melhoria
- Roadmap de novas funcionalidades aplicáveis ao cliente

### 9.3 Anual (Premium)

Relatório executivo em PDF + reunião presencial ou online:
- Resultado consolidado do ano
- Comparação com benchmarks da plataforma
- Sugestões estratégicas para o próximo ciclo
- Renovação contratual

---

## 10. Backups e recuperação

### 10.1 Backups automáticos

Inclusos em todos os planos, sem custo adicional:

| Tipo | Frequência | Retenção |
|---|---|---|
| Banco de dados completo | Diário | 7 dias (Básico) / 14 dias (Intermediário) / 30 dias (Premium) |
| Snapshots incrementais | A cada 6h | 24h |
| Backup off-site | Semanal | 90 dias |

### 10.2 Recuperação de dados

Em caso de perda acidental de dados pelo cliente (operador apagou
algo importante), restauração possível mediante chamado:

| Plano | RTO (tempo para restaurar) | RPO (perda máxima admitida) |
|---|---|---|
| Básico | 8h em horário comercial | 24h |
| Intermediário | 4h em horário estendido | 6h |
| Premium | 2h em 24x7 | 1h |

Após 5 restaurações por ano, restaurações adicionais têm custo
adicional.

---

## 11. Limites de uso e fair use

Mesmo em planos com limites "ilimitados", aplicam-se:

- Máximo de 500 requisições à API por minuto, por cliente
- Máximo de 10.000 mensagens recebidas por dia no WhatsApp por cliente
- Máximo de 200 análises de vídeo por mês no plano Premium (cap
ajustável mediante negociação)
- Máximo de 50 GB de tráfego por mês por cliente

Picos pontuais (acima do normal mas dentro de uso legítimo) são
acomodados sem cobrança. Uso abusivo ou indício de ataque resulta em
limitação temporária com aviso ao cliente.

---

## 12. Suporte fora do escopo (cobrado à parte)

Os itens abaixo NÃO estão cobertos pelo SLA padrão e, se solicitados,
são orçados separadamente:

- Treinamento adicional (acima do incluso na implantação)
- Migração de dados de sistemas legados (acima do limite de 30 dias)
- Customizações de funcionalidade
- Desenvolvimento de novas integrações específicas do cliente
- Consultoria estratégica de campanha
- Operação do sistema em nome do cliente (data entry, gestão de
operadores, etc.)
- Suporte por telefone fora do horário (exceto Sev 1 do Premium)
- Atendimento presencial (deslocamento da equipe)

---

## 13. Responsabilidades do cliente

Para que o SLA seja cumprido, o cliente se compromete a:

- Manter o admin e operadores com senhas seguras e 2FA ativo
- Comunicar imediatamente a saída de funcionários (para revogação
de acesso)
- Não compartilhar credenciais entre usuários
- Reportar incidentes assim que detectados (não esperar dias)
- Manter contato de e-mail e WhatsApp do admin sempre atualizado
- Responder em até 24h às solicitações de informação durante
investigação de chamados (caso contrário o tempo de resolução pode
ser estendido)
- Não realizar operações que comprometam o sistema (ataques, uso
abusivo, automações não autorizadas)

---

## 14. Quando o SLA NÃO é aplicável

O SLA fica suspenso nas seguintes situações:

- Cliente em inadimplência por mais de 15 dias
- Cliente em violação dos Termos de Uso
- Uso do sistema para finalidades ilegais
- Cliente recusando-se a aplicar atualizações de segurança críticas
solicitadas pela equipe técnica

Nessas situações, o atendimento continua mas sem garantia de tempos.

---

## 15. Revisão deste SLA

Este SLA é revisado anualmente. Alterações são comunicadas ao cliente
com 30 dias de antecedência. Cliente que discordar das mudanças pode
rescindir o contrato sem multa, mediante aviso de 30 dias.

---

## 16. Tabela-resumo de SLA por plano

| Item | Básico | Intermediário | Premium |
|---|:---:|:---:|:---:|
| Uptime garantido | 99,0% | 99,5% | 99,9% |
| Resposta Sev 1 | 4h, comercial | 2h, estendido | 1h, 24x7 |
| Resolução Sev 1 | 24h | 12h | 6h |
| Resposta Sev 2 | 8h | 4h | 2h |
| Resposta Sev 3 | 2 dias úteis | 1 dia útil | 4h |
| Canal e-mail | ✓ | ✓ | ✓ |
| Canal WhatsApp | — | ✓ | ✓ |
| Telefone Sev 1 | — | — | ✓ |
| Gerente de conta | — | — | ✓ |
| Reuniões periódicas | — | Mensal 30 min | Quinzenal 30 min |
| Retenção de backup | 7 dias | 14 dias | 30 dias |
| RTO (recuperação) | 8h | 4h | 2h |
| Relatório mensal | ✓ | ✓ | ✓ |
| Reunião trimestral | — | ✓ | ✓ |
| Reunião anual | — | — | ✓ |

---

## 17. Contato para questões sobre este SLA

`[E-mail comercial]`
`[Telefone comercial]`
`[Pessoa responsável pelo SLA]`

Este documento é parte integrante do Contrato de Prestação de Serviços
firmado entre as partes.
