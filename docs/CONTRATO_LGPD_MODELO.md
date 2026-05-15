# Modelo de Termo de Tratamento de Dados (LGPD) — Node Data Política

> **AVISO LEGAL IMPORTANTÍSSIMO**
>
> Este documento é um **MODELO TÉCNICO DE REFERÊNCIA**, redigido para
> orientar a relação entre a sua empresa fornecedora do software (operadora
> de dados) e o candidato cliente (controlador de dados). **Ele NÃO substitui
> consulta a advogado especializado em LGPD e direito eleitoral.** Antes de
> usar com clientes reais, contrate revisão jurídica completa.
>
> O texto a seguir contempla as obrigações da Lei nº 13.709/2018 (LGPD), da
> Lei das Eleições (Lei nº 9.504/1997) e das resoluções do TSE sobre
> propaganda eleitoral e tratamento de dados em campanhas. Cada estado e
> município pode ter regramento adicional que deve ser observado.

---

## Estrutura recomendada

Use este modelo como **anexo do Contrato de Prestação de Serviços** principal,
nominado como "Instrumento Particular de Tratamento de Dados Pessoais".

---

# INSTRUMENTO PARTICULAR DE TRATAMENTO DE DADOS PESSOAIS

**Anexo ao Contrato de Prestação de Serviços nº _____/_____**

Pelo presente instrumento particular, as partes:

**CONTROLADORA**: `[Nome completo do candidato]`, brasileiro(a),
portador(a) do CPF nº `[xxx.xxx.xxx-xx]`, residente e domiciliado(a) em
`[endereço completo]`, atuando individualmente em sua candidatura ao cargo
de `[cargo]` pelo `[partido]` (`[sigla]`), nas eleições de `[ano]`, doravante
denominada simplesmente **CONTROLADORA**;

**OPERADORA**: `[Razão social da sua empresa]`, pessoa jurídica de
direito privado, inscrita no CNPJ sob nº `[xx.xxx.xxx/xxxx-xx]`, com
sede em `[endereço]`, neste ato representada por `[nome do
representante legal]`, doravante denominada simplesmente **OPERADORA**;

resolvem celebrar o presente Instrumento de Tratamento de Dados Pessoais,
em conformidade com a Lei nº 13.709/2018 (Lei Geral de Proteção de Dados —
LGPD), nos termos das cláusulas a seguir.

---

## CLÁUSULA PRIMEIRA — OBJETO

1.1. O presente instrumento regula o tratamento de dados pessoais realizado
pela OPERADORA, por meio da plataforma de inteligência política denominada
**Node Data Política** (doravante "PLATAFORMA"), prestado em benefício e
sob a responsabilidade da CONTROLADORA, no contexto de sua candidatura.

1.2. A PLATAFORMA realiza, dentre outras funcionalidades:

a) coleta de feedbacks de cidadãos via WhatsApp;
b) classificação automatizada de mensagens por sentimento, categoria,
região e urgência;
c) monitoramento de comentários públicos em redes sociais
(Instagram, X/Twitter, YouTube);
d) agregação de notícias políticas por feeds RSS públicos;
e) mapeamento geográfico de demandas por município de Minas Gerais;
f) análise estratégica automatizada de vídeos e podcasts públicos
disponíveis em plataformas como YouTube, Spotify e Apple Podcasts;
g) gerenciamento de operadores de campo e relacionamento com lideranças
locais;
h) geração de respostas automatizadas e sugeridas com auxílio de
inteligência artificial.

---

## CLÁUSULA SEGUNDA — DEFINIÇÕES

2.1. Para os fins deste instrumento, adotam-se as definições do art. 5º
da LGPD, em especial:

a) **Dado Pessoal**: informação relacionada a pessoa natural identificada
ou identificável;
b) **Tratamento**: toda operação realizada com dados pessoais (coleta,
armazenamento, classificação, processamento etc.);
c) **Titular**: pessoa natural a quem se referem os dados pessoais
(cidadãos eleitores, lideranças, operadores de campo, adversários
públicos);
d) **Controlador**: a pessoa natural ou jurídica a quem competem as
decisões referentes ao tratamento (no caso, a CONTROLADORA);
e) **Operador**: pessoa natural ou jurídica que realiza o tratamento em
nome do controlador (no caso, a OPERADORA);
f) **Encarregado (DPO)**: pessoa indicada para atuar como canal de
comunicação entre titulares, controlador, operador e ANPD.

---

## CLÁUSULA TERCEIRA — PAPÉIS E RESPONSABILIDADES

3.1. As partes reconhecem que, para todos os efeitos da LGPD:

a) a **CONTROLADORA** define as finalidades e os meios essenciais do
tratamento de dados, sendo responsável por:

   i. legitimar a coleta e o uso dos dados pelas bases legais cabíveis
   (em especial, legítimo interesse para finalidades eleitorais e
   consentimento expresso quando aplicável);
   ii. atender às solicitações dos titulares previstas no art. 18 da LGPD;
   iii. comunicar incidentes de segurança à Autoridade Nacional de
   Proteção de Dados (ANPD), quando exigível;
   iv. arcar com as obrigações regulamentares perante o TSE e órgãos
   eleitorais;

b) a **OPERADORA** executa o tratamento conforme instruções da
CONTROLADORA, sendo responsável por:

   i. manter as medidas técnicas e administrativas de segurança
   descritas na Cláusula Sétima;
   ii. limitar o tratamento estritamente às finalidades autorizadas;
   iii. auxiliar a CONTROLADORA no atendimento aos titulares quando
   tecnicamente cabível;
   iv. notificar a CONTROLADORA, em até 24 (vinte e quatro) horas, de
   qualquer incidente de segurança que envolva os dados objeto deste
   instrumento.

---

## CLÁUSULA QUARTA — DADOS TRATADOS

4.1. A OPERADORA tratará, em nome da CONTROLADORA, as seguintes categorias
de dados pessoais:

### 4.1.1. Dados de cidadãos contactados via WhatsApp
- Número de telefone (JID do WhatsApp)
- Nome de exibição informado no perfil do WhatsApp
- Conteúdo textual e de áudio das mensagens enviadas
- Município/região informados ou inferidos
- Categoria de demanda (saúde, educação, infraestrutura etc.)
- Histórico de interações

### 4.1.2. Dados de operadores de campo (cabos eleitorais, lideranças)
- Nome completo
- Telefone
- Função na campanha
- Município de atuação
- Score de prioridade (calculado pela plataforma)
- Histórico de mensagens enviadas e recebidas

### 4.1.3. Dados de adversários e figuras públicas
- Nome
- Cargo público ou candidatura
- Manifestações públicas em redes sociais, podcasts, entrevistas e
imprensa (somente conteúdo de natureza pública)

### 4.1.4. Dados de usuários do painel administrativo
- Nome de usuário
- Hash da senha (criptografado, jamais a senha em claro)
- Segredo TOTP do 2FA (criptografado)
- Perfil de acesso (admin, coordenador, operador)
- Registro de acessos e tentativas de login

### 4.1.5. Dados gerados pela plataforma
- Transcrições de áudios e vídeos
- Análises geradas por inteligência artificial
- Classificações automáticas (sentimento, urgência, alinhamento)
- Estatísticas agregadas por município, região, candidato

4.2. **Categorias de dados sensíveis**: a CONTROLADORA reconhece e aceita
que algumas mensagens recebidas via WhatsApp podem conter dados pessoais
sensíveis (origem racial, opinião política, convicção religiosa, dado
referente à saúde etc.). O tratamento desses dados, quando ocorrer, será
limitado ao estritamente necessário para o atendimento da demanda do
cidadão e respeitará as bases legais da LGPD aplicáveis a dados sensíveis.

4.3. **Dados de menores**: a plataforma não se destina à coleta intencional
de dados de crianças e adolescentes. A CONTROLADORA se compromete a não
direcionar comunicações a este público. Caso a OPERADORA detecte tratamento
involuntário, comunicará imediatamente à CONTROLADORA para providências.

---

## CLÁUSULA QUINTA — BASES LEGAIS

5.1. A CONTROLADORA declara que o tratamento dos dados ocorre, conforme
o caso, sob as seguintes bases legais previstas no art. 7º da LGPD:

a) **Consentimento** do titular, obtido por meio da resposta espontânea
do cidadão ao número de WhatsApp divulgado pela campanha, sendo
informado sobre a finalidade do contato no início da interação;

b) **Execução de políticas públicas** e exercício regular de direitos
no contexto eleitoral, conforme art. 7º, III e VI;

c) **Legítimo interesse** da CONTROLADORA, no monitoramento de
manifestações públicas em redes sociais, podcasts e imprensa,
respeitados os direitos e liberdades fundamentais do titular
(art. 7º, IX);

d) **Cumprimento de obrigação legal**, quando aplicável, especialmente
no que se refere a registros e transparência exigidos pela legislação
eleitoral.

5.2. Para dados pessoais sensíveis, aplicam-se as bases do art. 11 da
LGPD, em especial o consentimento específico e destacado.

---

## CLÁUSULA SEXTA — DIREITOS DOS TITULARES

6.1. A CONTROLADORA garantirá aos titulares, a qualquer momento, o
exercício dos direitos previstos no art. 18 da LGPD:

a) confirmação da existência de tratamento;
b) acesso aos dados;
c) correção de dados incompletos, inexatos ou desatualizados;
d) anonimização, bloqueio ou eliminação de dados desnecessários;
e) portabilidade dos dados a outro fornecedor;
f) eliminação dos dados tratados com base no consentimento;
g) informação sobre compartilhamento;
h) revogação do consentimento;
i) revisão de decisões automatizadas que afetem seus interesses.

6.2. As solicitações dos titulares serão recebidas pelo Encarregado da
CONTROLADORA, conforme Cláusula Décima Quarta.

6.3. A OPERADORA disponibilizará à CONTROLADORA, sem custo adicional, as
ferramentas técnicas necessárias para atender estas solicitações
(exportação de dados, exclusão por solicitação, etc.).

---

## CLÁUSULA SÉTIMA — SEGURANÇA TÉCNICA E ADMINISTRATIVA

7.1. A OPERADORA implementa e mantém as seguintes medidas de segurança,
no mínimo:

### Segurança técnica
a) Comunicação cifrada em trânsito (HTTPS/TLS 1.2+ em todas as rotas
externas);
b) Senhas armazenadas com hash bcrypt (custo configurável, mínimo 12);
c) Autenticação em dois fatores (2FA) obrigatória para perfis
administrativos;
d) Política de cookies httpOnly, sameSite Lax e Secure em produção;
e) Proteção contra CSRF em formulários sensíveis;
f) Lockout temporário após 5 tentativas falhas de login;
g) Hospedagem em provedores que cumprem boas práticas de segurança
(Supabase, Coolify em VPS isolada);
h) Backup automatizado diário do banco de dados, com retenção mínima
de 7 dias;
i) Logs de auditoria de acessos administrativos retidos por 6 meses;
j) Isolamento físico (banco de dados dedicado) entre clientes diferentes
da OPERADORA, garantindo que dados de uma campanha não sejam acessíveis
a outra.

### Segurança administrativa
k) Acesso ao código e à infraestrutura limitado a pessoal técnico
autorizado, com termo de confidencialidade assinado;
l) Política interna de classificação de dados e ciclo de vida da
informação;
m) Treinamento periódico da equipe sobre LGPD e segurança da informação;
n) Revisão semestral das permissões de acesso ao sistema.

7.2. A OPERADORA não armazena dados de cartão de crédito ou meios de
pagamento; eventual cobrança do cliente ocorre por intermediário próprio
(Stripe, Pagar.me, ou similar).

---

## CLÁUSULA OITAVA — SUBCONTRATAÇÃO E TRANSFERÊNCIA INTERNACIONAL

8.1. A CONTROLADORA autoriza expressamente a OPERADORA a utilizar os
seguintes subcontratados (suboperadores) no tratamento dos dados,
mediante compromisso destes em observar a LGPD e padrões equivalentes:

| Suboperador | Finalidade | Localização |
|---|---|---|
| Supabase (banco de dados) | Armazenamento e autenticação | EUA (com instância em São Paulo, SA-East-1) |
| OpenAI | Transcrição (Whisper) e análise de texto (GPT-4o) | EUA |
| Apify | Coleta de comentários públicos em redes sociais | República Tcheca / EUA |
| Evolution API | Integração com WhatsApp | Brasil ou conforme deploy |
| Coolify | Orquestração de containers | Brasil (na infraestrutura da OPERADORA) |
| Provedor de VPS (Hetzner / DigitalOcean / outro) | Hospedagem da aplicação | A definir, com preferência por região Brasil |

8.2. **Transferência internacional de dados**: a CONTROLADORA reconhece
e autoriza expressamente a transferência internacional de dados pessoais
para os suboperadores listados, nos termos do art. 33, V e IX da LGPD,
mediante adoção pela OPERADORA de cláusulas contratuais padrão ou
mecanismos equivalentes de garantia.

8.3. A OPERADORA notificará a CONTROLADORA com 30 (trinta) dias de
antecedência sobre a inclusão de novos suboperadores que tratem dados
pessoais, possibilitando objeção fundamentada.

---

## CLÁUSULA NONA — INCIDENTES DE SEGURANÇA

9.1. A OPERADORA comunicará à CONTROLADORA, em prazo não superior a
**24 (vinte e quatro) horas** após a ciência, qualquer incidente de
segurança que possa acarretar risco ou dano relevante aos titulares.

9.2. A comunicação conterá, no mínimo:

a) descrição da natureza do incidente;
b) categoria e quantidade aproximada de dados e titulares afetados;
c) medidas técnicas e administrativas adotadas para mitigação;
d) riscos relacionados;
e) recomendações para o cumprimento das obrigações da CONTROLADORA
perante a ANPD e os titulares.

9.3. A CONTROLADORA é responsável pela comunicação do incidente à ANPD
e aos titulares, conforme art. 48 da LGPD, podendo contar com auxílio
técnico da OPERADORA na elaboração da comunicação.

---

## CLÁUSULA DÉCIMA — ELIMINAÇÃO E DEVOLUÇÃO DOS DADOS

10.1. Ao término do contrato principal, por qualquer motivo, a OPERADORA
fica obrigada a, conforme instrução da CONTROLADORA:

a) **eliminar** todos os dados pessoais sob sua custódia, em prazo não
superior a 30 (trinta) dias, lavrando-se termo de eliminação assinado;
ou
b) **devolver** os dados em formato estruturado e interoperável
(JSON, CSV, dump SQL), em prazo não superior a 30 (trinta) dias.

10.2. A OPERADORA poderá conservar dados apenas pelo tempo estritamente
necessário ao cumprimento de obrigação legal ou regulatória, ou para o
exercício regular de direitos em processo judicial, administrativo ou
arbitral, anonimizando-os sempre que possível.

10.3. **Período eleitoral**: tendo em vista o ciclo de uma campanha
política, as partes acordam que, sem prejuízo do disposto acima, os
dados poderão ser conservados até 30 (trinta) dias após a diplomação ou
o trânsito em julgado de eventual ação eleitoral, o que ocorrer por
último, salvo manifestação em contrário da CONTROLADORA.

---

## CLÁUSULA DÉCIMA PRIMEIRA — AUDITORIA

11.1. A CONTROLADORA poderá auditar, mediante aviso prévio de 15
(quinze) dias úteis, o cumprimento das obrigações deste instrumento pela
OPERADORA, limitando-se a uma auditoria por ano, salvo em caso de
incidente concreto que justifique nova revisão.

11.2. A auditoria poderá ser conduzida pela própria CONTROLADORA, por
auditor independente por ela contratado, ou ainda por intermédio do
Encarregado/DPO, observados os deveres de sigilo.

11.3. A OPERADORA fornecerá, mediante solicitação razoável, evidências
documentais e técnicas das medidas de segurança adotadas.

---

## CLÁUSULA DÉCIMA SEGUNDA — RESPONSABILIDADE E INDENIZAÇÃO

12.1. As partes respondem por danos causados a titulares ou terceiros
em razão de tratamento irregular de dados, na medida de sua atuação,
conforme art. 42 da LGPD.

12.2. Em caso de condenação solidária, fica assegurado direito de
regresso entre as partes, observando-se a responsabilidade efetiva de
cada uma na conduta que ensejou o dano.

12.3. A OPERADORA limita sua responsabilidade indenizatória à soma
total dos valores efetivamente pagos pela CONTROLADORA nos últimos 12
(doze) meses, ressalvados os casos de dolo ou culpa grave.

---

## CLÁUSULA DÉCIMA TERCEIRA — CONFIDENCIALIDADE

13.1. As partes obrigam-se a manter sigilo absoluto sobre quaisquer
informações, dados, estratégias, análises e demais conteúdos a que
tiverem acesso por força deste instrumento.

13.2. A obrigação de confidencialidade subsiste por 5 (cinco) anos após
o término do contrato.

13.3. Não se incluem na obrigação de sigilo as informações:

a) já públicas no momento da divulgação;
b) que se tornarem públicas sem violação deste instrumento;
c) cuja divulgação for exigida por lei ou ordem judicial.

---

## CLÁUSULA DÉCIMA QUARTA — ENCARREGADOS / DPO

14.1. As partes designam os seguintes Encarregados de Proteção de Dados
para fins de comunicação relacionada à LGPD:

**Pela CONTROLADORA**:
Nome: `[ ]`
E-mail: `[ ]`
Telefone: `[ ]`

**Pela OPERADORA**:
Nome: `[ ]`
E-mail: `dpo@seudominio.com.br`
Telefone: `[ ]`

14.2. Qualquer alteração no Encarregado deve ser comunicada à outra
parte em até 5 (cinco) dias úteis.

---

## CLÁUSULA DÉCIMA QUINTA — VIGÊNCIA

15.1. O presente instrumento entra em vigor na data de sua assinatura e
permanece vigente enquanto durar o contrato principal de prestação de
serviços, prorrogando-se automaticamente nas suas eventuais renovações.

15.2. As obrigações relativas a:

a) segurança (Cláusula Sétima);
b) eliminação ou devolução de dados (Cláusula Décima);
c) confidencialidade (Cláusula Décima Terceira);

subsistem após o término do contrato pelos prazos nelas indicados.

---

## CLÁUSULA DÉCIMA SEXTA — DISPOSIÇÕES GERAIS

16.1. Eventuais tolerâncias quanto ao cumprimento das obrigações ora
pactuadas constituirão mera liberalidade, não importando renúncia,
novação ou alteração contratual.

16.2. Este instrumento é firmado em caráter pessoal e intransferível,
sendo nula sua cessão a terceiros sem prévia e expressa autorização da
outra parte.

16.3. As alterações deste instrumento somente serão válidas se feitas
por escrito e assinadas por ambas as partes.

---

## CLÁUSULA DÉCIMA SÉTIMA — FORO

17.1. Fica eleito o foro da Comarca de `[cidade]`, Estado de
`[estado]`, para dirimir quaisquer controvérsias oriundas deste
instrumento, com renúncia a qualquer outro, por mais privilegiado que
seja.

---

E por estarem assim justas e contratadas, as partes assinam o presente
instrumento, em duas vias de igual teor e forma, na presença das
testemunhas abaixo identificadas.

`[Cidade]`, `[ ]` de `[ ]` de `[ano]`.

```
________________________________________
CONTROLADORA
[Nome do candidato]
CPF: [ ]


________________________________________
OPERADORA
[Razão social] CNPJ: [ ]
Representante: [Nome]
CPF: [ ]


Testemunhas:

1.) Nome:                              2.) Nome:
    CPF:                                   CPF:
    Assinatura:                            Assinatura:
```

---

## ANEXO I — Avisos a serem incluídos pela CONTROLADORA na divulgação
do WhatsApp da campanha

Para legitimar a coleta via consentimento dos cidadãos, recomenda-se que
a CONTROLADORA divulgue, sempre que veicular o número de WhatsApp da
campanha (peças impressas, redes, comícios), aviso similar a:

> "Ao enviar mensagem para este número, você concorda que sua mensagem
> e seu contato sejam tratados pela equipe da campanha de [Nome do
> Candidato] para fins de atendimento e diagnóstico de demandas
> populares, podendo sua mensagem ser analisada com auxílio de
> inteligência artificial. Você pode solicitar a exclusão a qualquer
> momento pelo e-mail [dpo@campanha.com.br]. Saiba mais em
> [URL da política de privacidade da campanha]."

Recomenda-se que, na primeira interação do bot com cada cidadão, seja
enviada mensagem automática com o teor acima.

---

## ANEXO II — Política de Privacidade Resumida da Campanha (modelo)

A CONTROLADORA deve manter, em domínio próprio da campanha, uma página
de Política de Privacidade pública. Modelo mínimo:

```
POLÍTICA DE PRIVACIDADE — CAMPANHA [NOME DO CANDIDATO]

1. Quem somos
[Identificação da campanha, CNPJ se houver, endereço, contato]

2. Quais dados coletamos
- Dados que você nos envia (WhatsApp, formulários, redes sociais)
- Dados públicos de redes sociais e imprensa
- Dados anonimizados de navegação no nosso site

3. Para que usamos
- Atendimento das suas demandas
- Diagnóstico territorial de problemas para propostas de campanha
- Comunicação eleitoral autorizada pelo titular

4. Com quem compartilhamos
Operamos a plataforma [Node Data Política] fornecida pela empresa
[Razão Social Operadora], que processa os dados em nosso nome.
Os dados podem trafegar por servidores nos Estados Unidos
(Supabase, OpenAI), sempre com garantias contratuais de proteção.

5. Por quanto tempo guardamos
Mantemos os dados pelo período da campanha eleitoral até 30 dias
após a diplomação ou trânsito em julgado de ação eleitoral.

6. Seus direitos
Você pode solicitar a qualquer momento acesso, correção, exclusão
ou portabilidade dos seus dados, escrevendo para [dpo@campanha.com.br].

7. Encarregado
[Nome do DPO]
[E-mail]
[Telefone]
```

---

## ANEXO III — Checklist mínimo de conformidade

Para cada candidato cliente, validar:

- [ ] Termo de Tratamento de Dados assinado e arquivado
- [ ] Política de Privacidade da campanha publicada em URL acessível
- [ ] Aviso de consentimento divulgado junto ao número de WhatsApp
- [ ] Encarregado (DPO) da campanha designado por escrito
- [ ] Resposta automática inicial do WhatsApp com aviso LGPD configurada
- [ ] Lista de subcontratados (Anexo da Cláusula Oitava) anexada e atualizada
- [ ] Formulário de solicitação de direitos do titular disponibilizado
- [ ] Processo interno de notificação de incidentes em 24h documentado
- [ ] Treinamento da equipe da campanha sobre LGPD registrado
- [ ] Auditoria interna técnica anual agendada
- [ ] Backup do banco de dados confirmado em duas regiões
- [ ] Eliminação programada de dados pós-eleição agendada no calendário
