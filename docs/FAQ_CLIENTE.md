# FAQ — Perguntas Frequentes do Cliente

> 30 perguntas que clientes (e prospects) costumam fazer sobre o sistema.
> Use como base de conhecimento para a equipe comercial e de suporte, e
> como ponto de partida para uma seção FAQ pública no site institucional
> ou dentro do próprio painel.

---

## A. SOBRE O SISTEMA (10 perguntas)

### 1. O que é o Node Data Política?

É uma plataforma online de inteligência de campanha desenvolvida
especificamente para candidatos e gabinetes parlamentares no Brasil.
Centraliza, em um único painel, a escuta da base via WhatsApp, o
monitoramento de redes sociais, a gestão dos operadores de campo e
a análise estratégica de conteúdos de mídia (entrevistas, podcasts,
pronunciamentos), tudo com auxílio de inteligência artificial.

### 2. Para quem o sistema serve?

Atendemos candidatos e mandatos a partir de **vereador** em cidades
médias até **governador** e **senador**. Também oferecemos o plano
"Mandato" para parlamentares que querem manter a escuta da base entre
eleições. Não atendemos candidatos a presidência (escopo muito maior
que o nosso atual estágio).

### 3. Funciona para qualquer cargo eletivo?

Sim, em qualquer cargo. O que muda é a configuração inicial (regiões
monitoradas, adversários cadastrados, perfis no Radar) e o plano
recomendado. Vereador costuma se beneficiar mais do plano Básico;
deputado, do Intermediário; senador e governador, do Premium.

### 4. Como o sistema classifica os feedbacks dos eleitores?

Cada mensagem que chega no WhatsApp da campanha é processada por
inteligência artificial (GPT-4o da OpenAI). A IA identifica:
- **Sentimento**: positivo, neutro ou negativo
- **Categoria**: saúde, educação, infraestrutura, segurança,
emprego, etc.
- **Urgência**: alta, média ou baixa
- **Município/bairro** (quando o eleitor menciona ou é inferível)
- **Spam**: mensagens off-topic são marcadas para revisão

A classificação aparece imediatamente no painel. O admin pode
revisar e corrigir a qualquer momento.

### 5. A IA funciona bem em português?

Sim. Usamos modelos calibrados para português brasileiro, incluindo
gírias, regionalismos e siglas políticas. Reconhece "TSE", "ALMG",
"PT", "MDB" sem precisar de configuração extra. Também identifica
contextos específicos como "votar contra o aumento da previdência"
ou "alinhamento com o governo federal".

### 6. Posso usar o sistema com qualquer número de WhatsApp?

Sim, mas é necessário usar um número **dedicado para a campanha**
(não o número pessoal do candidato). Configuramos a integração via
Evolution API, que faz a conexão entre o WhatsApp e nosso sistema
de forma profissional, sem usar o WhatsApp Business padrão. Você
divulga esse número em todo material de campanha.

### 7. Como funciona o radar de adversários?

Você cadastra os perfis públicos dos adversários (Instagram, X,
YouTube). Diariamente, o sistema coleta os comentários nos posts
desses perfis e classifica cada um:
- Quem é a favor / contra
- Qual tema gera mais discussão
- Quem está atacando / defendendo
- Comparativos entre adversários

Você vê pontualmente o que está pegando — antes que vire crise.

### 8. Os vídeos são analisados em tempo real?

Não em tempo real. Você submete a URL do vídeo (YouTube, Spotify,
Apple Podcasts) e o sistema processa em segundo plano. Tempo médio:
~2 minutos para vídeos de 30 min, até ~5 minutos para vídeos de 3h.
Você não precisa ficar esperando — o sistema notifica quando termina.

### 9. Posso editar as classificações que a IA fez?

Sim. Toda classificação automática pode ser corrigida pelo admin no
painel. As correções ficam registradas e podem ser usadas para
melhorar a IA no futuro. Em casos onde a IA erra sistematicamente
(por exemplo, sempre classificando um tema específico errado), nossa
equipe ajusta o prompt sob medida para o seu cliente.

### 10. O sistema funciona no celular?

Sim, totalmente. O painel é responsivo e funciona em qualquer
smartphone moderno. A maioria dos clientes usa pelo celular no dia
a dia. O computador é mais útil para análises mais profundas (modal
de vídeos, exportações, gráficos detalhados).

---

## B. SOBRE DADOS E SEGURANÇA (8 perguntas)

### 11. Onde ficam armazenados meus dados?

Os dados ficam em **servidor isolado e exclusivo da sua campanha**,
hospedado em infraestrutura do **Supabase** (banco PostgreSQL com
backup automático) com instância na região São Paulo. Os arquivos
de aplicação rodam em VPS própria gerenciada pela nossa empresa,
também em região Brasil sempre que possível.

### 12. Outros clientes podem ver meus dados?

**Não, em nenhuma hipótese**. Cada cliente nosso tem um banco de
dados completamente separado dos outros. Não há tabela compartilhada,
não há query que cruze clientes. Isolamento físico total. É um dos
nossos diferenciais mais fortes em relação a SaaS multi-tenant
tradicional.

### 13. E a LGPD? Como vocês tratam?

Entregamos um **Instrumento de Tratamento de Dados Pessoais** assinado
junto com o contrato principal. Esse documento define:
- Você é o controlador dos dados (responsável final)
- Nós somos o operador (processamos em seu nome)
- Lista detalhada de quais dados coletamos e por que
- Bases legais aplicáveis (consentimento, legítimo interesse)
- Direitos dos titulares (cidadãos que mandam mensagem)
- Como tratamos incidentes de segurança
- Como excluímos os dados ao final do contrato

Recomendamos que sua equipe jurídica revise o documento antes da
assinatura.

### 14. O que acontece com meus dados se eu cancelar o contrato?

Você pode escolher entre:
- **Eliminação total**: apagamos tudo em até 30 dias, com lavratura
de termo de exclusão assinado por nós
- **Devolução em formato estruturado**: entregamos dump SQL,
CSV e JSON em até 30 dias

Em qualquer dos casos, nossa equipe não retém cópia para usos
próprios, exceto onde a lei exigir (por exemplo, registros fiscais
do contrato em si).

### 15. Tem backup? Com que frequência?

Sim, **backup automático diário** incluso em todos os planos.
Detalhamento:
- Backup completo do banco: diário, retenção 7-30 dias conforme plano
- Snapshots incrementais: a cada 6h, retenção 24h
- Backup off-site (em outra região): semanal, retenção 90 dias

Restauração mediante chamado, com RTO de 8h (Básico) a 2h (Premium).

### 16. Os dados saem do Brasil?

Algumas operações específicas envolvem **transferência internacional
de dados**, expressamente autorizada no Termo LGPD:
- A inteligência artificial (OpenAI Whisper e GPT-4o) processa
mensagens em servidores nos EUA — os dados não são armazenados pela
OpenAI conforme política de zero-retention
- O Supabase tem infraestrutura mãe nos EUA, mas mantém seus dados
de banco em região São Paulo
- Os scrapers de redes sociais (Apify) podem operar a partir de
servidores na Europa ou EUA

Em todos os casos, há cláusulas contratuais padrão de proteção
equivalente à LGPD.

### 17. Quem da sua empresa pode ver meus dados?

Acesso à infraestrutura do cliente é restrito a:
- Equipe técnica autorizada (com termo de confidencialidade
assinado)
- Casos específicos de suporte (sempre com sua autorização
prévia)

Não há acesso indiscriminado. Toda ação técnica é logada e
auditável. Em caso de necessidade de acesso para diagnóstico,
o admin é notificado.

### 18. Como protejo as senhas dos meus operadores?

Boas práticas:
- Cada operador deve ter seu próprio login (nunca compartilhar)
- Admin obrigatoriamente usa 2FA (autenticação em dois fatores)
- Operadores podem ativar 2FA opcionalmente
- Senhas fortes (mínimo 12 caracteres) são exigidas pelo sistema
- Após 5 tentativas falhas, a conta fica bloqueada por 15 minutos
- Senhas são armazenadas no banco com hash bcrypt — nem mesmo nós
temos como ver

Quando um operador sai da campanha, o admin pode desativar a conta
imediatamente.

---

## C. SOBRE OPERAÇÃO (7 perguntas)

### 19. Quanto tempo leva pra ficar tudo pronto?

**Implantação padrão: 5 dias úteis** a partir da assinatura do
contrato:
- Dia 1: documentação e onboarding
- Dia 2: provisionamento técnico (Supabase + servidor)
- Dia 3: configuração específica do cliente (WhatsApp, dados
regionais, branding)
- Dia 4: testes técnicos
- Dia 5: entrega, treinamento e início do uso

**Implantação acelerada**: 48 horas úteis, mediante add-on.
Recomendada para campanhas em momento crítico (lançamento,
debate, crise).

### 20. Quem da minha equipe vai usar o sistema?

Tipicamente:
- **Admin** (1 pessoa): coordenador geral da campanha, chefe de
gabinete ou marqueteiro. Acesso total.
- **Coordenador** (opcional, 1 pessoa): responsável pela operação
de campo. Acesso parcial.
- **Operadores** (3 a 30 pessoas, conforme plano): atendentes,
estagiários, voluntários. Acesso restrito à execução de tarefas.

O candidato não precisa usar o sistema diretamente — ele recebe
relatórios e usa o assistente de WhatsApp (no Premium).

### 21. Precisa de treinamento? Quanto tempo?

Sim, mas é rápido:
- **Admin**: 2 horas de treinamento online (incluso)
- **Operadores**: 30 minutos a 1 hora cada (incluso para até 3)
- **Treinamento adicional** (mais operadores ou repetições):
add-on cobrado à parte

O painel foi desenhado para ser intuitivo. A maioria dos operadores
fica produtivo no primeiro dia.

### 22. Funciona em todos os estados? Só em Minas Gerais?

O sistema funciona em **qualquer estado do Brasil**. O que vem
configurado por padrão é:
- Mapeamento detalhado de **municípios de Minas Gerais** (todos
os 853)
- Regiões históricas eleitorais de MG (Jequitinhonha, Mucuri,
Vale do Rio Doce)

Para outros estados:
- Importamos a lista de municípios do IBGE (incluso na implantação)
- Adicionamos regionalizações específicas mediante solicitação
(pode estar incluído na implantação ou ser cobrado como add-on,
dependendo do plano)

### 23. O sistema fica fora do ar às vezes?

Garantimos uptime de:
- 99,0% no plano Básico
- 99,5% no plano Intermediário
- 99,9% no plano Premium

Manutenções programadas ocorrem em janelas pré-acordadas (geralmente
madrugadas de domingo, com aviso prévio). Indisponibilidades não
programadas são raras e tratadas com prioridade máxima.

Em caso de não cumprimento do uptime, há crédito automático na
mensalidade seguinte conforme o SLA.

### 24. Como peço suporte?

Canais disponíveis:
- **E-mail**: `suporte@[domínio]` — todos os planos
- **WhatsApp dedicado**: Intermediário e Premium
- **Botão no painel**: "Reportar problema", em todos os planos
- **Telefone direto**: apenas Premium, para incidentes críticos
24x7

Tempos de resposta detalhados no SLA. Para problemas críticos,
em qualquer canal, basta marcar como urgente.

### 25. E se eu precisar de mais operadores depois de já estar usando?

Sem problema. Você pode:
- **Comprar pacotes de operadores adicionais** (+10 ou +25
operadores) sem upgrade de plano
- **Fazer upgrade de plano** se múltiplos limites estão sendo
extrapolados

Em ambos os casos, a mudança é aplicada em até 48h sem interrupção
do serviço.

---

## D. SOBRE INVESTIMENTO E CONTRATO (5 perguntas)

### 26. Qual o investimento?

Os valores variam conforme o plano e os add-ons contratados.
A estrutura básica:

- **Implantação (cobrança única)**: cobre todo o trabalho de
provisionamento, configuração e treinamento inicial
- **Mensalidade**: cobrança recorrente, conforme plano

Oferecemos descontos para pagamentos trimestrais ou anuais
antecipados.

A proposta detalhada com valores é enviada após reunião de
qualificação, personalizada para o seu caso. Entre em contato
para receber a sua.

### 27. Tem fidelidade? Preciso me comprometer com prazo mínimo?

O contrato padrão tem **vigência mínima de 6 meses** ou
**período eleitoral integral** (o que for maior). Esse prazo
mínimo se justifica pelo investimento inicial de implantação
e treinamento.

Após o período mínimo, o contrato renova automaticamente em
ciclos mensais, podendo ser encerrado com aviso de 30 dias.

### 28. Posso cancelar a qualquer momento?

Pode, observado o prazo mínimo de fidelidade (item 27). O
cancelamento antecipado dentro do período mínimo está sujeito
a multa rescisória definida em contrato — geralmente
proporcional ao tempo restante.

Após o período mínimo, basta enviar aviso por escrito com 30
dias de antecedência.

### 29. Como é a cobrança?

Modalidades disponíveis:
- **Boleto bancário**: vencimento no dia escolhido por você
- **PIX**: cobrança recorrente automática
- **Transferência bancária**: para cobranças anuais
- **Cartão de crédito recorrente**: mediante combinação,
não é padrão (taxa adicional)

Nota fiscal de serviço emitida automaticamente.

Em caso de atraso superior a 15 dias, o sistema pode entrar em
modo restrito (leitura apenas) até regularização.

### 30. Tem garantia?

Garantias que oferecemos:
- **Implantação no prazo**: se não entregarmos no prazo
prometido (5 dias úteis), há desconto na fatura de implantação
- **Período de adequação**: 30 dias para ajustes de prompt da IA,
fluxos, regionalizações, sem custo
- **Uptime**: créditos automáticos se ficar abaixo do garantido
- **Migração assistida**: importação de dados de outras ferramentas
sem custo nos primeiros 30 dias

O que **não** garantimos:
- Resultado eleitoral (depende de muitos fatores fora do nosso
controle)
- Que a IA acerte 100% das classificações (taxa de acerto típica
é de 90-95%; revisão humana sempre necessária para casos críticos)
- Disponibilidade dos sistemas de terceiros (WhatsApp, Instagram,
OpenAI) quando o problema é do lado deles

---

## Perguntas que você pode adicionar com o tempo

Conforme novos clientes forem chegando, anote as perguntas recorrentes
e adicione aqui. Boas categorias para crescer:

- **Integração com outras ferramentas** (Hubspot, RD Station, etc.)
- **Relatórios e exportações** (PDF, Excel, dashboards de BI)
- **Compliance específico** (TSE, Marco Civil, regramento partidário)
- **Casos de uso avançados** (campanhas multi-candidato, federações
de partidos)
- **Treinamento e certificação** (cursos para operadores, certificado
de uso)
- **Roadmap do produto** (o que vem por aí)

---

## Como usar esta FAQ

### No site institucional
Publicar como página `/faq` com busca e categorias colapsáveis.

### Dentro do painel
Botão "Dúvidas frequentes" no menu de ajuda do painel administrativo,
ligando a esta página.

### Em e-mail comercial
Anexar como PDF no envio de proposta, para que o cliente já tenha as
respostas a mão.

### Para treinamento da equipe
Use este documento no onboarding de novos vendedores e atendentes —
é o "script" de respostas comuns.

### Atualização periódica
Reveja a cada 3 meses. Pergunte aos vendedores e atendentes quais
novas dúvidas estão surgindo. Adicione. Remova as que ninguém mais
pergunta.
