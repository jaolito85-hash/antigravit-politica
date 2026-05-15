# Manual do Usuário — Node Data Política

> Guia prático para o usuário final do sistema (admin, coordenador,
> operadores). Cobre desde o primeiro login até as funcionalidades
> avançadas, com passo a passo de cada operação comum.
>
> Esse documento deve ser entregue ao cliente em PDF + complementado
> com vídeo-tutorial de 15 minutos. Substituir os campos `[ ]` por dados
> específicos do cliente antes da entrega.

---

## 1. Primeiros passos

### 1.1 O que você recebeu

Junto com este manual, você recebeu:
- URL de acesso ao painel: `https://[seu-slug].app.[dominio].com.br`
- Usuário e senha temporária do admin, enviados pelo cofre compartilhado
- Vídeo-tutorial de 15 minutos
- Contato de suporte

### 1.2 Primeiro login

1. Abra a URL do painel no navegador (Chrome, Firefox ou Edge,
recomendados na versão mais atual)
2. Insira usuário e senha temporária recebidos
3. Você será solicitado a trocar a senha — escolha uma senha forte
(mínimo 12 caracteres, com letras, números e símbolos)
4. Será exibida a tela de configuração do 2FA (autenticação em dois
fatores)

### 1.3 Configurando o 2FA

O 2FA é **obrigatório** para o usuário admin. Para configurar:

1. Instale um aplicativo autenticador no celular:
   - **Recomendados**: Google Authenticator, Microsoft Authenticator,
   1Password, Authy
2. No painel, escaneie o QR Code exibido
3. Digite o código de 6 dígitos que o aplicativo gerou
4. Salve o código de recuperação em local seguro (se perder o celular,
esse código permite acesso)

A partir do próximo login, será exigido o código do aplicativo a cada
acesso.

### 1.4 Criando os usuários operadores

Como admin, você pode criar contas para sua equipe:

1. Acesse o menu lateral → **Configurações** → **Usuários**
2. Clique em **Adicionar usuário**
3. Preencha:
   - Nome completo
   - Usuário (sugestão: `nome-sobrenome` em minúsculas)
   - Função: `operador` (padrão), `coordenador` ou `admin`
4. O sistema gera uma senha temporária — copie e envie pelo canal
seguro ao novo usuário
5. O usuário será forçado a trocar a senha no primeiro acesso

**Importante**: nunca compartilhe credenciais entre pessoas. Cada
operador deve ter o próprio login para garantir rastreabilidade.

---

## 2. Visão geral do painel

### 2.1 Estrutura

O painel é organizado em **menu lateral** com as seguintes áreas:

- **Painel** (dashboard inicial)
- **Prioridades**
- **Operação Local**
- **Voz do Povo** (feedbacks WhatsApp)
- **Radar** (monitoramento de redes)
- **Mapa Eleitoral**
- **Simulador de Conquista**
- **Tarefas do Gabinete**
- **Vídeos & Podcasts** (planos Premium)

E no canto superior direito:
- Nome do usuário logado
- Opção de **Sair**

### 2.2 No celular

A mesma interface, com menu acessado pelo ícone de três linhas (≡) no
canto superior esquerdo. Funciona em qualquer smartphone moderno.

### 2.3 Tema dark

O painel usa tema escuro (preto + dourado) por padrão. Não há opção
de tema claro no momento.

---

## 3. Voz do Povo — atendimento ao cidadão

### 3.1 O que é

Centraliza todas as mensagens que chegam no WhatsApp da campanha,
classificadas automaticamente por IA.

### 3.2 Como cada feedback chega

1. Cidadão envia mensagem para o número do WhatsApp da campanha
2. O sistema recebe a mensagem
3. Em até 30 segundos, a IA classifica e o feedback aparece no painel
4. Se for áudio, é transcrito automaticamente

### 3.3 O que aparece em cada card

- Nome do cidadão (como aparece no WhatsApp)
- Número (parcialmente mascarado)
- Mensagem completa
- **Classificações automáticas**:
  - Categoria (saúde, educação, etc.)
  - Sentimento (positivo/neutro/negativo)
  - Urgência (alta/média/baixa)
  - Bairro/município (quando identificável)
- **Status**: aberto, em andamento, concluído
- Data e hora da mensagem
- Sugestão de resposta gerada pela IA

### 3.4 Como atender um feedback

1. Acesse **Voz do Povo**
2. Use os filtros para escolher os feedbacks (por status, urgência,
categoria, região)
3. Clique no card para abrir os detalhes
4. Leia a mensagem completa
5. Tome uma das ações:
   - **Responder** pelo WhatsApp pessoal (copiando a sugestão da IA
   ou escrevendo do zero)
   - **Marcar como em andamento** (quando vai providenciar algo)
   - **Marcar como concluído** (quando o caso está resolvido)
   - **Adicionar anotação interna** (visível só para a equipe)
6. Se a classificação automática estiver errada, corrija manualmente

### 3.5 Quando o mesmo cidadão manda várias mensagens

O sistema identifica automaticamente e agrupa em uma única thread
(conversa). Você vê o histórico completo daquele cidadão em um lugar
só.

### 3.6 Dica de uso

Sugerido rotina diária:
- **8h**: revisar feedbacks da noite anterior, marcar os urgentes
- **12h**: revisão do meio-dia, distribuir tarefas
- **18h**: fechamento do dia, marcar concluídos

---

## 4. Painel (dashboard inicial)

### 4.1 O que mostra

- **Mapa de calor** do estado configurado, com pontos de cada
município que gerou feedback
- **Estatísticas resumidas**: total de feedbacks no período, por
categoria, por sentimento
- **Indicadores principais**: feedbacks abertos, em andamento, concluídos
- **Detalhes da cidade** pesquisada (informações do IBGE, dados de
votação)

### 4.2 Pesquisar por cidade

1. Digite o nome da cidade na barra de busca
2. O mapa centra na cidade e mostra detalhes:
   - População, PIB, IDHM (dados do IBGE)
   - Voz do Povo da cidade (resumo dos feedbacks)
   - Tá na Mídia (resumo das notícias daquela cidade)
   - Oportunidades políticas identificadas pela IA
   - Temas mais frequentes

### 4.3 Como interpretar o mapa

- **Cor mais intensa**: cidade com mais demandas registradas
- **Cor mais clara**: cidade pouco ativa
- **Sem cor**: nenhum feedback ainda daquela cidade

Use o mapa para identificar regiões prioritárias ou esquecidas.

---

## 5. Radar — monitoramento de redes sociais

### 5.1 O que é

Monitora menções ao candidato e aos adversários no Instagram, X e
YouTube. Roda automaticamente todos os dias.

### 5.2 Como configurar

1. Acesse **Radar** → **Configurações**
2. Cadastre os perfis a monitorar:
   - Perfil próprio (do candidato)
   - Perfis dos adversários
3. Defina os adversários para classificação (a IA usa isso para
identificar comentários pró/anti-adversário)
4. Salve

Limite de perfis varia conforme plano contratado.

### 5.3 Como interpretar os resultados

Cada comentário coletado é classificado:
- **Sentimento** (positivo/neutro/negativo)
- **Alinhamento**: pró-candidato, neutro, pró-adversário, anti-adversário
- **Categoria** (saúde, segurança, economia, etc.)
- **Adversário mencionado** (quando aplicável)
- **Nível de hostilidade** (de 0 a 5)

### 5.4 Gráficos e relatórios

A aba **Radar → Comentários** tem:
- Gráfico de sentimento ao longo do tempo
- Distribuição por alinhamento
- Top adversários mencionados
- Lista detalhada com filtros

### 5.5 Reclassificar histórico

Se você muda os adversários cadastrados, pode pedir para a IA
reclassificar o histórico:

1. Vá em **Radar** → **Reclassificar histórico**
2. Confirme o candidato e a lista de adversários
3. Defina o limite (quantos comentários reclassificar)
4. Clique em **Iniciar**

O processo roda em background e atualiza os dados existentes.

### 5.6 Briefing IA

Gere um resumo executivo de tudo o que está acontecendo:

1. Vá em **Radar** → **Briefing IA**
2. Escolha o período (24h, 7 dias, 30 dias)
3. Selecione o candidato e adversários
4. Clique em **Gerar Briefing**

Em poucos segundos, você tem um texto resumindo:
- Volume de menções
- Sentimento geral
- Temas mais discutidos
- Adversários mais ativos
- Pontos de alerta

---

## 6. Operação Local — gestão de cabos eleitorais

### 6.1 O que é

Centraliza todos os operadores de campo (cabos eleitorais, vereadores
aliados, lideranças comunitárias) com perfil, função, score de
prioridade e histórico.

### 6.2 Cadastrando operadores

1. Acesse **Operação Local** → **Operadores**
2. Clique em **Adicionar operador**
3. Preencha:
   - Nome completo
   - Telefone (com DDD)
   - Função (prefeito, vereador, cabo eleitoral, etc.)
   - Influência (de 1 a 10)
   - Cidade de atuação
   - Observações
4. Salve

O sistema calcula automaticamente um **score de prioridade** baseado
em função, influência e dados eleitorais da cidade.

### 6.3 Como o score funciona

Fórmula: `(influência × 10) + (peso da função × 5) + (votos da cidade ÷ 1000)`

Operadores com score mais alto aparecem primeiro nas listagens. Use
isso para focar nos mais importantes primeiro.

### 6.4 Atualizações de campo

Cada conversa importante com um operador deve virar uma "atualização
de campo":

1. Vá em **Operação Local** → **Chamados de Campo**
2. Clique em **Nova atualização**
3. Escolha o operador
4. Selecione o tema (problema na cidade, oportunidade, denúncia, etc.)
5. Descreva o ocorrido
6. Anote lideranças citadas
7. Salve

A IA gera automaticamente:
- Um **resumo** do que aconteceu
- Sugestões de **próximos passos** (cadastráveis como tarefas)

### 6.5 Operadores sem contato

A aba **Operação Local** → **Sem contato** mostra os operadores que
estão há mais de X dias sem nenhuma interação registrada. Útil para
não esquecer ninguém.

### 6.6 Mapa de prioridade

A aba **Operação Local** → **Mapa** mostra um mapa das cidades onde
há operadores cadastrados, com indicação visual do score agregado.

### 6.7 Mensagens

Cada operador tem uma área de mensagens. Você pode:
- Anotar conversas que aconteceram fora do sistema
- Enviar mensagens pelo WhatsApp diretamente (mediante integração
Evolution API)
- Acompanhar o histórico completo

---

## 7. Prioridades — agenda estratégica da semana

### 7.1 O que é

Lista gerada pela IA semanalmente, indicando as 5 a 10 ações mais
estratégicas para a campanha naquela semana, baseada em:
- Dados do Radar (o que está fervendo)
- Voz do Povo (demandas urgentes)
- Operação Local (oportunidades de cidade)

### 7.2 Como gerar

1. Acesse **Prioridades**
2. Clique em **Recalcular** para gerar uma nova versão
3. Aguarde alguns segundos

A IA combina os dados e propõe as prioridades.

### 7.3 Filtros

Você pode filtrar por:
- **Nível**: máxima, alta, média, normal
- **Limite**: quantas prioridades mostrar

### 7.4 Use semanalmente

Sugerido: na segunda-feira de manhã, o coordenador da campanha entra
na aba Prioridades, recalcula e usa como pauta da reunião semanal de
estratégia.

---

## 8. Mapa Eleitoral — histórico de votação

### 8.1 O que mostra

Histórico de votação por região (Jequitinhonha, Mucuri, Vale do Rio
Doce em MG; configurável para outros estados).

### 8.2 Como usar

1. Acesse **Mapa Eleitoral**
2. Selecione a região
3. Veja:
   - Cidades mais votadas pelo seu candidato
   - Cidades onde os adversários venceram
   - Histórico ao longo dos pleitos
   - Comparação com base eleitoral atual

### 8.3 Aplicação prática

Use esses dados para:
- Identificar feudos a manter
- Identificar regiões a conquistar
- Priorizar deslocamentos durante a campanha

---

## 9. Simulador de Conquista

### 9.1 O que é

Permite simular cenários de conquista de bairros/cidades.

### 9.2 Como usar

1. Acesse **Simulador**
2. Configure os parâmetros:
   - Meta de votos
   - Cidades-alvo
   - Investimento estimado
3. Veja a projeção
4. Compare cenários

### 9.3 Limitações

O simulador trabalha com dados históricos e suposições. Não substitui
estrategista político — é apenas uma ferramenta de apoio.

---

## 10. Tarefas do Gabinete

### 10.1 O que é

Lista centralizada de tarefas da campanha. Criadas por:
- Chefe de gabinete digital via WhatsApp (modo conversacional)
- Manualmente pelo painel
- Geradas automaticamente a partir de atualizações de campo

### 10.2 Criando tarefa manual

1. Acesse **Tarefas do Gabinete**
2. Clique em **Nova tarefa**
3. Preencha título, detalhes, responsável, prazo
4. Salve

### 10.3 Criando tarefa via WhatsApp (Premium)

O candidato (ou pessoa autorizada) pode mandar mensagem no WhatsApp
para o número do gabinete digital:

> "Cria uma tarefa pra visitar Itaúna sexta-feira de manhã. Levar o
> material novo de panfleto."

O assistente cria a tarefa automaticamente, com prazo inferido.

### 10.4 Status das tarefas

- **Aberta**: aguardando início
- **Em andamento**: alguém está executando
- **Concluída**: finalizada
- **Vencida**: prazo passou e não foi concluída

### 10.5 KPIs

No topo da aba, indicadores rápidos: abertas, em andamento, concluídas,
vencidas.

---

## 11. Vídeos & Podcasts (planos Premium)

### 11.1 O que é

Módulo de análise estratégica de conteúdo audiovisual longo
(entrevistas, podcasts, pronunciamentos).

### 11.2 Como submeter um vídeo

1. Acesse **Vídeos & Podcasts**
2. No campo URL, cole o link do YouTube, Spotify ou Apple Podcasts
3. Preencha:
   - **Candidato**: NOME DO SEU CANDIDATO (não do entrevistado)
   - **Tipo**: "Adversário" se for vídeo de oposição; "Próprio" se for
   do seu candidato (para auditoria)
   - **Contexto opcional**: informações que ajudam a IA a calibrar a
   análise (ex.: programa, data, foco esperado)
4. Clique em **Analisar**

### 11.3 Tempo de processamento

- Vídeo de 10 min: ~2 minutos
- Vídeo de 30 min: ~3 minutos
- Vídeo de 1 hora: ~4 minutos
- Vídeo de 3 horas: ~8 minutos

Você não precisa esperar. Pode fechar a aba e voltar depois.

### 11.4 O que o sistema entrega

Quando o card mudar para "Pronto", clique para abrir o modal com 6
abas:

1. **Resumo**: tese central, pontos principais, tom emocional
2. **Atenção**: gaffes, ataques, contradições com timestamps e
severidade (1 a 3)
3. **Promessas**: lista de promessas e dados verificáveis
4. **Contradições**: contradições internas do próprio vídeo
5. **Respostas**: contra-argumentos prontos, tweets, stories
6. **Transcrição**: texto completo com timestamps

### 11.5 Como usar as respostas

Para cada ponto de atenção identificado, você tem:
- **Contra-argumento curto** (para entrevista ao vivo)
- **Contra-argumento longo** (≤80 palavras)
- **Tweet** pronto (≤280 caracteres)
- **Story Instagram** pronto

Use o botão de **copiar** para colar direto na rede social.

### 11.6 Regerar respostas

Se as respostas não vieram do jeito que você queria:
1. Abra o modal do vídeo
2. Vá na aba **Respostas**
3. Clique em **Re-gerar**

Não retranscreve o vídeo — apenas refaz as respostas. Custo
adicional muito baixo.

### 11.7 Excluir uma análise (admin/coordenador)

Passe o mouse sobre o card. Aparece um ícone de lixeira no canto.
Clique e confirme. A exclusão é permanente.

### 11.8 Filtros

Use os filtros no topo:
- **Tipo**: adversários, próprios, todos
- **Status**: prontos, processando, com erro
- **Período**: hoje, 7 dias, 30 dias, todo o período

---

## 12. Rotina sugerida de uso

Para extrair o máximo do sistema:

### Diariamente (10 a 15 minutos)
- Manhã: revisar feedbacks da Voz do Povo
- Final do dia: marcar concluídos
- Verificar alertas do Radar

### Semanalmente (30 a 60 minutos)
- Segunda-feira: recalcular Prioridades
- Reunião de equipe usando as prioridades como pauta
- Revisar operadores sem contato

### Quinzenalmente (1 a 2 horas)
- Analisar 1 a 2 vídeos importantes (entrevistas, podcasts)
- Atualizar cadastro de operadores
- Revisar adversários no Radar

### Mensalmente (2 a 3 horas)
- Briefing IA do mês
- Reunião de revisão com gerente de conta (Intermediário e Premium)
- Análise de tendências do mapa de calor

---

## 13. Troubleshooting básico

### Não consigo fazer login

- Confira se digitou usuário e senha corretamente (Caps Lock)
- Se errou 5 vezes, a conta fica bloqueada por 15 min
- Use a opção "Esqueci minha senha" se tiver
- Como último recurso, peça ao admin para resetar

### O 2FA está dando código inválido

- Confira se o relógio do celular está sincronizado
- Tente abrir o aplicativo autenticador novamente
- Se persistir, use o código de recuperação que você guardou
- Em casos extremos, contate o suporte

### Não recebo feedbacks novos

- Confira se o WhatsApp da campanha está conectado (Evolution API)
- Veja se o número do WhatsApp realmente está sendo divulgado
- Em caso de bloqueio do WhatsApp, contate o suporte

### Vídeo falha ao processar

- Confira se a URL está correta e o vídeo é público
- Vídeos com restrição de idade podem falhar
- Lives ainda em andamento não funcionam
- Em caso de falha, exclua a entrada e tente novamente

### O sistema está lento

- Tente recarregar a página (F5)
- Tente em outro navegador
- Se persistir, abra um chamado no suporte

---

## 14. Quando entrar em contato com o suporte

Entre em contato sempre que:
- O sistema esteja inacessível
- Uma funcionalidade não funciona como descrito neste manual
- Você precise de ajuda para uma operação específica
- Tiver dúvida sobre LGPD ou segurança
- Quiser sugerir uma melhoria ou nova feature

Como entrar em contato:
- E-mail: `suporte@[dominio].com.br`
- WhatsApp: `[número de suporte]` (planos Intermediário e Premium)
- Botão "Reportar problema" no painel

Ao reportar, inclua:
- Seu usuário
- O que estava tentando fazer
- O que aconteceu vs. o que era esperado
- Print de tela (se possível)
- Horário aproximado

---

## 15. Boas práticas

### Para o admin
- Mantenha o 2FA ativo
- Use senha forte e única
- Revogue acesso de quem sai da equipe imediatamente
- Faça revisão mensal dos usuários cadastrados

### Para os operadores
- Não compartilhe seu login com outros
- Saia da sessão ao terminar (especialmente em computadores
compartilhados)
- Reporte qualquer comportamento estranho ao admin

### Para todos
- Não publique nada do sistema em redes sociais (prints com dados de
cidadãos, por exemplo)
- Trate os dados dos eleitores com a mesma seriedade que dados pessoais
seus
- Aja com bom senso: a tecnologia é poderosa, mas o julgamento humano
é insubstituível

---

## 16. Recursos adicionais

- **Vídeo-tutorial**: link enviado junto com este manual
- **Base de conhecimento online**: `[URL da base de conhecimento]`
- **Atualizações de funcionalidades**: nos comunicaremos por e-mail
sempre que houver novidades relevantes
- **Treinamento adicional**: disponível como add-on

---

## 17. Sobre

Plataforma desenvolvida por `[Razão social da empresa]`, CNPJ
`[número]`.

Versão deste manual: `[versão]`
Atualizado em: `[data]`

Em caso de dúvidas sobre este manual:
`[email-do-suporte]`
