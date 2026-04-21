# Financeiro de Campanha

## Objetivo

Criar uma aba gerencial para o deputado enxergar para onde o dinheiro da campanha esta indo, quem pediu, quem aprovou, quais cidades consomem mais recurso e quais gastos ainda precisam de comprovacao.

Esta feature nao substitui contador, juridico ou prestacao oficial ao TSE. Ela deve funcionar como controle operacional interno da campanha.

## Problema Que Resolve

Campanha regional tem muitos pedidos e gastos pequenos espalhados:

- vereador pedindo verba para reuniao;
- cabo eleitoral pedindo combustivel;
- assessor pagando alimentacao ou deslocamento;
- evento precisando de som, cadeira, material grafico;
- impulsionamento por cidade;
- reembolso sem comprovante;
- gasto alto em cidade com pouco retorno politico.

Sem painel, o deputado perde controle e decide no escuro.

## Aba Proposta

Nome sugerido: **Financeiro de Campanha** ou **Orcamento de Campo**.

### Cards Principais

- Gasto total no periodo
- Pedidos pendentes
- Valor aprovado ainda nao pago
- Valor pago sem comprovacao
- Cidades com maior gasto
- Operadores com maior despesa
- Alto gasto / baixo movimento

## Subareas

### 1. Resumo

Mostra a foto geral do caixa operacional:

- total gasto;
- total pendente;
- total aprovado;
- total sem comprovacao;
- gasto por semana;
- gasto por categoria.

### 2. Pedidos de Verba

Campos principais:

- solicitante;
- telefone/JID;
- cidade;
- finalidade;
- valor pedido;
- urgencia;
- status: pendente, aprovado, negado, pago, prestado;
- quem aprovou;
- data do pedido;
- observacoes.

### 3. Gastos Realizados

Categorias iniciais:

- combustivel;
- alimentacao;
- transporte;
- hospedagem;
- evento;
- material grafico;
- impulsionamento;
- equipe/cabos;
- som/estrutura;
- outros.

Campos:

- valor;
- cidade;
- operador/responsavel;
- categoria;
- descricao curta;
- comprovante;
- status de comprovacao.

### 4. Por Cidade

Ranking de cidades por gasto:

- gasto total;
- pedidos pendentes;
- comprovacoes faltando;
- numero de agendas;
- numero de movimentos de campo;
- custo por movimento;
- alerta de alto gasto e baixo retorno.

### 5. Por Operador

Mostra quem esta consumindo recurso:

- operador;
- cidade/regiao;
- total pedido;
- total aprovado;
- total pendente de nota;
- ultimo pedido;
- produtividade de campo.

### 6. Alertas

Alertas sugeridos:

- gasto sem comprovante ha mais de 7 dias;
- pedido duplicado parecido;
- valor acima do limite definido;
- cidade com gasto alto e pouco movimento;
- operador com muitas despesas e poucas atualizacoes;
- gasto sem cidade associada;
- gasto sem responsavel.

## Fluxo Pelo WhatsApp

Operadores e assessores poderiam mandar mensagens como:

```text
Pedido de verba: R$ 800 para combustivel em Irati.
```

```text
Gasto realizado: R$ 220 em almoco com liderancas em Uniao da Vitoria. Nota enviada.
```

```text
Preciso aprovar R$ 1.500 para som de evento em Ponta Grossa.
```

O sistema classificaria:

- tipo: pedido, gasto, reembolso ou comprovacao;
- cidade;
- valor;
- categoria;
- solicitante;
- status inicial;
- necessidade de aprovacao.

## Tabelas Sugeridas

### financeiro_pedidos

- id
- solicitante_nome
- solicitante_jid
- cidade
- regiao
- finalidade
- categoria
- valor_pedido
- valor_aprovado
- status
- urgencia
- aprovado_por
- observacoes
- criado_em
- atualizado_em

### financeiro_gastos

- id
- pedido_id
- responsavel_nome
- responsavel_jid
- cidade
- categoria
- valor
- descricao
- status_comprovacao
- comprovante_url
- origem
- criado_em
- atualizado_em

### financeiro_comprovacoes

- id
- gasto_id
- tipo
- arquivo_url
- observacao
- enviado_por
- criado_em

### financeiro_centros_custo

- id
- nome
- tipo: cidade, evento, coordenador, midia, equipe
- cidade
- status
- criado_em

## MVP Recomendado

Versao 1:

- criar aba Financeiro;
- cadastrar pedido manual pelo painel;
- registrar gasto manual pelo painel;
- mostrar resumo por cidade;
- mostrar pendencias de comprovacao;
- permitir criar pedido via WhatsApp;
- botao "aprovar", "negar" e "marcar como pago".

Versao 2:

- upload de comprovantes;
- alertas;
- vinculo com Operacao Local;
- custo por cidade;
- custo por movimento;
- auditoria financeira.

## Posicionamento Comercial

Frase de venda:

> O deputado nao perde mais dinheiro no escuro. Cada gasto fica ligado a cidade, operador, finalidade e retorno politico.

## Cuidados

- Nao prometer prestacao oficial automatica.
- Nao misturar recurso eleitoral com caixa informal.
- Registrar tudo com trilha de auditoria.
- Exibir dados financeiros apenas para usuarios autorizados.
- Evitar exportacao ampla sem controle.
