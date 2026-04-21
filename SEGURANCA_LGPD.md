# Seguranca e LGPD

## Objetivo

Criar um plano de hardening para proteger dados sensiveis de campanha, operadores, cidadaos, liderancas, tarefas, estrategia e informacoes financeiras futuras.

Este projeto deve ser tratado como **nivel sensivel alto**, porque pode envolver telefone, opiniao politica, liderancas, cidade, demandas, pedidos de verba, estrategia territorial e dados de campanha.

## Riscos Principais

- Vazamento de contatos de cabos, liderancas e cidadaos.
- Exposicao de estrategia de campanha por cidade.
- Logs com telefone, JID ou mensagem completa.
- Webhook recebendo chamadas falsas.
- Usuario interno acessando dados que nao deveria.
- Exportacao indevida de dados.
- Chaves de API expostas.
- Dados enviados para IA sem minimizacao.
- Falta de auditoria em acoes criticas.

## Prioridade 1 - Logs Seguros

Hoje logs de debug podem expor dados demais. A regra deve ser:

- nunca logar telefone completo;
- nunca logar JID completo;
- nunca logar mensagem completa de cidadao/cabo;
- nunca logar texto completo transcrito de audio;
- nunca logar tokens, chaves ou payload bruto;
- usar telefone mascarado;
- logar apenas contexto minimo: evento, cidade, tipo, status, id.

Exemplo desejado:

```text
[operacao] atualizacao salva operador=Rafael telefone=5544***71 cidade=Vespasiano tipo=lideranca
```

Evitar:

```text
Processing new feedback: texto completo da pessoa...
```

## Prioridade 2 - Webhook Protegido

Adicionar `WEBHOOK_SECRET` no ambiente e validar toda requisicao do webhook.

Opcoes:

- header `X-Webhook-Secret`;
- query param secreto;
- Authorization Bearer.

Regras:

- rejeitar requisicao sem segredo;
- rejeitar payload invalido;
- manter retorno rapido;
- evitar processar payload gigante;
- criar idempotencia para nao duplicar evento.

## Prioridade 3 - Controle de Acesso

Criar papeis:

- admin;
- deputado;
- coordenador;
- operador/cabo;
- leitura.

Permissoes sugeridas:

- admin: tudo;
- deputado: dashboard, prioridades, tarefas, operacao, financeiro resumido;
- coordenador: operacao local, tarefas da regiao, operadores da regiao;
- operador/cabo: somente enviar WhatsApp, sem acesso ao painel;
- leitura: dashboard limitado.

## Prioridade 4 - Sessao e Login

Melhorias recomendadas:

- senha forte via variavel de ambiente;
- cookie `Secure`;
- cookie `HttpOnly`;
- cookie `SameSite=Lax` ou `Strict`;
- expirar sessao;
- limitar tentativas de login;
- registrar login falho;
- considerar 2FA para admin.

## Prioridade 5 - Supabase

Regras:

- `service_role` somente no backend;
- nunca expor service key no frontend;
- RLS ativo nas tabelas sensiveis;
- policies por campanha/cliente quando houver multi-cliente;
- criar indices nas queries criticas;
- limitar queries grandes;
- evitar endpoint que retorna tudo sem paginacao;
- backup ativado;
- rotina de rollback.

Tabelas sensiveis:

- feedbacks;
- operadores_campo;
- operacao_local_atualizacoes;
- tarefas_gabinete;
- contatos_gabinete;
- futuras tabelas financeiras.

## Prioridade 6 - Minimizacao de Dados

Guardar apenas o necessario.

Regras:

- nao armazenar audio bruto se nao for necessario;
- nao guardar conteudo completo quando resumo for suficiente;
- mascarar telefone na interface sempre que possivel;
- limitar retencao de dados antigos;
- separar dado operacional de dado pessoal;
- enviar para IA somente o texto necessario.

## Prioridade 7 - Auditoria

Registrar eventos criticos:

- login;
- cadastro de operador;
- criacao de tarefa;
- conclusao de tarefa;
- criacao de pedido financeiro;
- aprovacao de gasto;
- exportacao;
- consulta de dados sensiveis;
- alteracao de status;
- erro de webhook.

Tabela sugerida:

### auditoria_eventos

- id
- usuario
- papel
- acao
- entidade
- entidade_id
- telefone_mascarado
- ip
- user_agent
- metadata_json
- criado_em

## Prioridade 8 - Exportacao e Downloads

Exportar dados e uma das maiores portas de vazamento.

Regras:

- exportar somente para admin;
- registrar auditoria;
- limitar campos sensiveis;
- mascarar telefone por padrao;
- gerar arquivo temporario;
- expirar link;
- evitar exportar mensagem completa sem motivo.

## Prioridade 9 - IA e Dados Sensíveis

Antes de enviar texto para IA:

- remover telefone, CPF, email se aparecer;
- evitar mandar nome completo quando nao precisa;
- mandar somente trecho necessario;
- nao usar dados para treinamento;
- registrar finalidade do uso.

## Sprint de Hardening Recomendada

### Fase 1 - Imediata

- mascarar logs;
- remover logs de mensagem completa;
- adicionar `WEBHOOK_SECRET`;
- validar tamanho do payload;
- configurar cookies seguros;
- revisar endpoints abertos.

### Fase 2 - Curto Prazo

- tabela de auditoria;
- rate limit no login e webhook;
- roles e permissoes;
- pagina de auditoria simples;
- politica de exportacao.

### Fase 3 - Produto Maduro

- 2FA;
- multi-tenancy por campanha;
- criptografia adicional para campos criticos;
- retencao automatica;
- painel de incidentes;
- backups testados.

## Checklist Antes de Apresentar Para Campanha Grande

- [ ] Logs nao mostram telefone completo.
- [ ] Logs nao mostram mensagem completa.
- [ ] Webhook exige segredo.
- [ ] Login tem sessao segura.
- [ ] Service role nao aparece no frontend.
- [ ] RLS ativo nas tabelas sensiveis.
- [ ] Operadores nao acessam painel administrativo.
- [ ] Existe plano de revogacao de token.
- [ ] Existe plano de rollback.
- [ ] Exportacao esta controlada.

## Posicionamento Comercial

Frase de venda:

> Inteligencia de campanha com controle de acesso, rastreabilidade e protecao LGPD.

## Observacao

Este documento nao substitui assessoria juridica. Ele serve como plano tecnico e operacional de seguranca para reduzir risco e preparar o produto para campanhas maiores.
