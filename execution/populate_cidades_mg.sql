-- ============================================================
-- Node Data Política — Feedbacks com Cidades de MG
-- Cenário: Dep. Estadual - Monitoramento Político em Minas Gerais
-- Execute no SQL Editor do Supabase
-- ============================================================

-- 1. Adicionar coluna city se não existir
ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS city text;

-- 2. Limpar dados mock anteriores
TRUNCATE feedbacks RESTART IDENTITY;

-- 3. Inserir feedbacks com cidades de MG
INSERT INTO feedbacks (sender, name, message, timestamp, category, region, urgency, sentiment, topic, status, city, resolved_at, created_at) VALUES

-- ===================== BELO HORIZONTE (10 feedbacks) =====================

('5531987410001', 'Ana Paula Ferreira',
 'Bom dia! Moro no bairro Barreiro em Belo Horizonte e quero elogiar o projeto das creches comunitárias que foi aprovado. Nossa creche vai receber reforma, as crianças precisavam muito disso!',
 now() - interval '6 hours',
 'Saúde & Educação', 'Zona Oeste', 'Positivo', 'Positivo', 'creches comunitárias aprovadas',
 'resolvido', 'Belo Horizonte', (now() - interval '2 hours')::text, now() - interval '6 hours'),

('5531976523302', 'Ricardo Nascimento',
 'Deputado, a situação da segurança no hipercentro de Belo Horizonte está insuportável. Minha loja na Rua dos Caetés foi assaltada 3 vezes em 2 meses. As câmeras de monitoramento não funcionam. Precisamos de ação urgente!',
 now() - interval '1 day',
 'Segurança Pública', 'Centro', 'Urgente', 'Negativo', 'assaltos no hipercentro BH',
 'em_andamento', 'Belo Horizonte', null, now() - interval '1 day'),

('5531998234561', 'Mariana Costa Silva',
 'Moro na região do Barreiro em BH e a UBS do bairro está fechada há 15 dias sem médico. Sou hipertensa e não consigo acompanhamento. Belo Horizonte não pode ter esse tipo de abandono na saúde pública!',
 now() - interval '1 day 4 hours',
 'Saúde & Educação', 'Zona Oeste', 'Urgente', 'Negativo', 'UBS fechada sem médico BH',
 'aberto', 'Belo Horizonte', null, now() - interval '1 day 4 hours'),

('5531965432110', 'Fernando Oliveira',
 'Parabéns ao deputado pela aprovação do projeto de ciclovias em Belo Horizonte! A Avenida Amazonas já está recebendo as obras. Isso vai mudar a mobilidade da cidade. Continuem assim!',
 now() - interval '2 days',
 'Transporte & Mobilidade', 'Centro', 'Positivo', 'Positivo', 'ciclovias BH aprovadas',
 'resolvido', 'Belo Horizonte', (now() - interval '1 day')::text, now() - interval '2 days'),

('5531943217655', 'Cláudia Aparecida',
 'A Avenida Vilarinho em Venda Nova, Belo Horizonte, está com buracos enormes. Dois ônibus quebraram essa semana por causa do asfalto destruído. É um perigo para motoristas e pedestres!',
 now() - interval '3 days',
 'Infraestrutura & Obras', 'Zona Norte', 'Urgente', 'Negativo', 'buracos Av Vilarinho BH',
 'em_andamento', 'Belo Horizonte', null, now() - interval '3 days'),

('5531921098766', 'Pedro Henrique Santos',
 'Denúncia grave: estão despejando entulho de construção na Serra do Curral em Belo Horizonte. Área de preservação ambiental sendo destruída. Tenho fotos e vídeos como prova.',
 now() - interval '4 days',
 'Meio Ambiente', 'Zona Sul', 'Critico', 'Negativo', 'despejo entulho Serra do Curral',
 'em_andamento', 'Belo Horizonte', null, now() - interval '4 days'),

('5531934521877', 'Luciana Cardoso',
 'Quero agradecer ao gabinete pela intermediação no caso do BPC da minha mãe aqui em BH. Em 15 dias vocês resolveram o que eu tentei por 8 meses. Equipe nota 10!',
 now() - interval '5 days',
 'Assistência Social', 'Zona Norte', 'Positivo', 'Positivo', 'BPC resolvido rapidamente',
 'resolvido', 'Belo Horizonte', (now() - interval '4 days')::text, now() - interval '5 days'),

('5531956234188', 'Roberto Almeida',
 'O projeto de lei para reduzir a tarifa de ônibus em Belo Horizonte foi engavetado? A passagem está R$5,75 e o salário mínimo não acompanha. Quando vai ser votado?',
 now() - interval '6 days',
 'Transporte & Mobilidade', 'Zona Sul', 'Neutro', 'Negativo', 'tarifa ônibus BH alta',
 'aberto', 'Belo Horizonte', null, now() - interval '6 days'),

('5531912876544', 'Tatiana Rodrigues',
 'Sou empresária em Belo Horizonte e quero propor uma audiência sobre incentivos fiscais para startups de tecnologia. A capital mineira tem potencial enorme mas a burocracia trava tudo.',
 now() - interval '8 days',
 'Desenvolvimento Econômico', 'Centro', 'Neutro', 'Neutro', 'incentivos startups BH',
 'aberto', 'Belo Horizonte', null, now() - interval '8 days'),

('5531987654321', 'Gilberto Mendes',
 'Deputado, o programa de requalificação profissional que foi aprovado para a região metropolitana de Belo Horizonte já empregou 200 pessoas no meu bairro. Política pública que funciona!',
 now() - interval '10 days',
 'Desenvolvimento Econômico', 'Zona Norte', 'Positivo', 'Positivo', 'requalificação profissional BH',
 'resolvido', 'Belo Horizonte', (now() - interval '9 days')::text, now() - interval '10 days'),

-- ===================== UBERLÂNDIA (5 feedbacks) =====================

('5534987410002', 'Carlos Eduardo Lima',
 'Moro em Uberlândia e a situação dos buracos na Avenida Rondon Pacheco é vergonhosa. Já foram 4 acidentes essa semana. A prefeitura não resolve e o Estado precisa intervir.',
 now() - interval '8 hours',
 'Infraestrutura & Obras', 'Centro', 'Urgente', 'Negativo', 'buracos Av Rondon Pacheco',
 'aberto', 'Uberlândia', null, now() - interval '8 hours'),

('5534976523303', 'Patrícia Oliveira',
 'Boa tarde! O hospital da UFU em Uberlândia está com fila de 6 meses para cirurgia ortopédica. Minha mãe de 72 anos precisa operar o quadril urgente. Como o deputado pode ajudar?',
 now() - interval '2 days 3 hours',
 'Saúde & Educação', 'Zona Sul', 'Urgente', 'Negativo', 'fila cirurgia hospital UFU',
 'em_andamento', 'Uberlândia', null, now() - interval '2 days 3 hours'),

('5534998234562', 'Marcos Vinícius',
 'Quero parabenizar o deputado pelo projeto de incentivo à agricultura familiar na região de Uberlândia. Minha cooperativa de hortaliças já exporta para 3 estados. Isso é desenvolvimento real!',
 now() - interval '5 days',
 'Desenvolvimento Econômico', 'Zona Rural', 'Positivo', 'Positivo', 'cooperativa hortaliças cresceu',
 'resolvido', 'Uberlândia', (now() - interval '4 days')::text, now() - interval '5 days'),

('5534965432111', 'Fernanda Rocha',
 'Uberlândia precisa urgente de mais linhas de ônibus para o bairro Morumbi. A população cresceu 40% nos últimos 3 anos e o transporte continua o mesmo. Trabalhadores ficam 2h esperando no ponto.',
 now() - interval '7 days',
 'Transporte & Mobilidade', 'Zona Norte', 'Neutro', 'Negativo', 'falta ônibus bairro Morumbi',
 'aberto', 'Uberlândia', null, now() - interval '7 days'),

('5534943217656', 'André Luiz Pereira',
 'Denúncia: empresa está poluindo o Rio Uberabinha em Uberlândia com descarte de produtos químicos. A água está com cheiro forte. Isso afeta o abastecimento da cidade inteira!',
 now() - interval '9 days',
 'Meio Ambiente', 'Zona Leste', 'Critico', 'Negativo', 'poluição Rio Uberabinha',
 'em_andamento', 'Uberlândia', null, now() - interval '9 days'),

-- ===================== CONTAGEM (5 feedbacks) =====================

('5531987410003', 'Rosimeire Santos',
 'Boa tarde! A Avenida João César de Oliveira em Contagem está intransitável. Buracos enormes na pista principal. Já quebraram vários carros essa semana. Precisamos de recapeamento urgente!',
 now() - interval '10 hours',
 'Infraestrutura & Obras', 'Centro', 'Urgente', 'Negativo', 'buracos Av João César Contagem',
 'aberto', 'Contagem', null, now() - interval '10 hours'),

('5531976523304', 'José Aparecido',
 'O projeto de iluminação pública na região do Eldorado em Contagem foi uma benção! Eram 4 anos no escuro. Agora as famílias podem sair de casa à noite com mais segurança. Obrigado deputado!',
 now() - interval '3 days 2 hours',
 'Segurança Pública', 'Zona Norte', 'Positivo', 'Positivo', 'iluminação Eldorado Contagem',
 'resolvido', 'Contagem', (now() - interval '2 days')::text, now() - interval '3 days 2 hours'),

('5531998234563', 'Simone Alves',
 'Moro no bairro Ressaca em Contagem e a escola estadual do meu filho não tem professor de matemática há 2 meses. As crianças estão ficando sem aula. Isso é inadmissível!',
 now() - interval '5 days 6 hours',
 'Saúde & Educação', 'Zona Leste', 'Urgente', 'Negativo', 'escola sem professor Contagem',
 'em_andamento', 'Contagem', null, now() - interval '5 days 6 hours'),

('5531965432112', 'Wagner Costa',
 'Deputado, a região industrial de Contagem está perdendo fábricas para outros estados. Já fecharam 3 metalúrgicas esse ano. Precisamos de política industrial urgente para manter os empregos aqui.',
 now() - interval '8 days 4 hours',
 'Desenvolvimento Econômico', 'Distrito Industrial', 'Urgente', 'Negativo', 'fábricas fechando Contagem',
 'aberto', 'Contagem', null, now() - interval '8 days 4 hours'),

('5531943217657', 'Eliana Souza',
 'Quero agradecer pelo programa de assistência social que chegou no bairro Nacional em Contagem. Minha família conseguiu cestas básicas e orientação jurídica gratuita. Deus abençoe!',
 now() - interval '11 days',
 'Assistência Social', 'Zona Oeste', 'Positivo', 'Positivo', 'assistência social Nacional Contagem',
 'resolvido', 'Contagem', (now() - interval '10 days')::text, now() - interval '11 days'),

-- ===================== JUIZ DE FORA (5 feedbacks) =====================

('5532987410004', 'Débora Cristina',
 'Sou moradora de Juiz de Fora e quero denunciar a situação caótica da Santa Casa. Faltam leitos, equipamentos e profissionais. Pacientes ficam nos corredores. O deputado precisa intervir!',
 now() - interval '12 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'crise Santa Casa Juiz de Fora',
 'em_andamento', 'Juiz de Fora', null, now() - interval '12 hours'),

('5532976523305', 'Henrique Moreira',
 'O projeto de revitalização da Rua Halfeld em Juiz de Fora ficou lindo! O centro histórico está mais bonito e atraindo turistas. Parabéns pela emenda que viabilizou essa obra.',
 now() - interval '3 days 5 hours',
 'Infraestrutura & Obras', 'Centro', 'Positivo', 'Positivo', 'revitalização Rua Halfeld JF',
 'resolvido', 'Juiz de Fora', (now() - interval '2 days')::text, now() - interval '3 days 5 hours'),

('5532998234564', 'Luana Martins',
 'Moro no bairro Benfica em Juiz de Fora e o assalto à mão armada virou rotina. Meu vizinho foi baleado semana passada. A polícia demora 40 minutos para chegar. Precisamos de mais policiamento!',
 now() - interval '6 days',
 'Segurança Pública', 'Zona Norte', 'Critico', 'Negativo', 'assaltos armados Benfica JF',
 'em_andamento', 'Juiz de Fora', null, now() - interval '6 days'),

('5532965432113', 'Paulo Roberto',
 'O polo tecnológico de Juiz de Fora precisa de mais apoio do Estado. Temos a UFJF formando programadores excelentes mas as empresas vão para SP por falta de incentivo fiscal aqui.',
 now() - interval '9 days 3 hours',
 'Desenvolvimento Econômico', 'Zona Oeste', 'Neutro', 'Neutro', 'incentivo polo tecnológico JF',
 'aberto', 'Juiz de Fora', null, now() - interval '9 days 3 hours'),

('5532943217658', 'Sandra Regina',
 'Quero elogiar o programa de energia solar em escolas públicas de Juiz de Fora. A economia de energia já permitiu investir em material didático novo. Iniciativa brilhante do deputado!',
 now() - interval '12 days',
 'Meio Ambiente', 'Zona Sul', 'Positivo', 'Positivo', 'energia solar escolas JF',
 'resolvido', 'Juiz de Fora', (now() - interval '11 days')::text, now() - interval '12 days'),

-- ===================== BETIM (4 feedbacks) =====================

('5531987410005', 'Sandra Mello',
 'Minha filha sofreu um acidente na ciclovia da zona sul aqui em Betim. A ciclovia está toda quebrada e cheia de buracos. Levou 8 pontos na cabeça. O DER precisa ser acionado urgente!',
 now() - interval '4 hours',
 'Infraestrutura & Obras', 'Zona Sul', 'Critico', 'Negativo', 'ciclovia perigosa acidente Betim',
 'em_andamento', 'Betim', null, now() - interval '4 hours'),

('5531976523306', 'Antônio Carlos',
 'O Distrito Industrial de Betim está em crise. A FIAT reduziu turnos e as empresas fornecedoras estão demitindo em massa. Precisamos de uma audiência pública urgente sobre emprego na região!',
 now() - interval '2 days 6 hours',
 'Desenvolvimento Econômico', 'Distrito Industrial', 'Urgente', 'Negativo', 'crise emprego Betim FIAT',
 'aberto', 'Betim', null, now() - interval '2 days 6 hours'),

('5531998234565', 'Maria José',
 'Sou moradora do bairro PTB em Betim. O esgoto a céu aberto na rua principal causa mau cheiro e doenças. Meus filhos já tiveram dengue 2 vezes. Quando vão resolver o saneamento aqui?',
 now() - interval '6 days 2 hours',
 'Infraestrutura & Obras', 'Zona Norte', 'Urgente', 'Negativo', 'esgoto céu aberto PTB Betim',
 'em_andamento', 'Betim', null, now() - interval '6 days 2 hours'),

('5531965432114', 'Edilson Pereira',
 'O novo centro esportivo inaugurado em Betim com emenda do deputado está sendo muito usado pela comunidade. Cursos de natação gratuitos para crianças. Parabéns pela iniciativa!',
 now() - interval '13 days',
 'Assistência Social', 'Zona Leste', 'Positivo', 'Positivo', 'centro esportivo Betim inaugurado',
 'resolvido', 'Betim', (now() - interval '12 days')::text, now() - interval '13 days'),

-- ===================== MONTES CLAROS (4 feedbacks) =====================

('5538987410006', 'Joana D''arc Souza',
 'Deputado, a seca no norte de Minas está castigando. Aqui em Montes Claros já tem bairro sem água há 3 semanas. A Copasa não resolve. Famílias inteiras dependendo de caminhão-pipa. É desumano!',
 now() - interval '5 hours',
 'Infraestrutura & Obras', 'Zona Norte', 'Critico', 'Negativo', 'falta água Montes Claros seca',
 'em_andamento', 'Montes Claros', null, now() - interval '5 hours'),

('5538976523307', 'Edson Marcelino',
 'O hospital universitário de Montes Claros está com falta de medicamentos básicos. Minha avó diabética não consegue insulina pelo SUS há 1 mês. Isso é emergência de saúde!',
 now() - interval '3 days 7 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'falta medicamentos HU Montes Claros',
 'aberto', 'Montes Claros', null, now() - interval '3 days 7 hours'),

('5538998234566', 'Sebastião Oliveira',
 'Quero agradecer ao deputado pelo projeto de irrigação para pequenos produtores da região de Montes Claros. Minha plantação de manga triplicou a produção. Isso transforma vidas no norte de Minas!',
 now() - interval '7 days 4 hours',
 'Desenvolvimento Econômico', 'Zona Rural', 'Positivo', 'Positivo', 'irrigação produtores Montes Claros',
 'resolvido', 'Montes Claros', (now() - interval '6 days')::text, now() - interval '7 days 4 hours'),

('5538965432115', 'Aparecida Nunes',
 'A creche municipal do bairro Major Prates em Montes Claros está com goteiras e risco de desabamento. Tem 120 crianças estudando ali. Precisa de reforma urgente antes que aconteça uma tragédia!',
 now() - interval '11 days 2 hours',
 'Saúde & Educação', 'Zona Oeste', 'Critico', 'Negativo', 'creche risco desabamento Montes Claros',
 'em_andamento', 'Montes Claros', null, now() - interval '11 days 2 hours'),

-- ===================== GOVERNADOR VALADARES (4 feedbacks) =====================

('5533987410007', 'Wanderley Souza',
 'As enchentes em Governador Valadares destruíram tudo de novo. O Rio Doce transbordou e 500 famílias ficaram desabrigadas. Precisamos de obra de contenção definitiva. Toda vez é a mesma tragédia!',
 now() - interval '1 day 2 hours',
 'Infraestrutura & Obras', 'Centro', 'Critico', 'Negativo', 'enchente Rio Doce Gov Valadares',
 'em_andamento', 'Governador Valadares', null, now() - interval '1 day 2 hours'),

('5533976523308', 'Cristiane Santos',
 'Moro em Governador Valadares e o tráfico de drogas no bairro São Paulo está fora de controle. Tiroteio toda noite. As crianças não podem brincar na rua. Cadê a polícia?',
 now() - interval '4 days 3 hours',
 'Segurança Pública', 'Zona Norte', 'Critico', 'Negativo', 'tráfico drogas Gov Valadares',
 'aberto', 'Governador Valadares', null, now() - interval '4 days 3 hours'),

('5533998234567', 'Michele Ferreira',
 'O curso técnico em enfermagem que o deputado trouxe para Governador Valadares já formou 80 profissionais. Muitos já estão trabalhando no hospital da cidade. Iniciativa que transforma!',
 now() - interval '8 days 5 hours',
 'Desenvolvimento Econômico', 'Centro', 'Positivo', 'Positivo', 'curso técnico enfermagem GV',
 'resolvido', 'Governador Valadares', (now() - interval '7 days')::text, now() - interval '8 days 5 hours'),

('5533965432116', 'Fabiano Motta',
 'O transporte público em Governador Valadares é uma vergonha. Só tem 12 linhas de ônibus para uma cidade de 280 mil habitantes. Tem gente andando 5km para chegar ao trabalho.',
 now() - interval '14 days',
 'Transporte & Mobilidade', 'Zona Oeste', 'Neutro', 'Negativo', 'poucas linhas ônibus GV',
 'aberto', 'Governador Valadares', null, now() - interval '14 days'),

-- ===================== IPATINGA (4 feedbacks) =====================

('5531987410008', 'Geovana Martins',
 'Sou moradora de Ipatinga e quero denunciar a poluição do ar causada pela Usiminas. A poeira de minério está cobrindo as casas do bairro Cariru. Meus filhos têm rinite crônica por causa disso.',
 now() - interval '1 day 5 hours',
 'Meio Ambiente', 'Zona Leste', 'Critico', 'Negativo', 'poluição ar Usiminas Ipatinga',
 'em_andamento', 'Ipatinga', null, now() - interval '1 day 5 hours'),

('5531976523309', 'Leandro Costa',
 'A obra da ponte que liga os bairros Horto e Cidade Nobre em Ipatinga finalmente saiu do papel com a emenda do deputado! Eram 8 anos de espera. A comunidade agradece muito!',
 now() - interval '4 days 6 hours',
 'Infraestrutura & Obras', 'Zona Norte', 'Positivo', 'Positivo', 'ponte Horto Cidade Nobre Ipatinga',
 'resolvido', 'Ipatinga', (now() - interval '3 days')::text, now() - interval '4 days 6 hours'),

('5531998234568', 'Adriana Conceição',
 'A UPA de Ipatinga está com tempo de espera de 8 horas para atendimento. Levei minha filha com febre de 39 graus e tive que esperar a noite inteira. O sistema de saúde está colapsando!',
 now() - interval '7 days 3 hours',
 'Saúde & Educação', 'Centro', 'Urgente', 'Negativo', 'UPA lotada espera 8h Ipatinga',
 'aberto', 'Ipatinga', null, now() - interval '7 days 3 hours'),

('5531965432117', 'Renata Figueiredo',
 'O programa de microcrédito para empreendedores de Ipatinga já beneficiou 150 pequenos negócios. Minha confeitaria cresceu 60% com o financiamento. Obrigada deputado pela iniciativa!',
 now() - interval '15 days',
 'Desenvolvimento Econômico', 'Zona Sul', 'Positivo', 'Positivo', 'microcrédito empreendedores Ipatinga',
 'resolvido', 'Ipatinga', (now() - interval '14 days')::text, now() - interval '15 days'),

-- ===================== UBERABA (3 feedbacks) =====================

('5534987410009', 'Hélio Castilho',
 'A estrada que liga Uberaba a Sacramento está destruída. Caminhões de gado tombam toda semana. Como principal polo pecuário de Minas, precisamos de rodovias decentes!',
 now() - interval '2 days 5 hours',
 'Infraestrutura & Obras', 'Zona Rural', 'Urgente', 'Negativo', 'estrada destruída Uberaba Sacramento',
 'em_andamento', 'Uberaba', null, now() - interval '2 days 5 hours'),

('5534976523310', 'Ivone Cavalcanti',
 'Obrigada deputado! A feira agropecuária de Uberaba recebeu apoio estadual e está gerando empregos temporários para milhares de famílias. O turismo rural está crescendo!',
 now() - interval '6 days 3 hours',
 'Desenvolvimento Econômico', 'Centro', 'Positivo', 'Positivo', 'feira agropecuária Uberaba apoiada',
 'resolvido', 'Uberaba', (now() - interval '5 days')::text, now() - interval '6 days 3 hours'),

('5534998234569', 'Bruno Lacerda',
 'As escolas estaduais de Uberaba estão sem merenda há 1 semana. Meu filho vai à escola e volta com fome. A empresa terceirizada não entregou os alimentos. Isso é crime contra as crianças!',
 now() - interval '10 days 2 hours',
 'Saúde & Educação', 'Zona Norte', 'Critico', 'Negativo', 'escolas sem merenda Uberaba',
 'aberto', 'Uberaba', null, now() - interval '10 days 2 hours'),

-- ===================== RIBEIRÃO DAS NEVES (3 feedbacks) =====================

('5531987410010', 'Sônia Lúcia',
 'Ribeirão das Neves não tem hospital público! A cidade tem 340 mil habitantes e para qualquer emergência temos que ir para BH. Já morreu gente no caminho. Isso é descaso!',
 now() - interval '1 day 8 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'sem hospital público Rib Neves',
 'aberto', 'Ribeirão das Neves', null, now() - interval '1 day 8 hours'),

('5531976523311', 'Dirceu Fonseca',
 'O esgoto a céu aberto no bairro Justinópolis em Ribeirão das Neves é um absurdo. Ratos, baratas e mau cheiro. As crianças brincam perto dessa sujeira. Saneamento básico é direito!',
 now() - interval '5 days 4 hours',
 'Infraestrutura & Obras', 'Zona Norte', 'Urgente', 'Negativo', 'esgoto Justinópolis Rib Neves',
 'em_andamento', 'Ribeirão das Neves', null, now() - interval '5 days 4 hours'),

('5531998234570', 'Vanessa Duarte',
 'O programa Jovem Aprendiz que o deputado trouxe para Ribeirão das Neves já colocou 200 jovens no mercado de trabalho. Meu filho de 18 anos conseguiu o primeiro emprego. Gratidão!',
 now() - interval '12 days 6 hours',
 'Desenvolvimento Econômico', 'Zona Sul', 'Positivo', 'Positivo', 'Jovem Aprendiz Rib Neves',
 'resolvido', 'Ribeirão das Neves', (now() - interval '11 days')::text, now() - interval '12 days 6 hours'),

-- ===================== SETE LAGOAS (3 feedbacks) =====================

('5531987410011', 'Norma Albuquerque',
 'A duplicação da MG-424 entre Sete Lagoas e BH precisa acontecer urgente. Todo dia tem acidente fatal. Perdi meu sobrinho nessa estrada mês passado. Quantas vidas mais vão ser perdidas?',
 now() - interval '2 days 3 hours',
 'Infraestrutura & Obras', 'Zona Rural', 'Critico', 'Negativo', 'duplicação MG-424 Sete Lagoas',
 'em_andamento', 'Sete Lagoas', null, now() - interval '2 days 3 hours'),

('5531976523312', 'Cíntia Barbosa',
 'Parabéns pela aprovação do distrito industrial ampliado em Sete Lagoas! As siderúrgicas da região vão gerar 1.500 empregos diretos. O norte da metropolitana agradece.',
 now() - interval '7 days 2 hours',
 'Desenvolvimento Econômico', 'Distrito Industrial', 'Positivo', 'Positivo', 'distrito industrial Sete Lagoas',
 'resolvido', 'Sete Lagoas', (now() - interval '6 days')::text, now() - interval '7 days 2 hours'),

('5531998234571', 'Emília Corrêa',
 'O CAPS de Sete Lagoas foi fechado por falta de verba. 400 pacientes psiquiátricos ficaram sem atendimento. Meu pai com esquizofrenia não tem onde ser atendido. É uma crise humanitária!',
 now() - interval '13 days 3 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'CAPS fechado Sete Lagoas',
 'aberto', 'Sete Lagoas', null, now() - interval '13 days 3 hours'),

-- ===================== DIVINÓPOLIS (2 feedbacks) =====================

('5537987410012', 'Tiago Mendonça',
 'Sou comerciante em Divinópolis e a concorrência com produtos importados está quebrando o comércio local. O projeto de proteção ao comércio regional que o deputado apresentou precisa ser votado logo!',
 now() - interval '3 days 4 hours',
 'Desenvolvimento Econômico', 'Centro', 'Neutro', 'Negativo', 'comércio local Divinópolis ameaçado',
 'aberto', 'Divinópolis', null, now() - interval '3 days 4 hours'),

('5537976523313', 'Alessandra Vieira',
 'O projeto de arborização urbana em Divinópolis está transformando a cidade! Já plantaram 2.000 árvores nos últimos 6 meses. O clima está mais agradável e a cidade mais bonita.',
 now() - interval '9 days 5 hours',
 'Meio Ambiente', 'Zona Norte', 'Positivo', 'Positivo', 'arborização urbana Divinópolis',
 'resolvido', 'Divinópolis', (now() - interval '8 days')::text, now() - interval '9 days 5 hours'),

-- ===================== SANTA LUZIA (2 feedbacks) =====================

('5531987410013', 'Valdeci Nogueira',
 'Santa Luzia está abandonada pelo Estado. As escolas caindo aos pedaços, sem hospital, ruas destruídas. Temos 230 mil habitantes e somos tratados como cidade fantasma!',
 now() - interval '2 days 7 hours',
 'Infraestrutura & Obras', 'Centro', 'Urgente', 'Negativo', 'abandono geral Santa Luzia',
 'aberto', 'Santa Luzia', null, now() - interval '2 days 7 hours'),

('5531976523314', 'Carla Magalhães',
 'O gabinete itinerante que o deputado fez em Santa Luzia foi excelente. Em um dia resolveram 50 demandas de moradores. CadÚnico, CRAS, orientação jurídica. Façam mais vezes!',
 now() - interval '8 days 6 hours',
 'Assistência Social', 'Zona Norte', 'Positivo', 'Positivo', 'gabinete itinerante Santa Luzia',
 'resolvido', 'Santa Luzia', (now() - interval '7 days')::text, now() - interval '8 days 6 hours'),

-- ===================== POÇOS DE CALDAS (2 feedbacks) =====================

('5535987410014', 'Fábio Santana',
 'O turismo termal de Poços de Caldas precisa de mais investimento do Estado. Os balneários estão deteriorados e os turistas reclamam. É a principal fonte de renda da cidade!',
 now() - interval '4 days 5 hours',
 'Desenvolvimento Econômico', 'Centro', 'Neutro', 'Negativo', 'turismo termal Poços deteriorado',
 'aberto', 'Poços de Caldas', null, now() - interval '4 days 5 hours'),

('5535976523315', 'Marcelo Borba',
 'Parabéns ao deputado pela inclusão de Poços de Caldas na rota turística do circuito das águas de MG. Nossos hotéis tiveram aumento de 30% na ocupação. Turismo gera emprego!',
 now() - interval '11 days 4 hours',
 'Desenvolvimento Econômico', 'Centro', 'Positivo', 'Positivo', 'rota turística Poços de Caldas',
 'resolvido', 'Poços de Caldas', (now() - interval '10 days')::text, now() - interval '11 days 4 hours'),

-- ===================== TEÓFILO OTONI (2 feedbacks) =====================

('5533987410015', 'Gilberto Araújo',
 'Teófilo Otoni está sem médico pediatra no hospital regional há 2 meses. As mães precisam viajar 3 horas até Governador Valadares para atender os filhos. É desumano!',
 now() - interval '1 day 6 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'sem pediatra hospital Teófilo Otoni',
 'em_andamento', 'Teófilo Otoni', null, now() - interval '1 day 6 hours'),

('5533976523316', 'Wagner Santos',
 'A região de Teófilo Otoni precisa de mais investimento em estradas. As vicinais estão intransitáveis e os produtores rurais não conseguem escoar a produção. Prejudica toda a economia do Vale do Mucuri.',
 now() - interval '9 days 6 hours',
 'Infraestrutura & Obras', 'Zona Rural', 'Urgente', 'Negativo', 'estradas vicinais Teófilo Otoni',
 'aberto', 'Teófilo Otoni', null, now() - interval '9 days 6 hours'),

-- ===================== PATOS DE MINAS (2 feedbacks) =====================

('5534987410016', 'Eliana Borges',
 'A Festa do Milho de Patos de Minas é patrimônio cultural e precisa de apoio estadual. Sem verba, o evento pode acabar. São 60 anos de tradição que geram renda para milhares de famílias!',
 now() - interval '5 days 3 hours',
 'Desenvolvimento Econômico', 'Centro', 'Neutro', 'Neutro', 'Festa do Milho Patos de Minas',
 'aberto', 'Patos de Minas', null, now() - interval '5 days 3 hours'),

('5534976523317', 'Maurício Pinheiro',
 'O programa de mecanização agrícola que chegou em Patos de Minas está transformando a produção rural. 80 famílias já foram beneficiadas com tratores e implementos. Obrigado deputado!',
 now() - interval '10 days 5 hours',
 'Desenvolvimento Econômico', 'Zona Rural', 'Positivo', 'Positivo', 'mecanização agrícola Patos de Minas',
 'resolvido', 'Patos de Minas', (now() - interval '9 days')::text, now() - interval '10 days 5 hours'),

-- ===================== POUSO ALEGRE (2 feedbacks) =====================

('5535987410017', 'Ricardo Melo',
 'O polo industrial de Pouso Alegre está crescendo muito mas a infraestrutura não acompanha. Trânsito caótico, falta saneamento nos novos bairros. O crescimento precisa ser planejado!',
 now() - interval '3 days 8 hours',
 'Infraestrutura & Obras', 'Distrito Industrial', 'Neutro', 'Negativo', 'infraestrutura crescimento Pouso Alegre',
 'aberto', 'Pouso Alegre', null, now() - interval '3 days 8 hours'),

('5535976523318', 'Simone Rodrigues',
 'O SENAI de Pouso Alegre está com fila de espera de 1 ano para cursos técnicos. A demanda é enorme mas só tem 200 vagas por semestre. Precisamos ampliar a unidade!',
 now() - interval '8 days 3 hours',
 'Saúde & Educação', 'Centro', 'Neutro', 'Neutro', 'SENAI lotado Pouso Alegre',
 'aberto', 'Pouso Alegre', null, now() - interval '8 days 3 hours'),

-- ===================== BARBACENA (2 feedbacks) =====================

('5532987410018', 'Rodrigo Teixeira',
 'O Hospital Regional de Barbacena está em situação crítica. Equipamentos de raio-X quebrados há 3 meses. Pacientes precisam ir a Juiz de Fora para exames básicos. Absurdo!',
 now() - interval '2 days 4 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'equipamentos quebrados hospital Barbacena',
 'em_andamento', 'Barbacena', null, now() - interval '2 days 4 hours'),

('5532976523319', 'Ana Beatriz',
 'O festival de inverno de Barbacena com apoio do deputado foi um sucesso! Trouxe turistas de todo o estado e movimentou R$2 milhões na economia local em uma semana.',
 now() - interval '14 days 4 hours',
 'Desenvolvimento Econômico', 'Centro', 'Positivo', 'Positivo', 'festival inverno Barbacena sucesso',
 'resolvido', 'Barbacena', (now() - interval '13 days')::text, now() - interval '14 days 4 hours'),

-- ===================== VARGINHA (2 feedbacks) =====================

('5535987410019', 'Daniela Freitas',
 'A segurança em Varginha piorou muito. Os bairros periféricos estão sem policiamento e os assaltos aumentaram 40% esse ano. Precisamos de mais viaturas e efetivo policial!',
 now() - interval '4 days 2 hours',
 'Segurança Pública', 'Zona Norte', 'Urgente', 'Negativo', 'assaltos aumentaram Varginha',
 'em_andamento', 'Varginha', null, now() - interval '4 days 2 hours'),

('5535976523320', 'Gustavo Henrique',
 'O aeroporto de Varginha com a nova rota para São Paulo está trazendo empresários e investimentos para a região. Boa articulação do deputado com a ANAC!',
 now() - interval '11 days 5 hours',
 'Desenvolvimento Econômico', 'Centro', 'Positivo', 'Positivo', 'aeroporto Varginha nova rota',
 'resolvido', 'Varginha', (now() - interval '10 days')::text, now() - interval '11 days 5 hours'),

-- ===================== OURO PRETO (2 feedbacks) =====================

('5531987410020', 'Letícia Campos',
 'O casario histórico de Ouro Preto está desabando por falta de manutenção. Patrimônio da UNESCO sendo destruído! O Estado precisa de um programa emergencial de restauração.',
 now() - interval '3 days 6 hours',
 'Infraestrutura & Obras', 'Centro', 'Critico', 'Negativo', 'casario histórico desabando Ouro Preto',
 'em_andamento', 'Ouro Preto', null, now() - interval '3 days 6 hours'),

('5531976523321', 'Rafael Augusto',
 'O programa de turismo sustentável em Ouro Preto está dando resultado! Os guias locais estão sendo capacitados e a experiência dos turistas melhorou muito. Parabéns ao deputado!',
 now() - interval '12 days 3 hours',
 'Desenvolvimento Econômico', 'Centro', 'Positivo', 'Positivo', 'turismo sustentável Ouro Preto',
 'resolvido', 'Ouro Preto', (now() - interval '11 days')::text, now() - interval '12 days 3 hours'),

-- ===================== CARATINGA (2 feedbacks) =====================

('5533987410021', 'Maria Lúcia Alves',
 'Moro em Caratinga e a ponte sobre o Rio Caratinga está interditada há 6 meses. Os moradores precisam dar uma volta de 20km para ir ao centro. Isso prejudica toda a região!',
 now() - interval '4 days 4 hours',
 'Infraestrutura & Obras', 'Centro', 'Urgente', 'Negativo', 'ponte interditada Caratinga',
 'aberto', 'Caratinga', null, now() - interval '4 days 4 hours'),

('5533976523322', 'José Antônio',
 'O projeto de merenda escolar orgânica que chegou nas escolas de Caratinga é excelente! As crianças estão comendo melhor e os produtores locais estão vendendo mais. Todos ganham!',
 now() - interval '10 days 4 hours',
 'Saúde & Educação', 'Zona Rural', 'Positivo', 'Positivo', 'merenda orgânica Caratinga',
 'resolvido', 'Caratinga', (now() - interval '9 days')::text, now() - interval '10 days 4 hours'),

-- ===================== CORONEL FABRICIANO (2 feedbacks) =====================

('5531987410022', 'Márcia Helena',
 'O bairro Caladão em Coronel Fabriciano está sofrendo com alagamentos constantes. Todo mês de chuva é a mesma tragédia. Já perdi todos os móveis 3 vezes. Precisamos de obra de drenagem!',
 now() - interval '5 days 2 hours',
 'Infraestrutura & Obras', 'Zona Norte', 'Urgente', 'Negativo', 'alagamentos Caladão Cel Fabriciano',
 'em_andamento', 'Coronel Fabriciano', null, now() - interval '5 days 2 hours'),

('5531976523323', 'Lucas Gabriel',
 'O programa de esporte para jovens em Coronel Fabriciano tirou muitos meninos das drogas. Meu filho estava se envolvendo com gente errada e hoje é atleta de vôlei do projeto. Obrigado deputado!',
 now() - interval '15 days 3 hours',
 'Assistência Social', 'Zona Sul', 'Positivo', 'Positivo', 'esporte jovens Cel Fabriciano',
 'resolvido', 'Coronel Fabriciano', (now() - interval '14 days')::text, now() - interval '15 days 3 hours'),

-- ===================== TIMÓTEO (2 feedbacks) =====================

('5531987410023', 'Priscila Mendes',
 'A Aperam em Timóteo está demitindo em massa e a cidade depende dessa empresa. 300 funcionários na rua esse mês. O deputado precisa articular com o governo uma solução para o Vale do Aço!',
 now() - interval '2 days 8 hours',
 'Desenvolvimento Econômico', 'Distrito Industrial', 'Critico', 'Negativo', 'demissões Aperam Timóteo',
 'em_andamento', 'Timóteo', null, now() - interval '2 days 8 hours'),

('5531976523324', 'Anderson Silva',
 'O parque do Cachoeirão em Timóteo ficou lindo depois da revitalização com emenda parlamentar. Área de lazer que a população precisava. As famílias estão aproveitando nos finais de semana!',
 now() - interval '13 days 5 hours',
 'Meio Ambiente', 'Zona Leste', 'Positivo', 'Positivo', 'parque Cachoeirão Timóteo revitalizado',
 'resolvido', 'Timóteo', (now() - interval '12 days')::text, now() - interval '13 days 5 hours'),

-- ===================== CIDADES COM 1 FEEDBACK CADA =====================

-- Muriaé
('5532987410024', 'Cláudio Roberto',
 'A BR-116 na altura de Muriaé é uma das mais perigosas do país. Caminhões sem freio, curvas sem sinalização. Precisamos de radares e obras de segurança viária urgente!',
 now() - interval '6 days 4 hours',
 'Infraestrutura & Obras', 'Zona Rural', 'Critico', 'Negativo', 'BR-116 perigosa Muriaé',
 'em_andamento', 'Muriaé', null, now() - interval '6 days 4 hours'),

-- Conselheiro Lafaiete
('5531987410025', 'Tereza Cristina',
 'O hospital de Conselheiro Lafaiete finalmente recebeu o tomógrafo que o deputado intermediou. Antes tínhamos que ir a BH para fazer exame. Isso salva vidas!',
 now() - interval '7 days 5 hours',
 'Saúde & Educação', 'Centro', 'Positivo', 'Positivo', 'tomógrafo hospital Conselheiro Lafaiete',
 'resolvido', 'Conselheiro Lafaiete', (now() - interval '6 days')::text, now() - interval '7 days 5 hours'),

-- Lavras
('5535987410026', 'Benedito Gonçalves',
 'O campus da UFLA em Lavras precisa de investimento federal para ampliar vagas. A universidade é referência em agropecuária mas tem lista de espera enorme. O deputado pode articular?',
 now() - interval '8 days 2 hours',
 'Saúde & Educação', 'Centro', 'Neutro', 'Neutro', 'ampliação UFLA Lavras',
 'aberto', 'Lavras', null, now() - interval '8 days 2 hours'),

-- Nova Lima
('5531987410027', 'Juliana Andrade',
 'As barragens de mineração próximas a Nova Lima são uma bomba-relógio. Depois de Brumadinho, nenhuma medida efetiva foi tomada. Vivemos com medo! O deputado apoia a fiscalização rigorosa?',
 now() - interval '3 days 3 hours',
 'Meio Ambiente', 'Zona Sul', 'Critico', 'Negativo', 'barragens mineração Nova Lima risco',
 'em_andamento', 'Nova Lima', null, now() - interval '3 days 3 hours'),

-- Sabará
('5531987410028', 'Osvaldo Reis',
 'O centro histórico de Sabará está se deteriorando. Igrejas barrocas com infiltração, casarões desabando. Precisamos de verba estadual para preservação do patrimônio!',
 now() - interval '9 days 4 hours',
 'Infraestrutura & Obras', 'Centro', 'Neutro', 'Negativo', 'patrimônio histórico Sabará deteriorando',
 'aberto', 'Sabará', null, now() - interval '9 days 4 hours'),

-- Itabira
('5531987410029', 'Carmem Lúcia',
 'Itabira sofre com o desemprego após a redução das operações da Vale. O deputado pode articular alternativas econômicas para a cidade? Dependemos da mineração há 80 anos.',
 now() - interval '4 days 7 hours',
 'Desenvolvimento Econômico', 'Centro', 'Urgente', 'Negativo', 'desemprego mineração Itabira',
 'aberto', 'Itabira', null, now() - interval '4 days 7 hours'),

-- João Monlevade
('5531987410030', 'Edivaldo Correia',
 'A ArcelorMittal em João Monlevade está poluindo o Rio Piracicaba sem punição. A água que abastece a cidade está contaminada. Precisamos de fiscalização ambiental rigorosa!',
 now() - interval '6 days 6 hours',
 'Meio Ambiente', 'Distrito Industrial', 'Critico', 'Negativo', 'poluição Rio Piracicaba João Monlevade',
 'em_andamento', 'João Monlevade', null, now() - interval '6 days 6 hours'),

-- Araguari
('5534987410031', 'Rosângela Dias',
 'O tomate de Araguari está perdendo mercado por falta de apoio logístico. Somos o maior produtor de tomate de MG mas a estrada para escoar a produção é péssima!',
 now() - interval '7 days 6 hours',
 'Desenvolvimento Econômico', 'Zona Rural', 'Neutro', 'Negativo', 'logística tomate Araguari',
 'aberto', 'Araguari', null, now() - interval '7 days 6 hours'),

-- Passos
('5535987410032', 'Geraldo Neto',
 'Parabéns ao deputado pelo projeto de energia renovável que chegou em Passos! A usina solar está gerando emprego e energia limpa para 5 mil famílias. Sudoeste de Minas agradece!',
 now() - interval '10 days 6 hours',
 'Meio Ambiente', 'Zona Rural', 'Positivo', 'Positivo', 'usina solar Passos',
 'resolvido', 'Passos', (now() - interval '9 days')::text, now() - interval '10 days 6 hours'),

-- Viçosa
('5531987410033', 'Renato Barbosa',
 'A UFV em Viçosa está com corte de 40% no orçamento. Pesquisas agropecuárias que alimentam Minas inteira estão parando. O deputado pode pressionar por mais recursos federais?',
 now() - interval '5 days 5 hours',
 'Saúde & Educação', 'Centro', 'Urgente', 'Negativo', 'corte orçamento UFV Viçosa',
 'aberto', 'Viçosa', null, now() - interval '5 days 5 hours'),

-- Ituiutaba
('5534987410034', 'Sebastiana Lopes',
 'O hospital público de Ituiutaba precisa de mais leitos de UTI. Tem apenas 10 para uma região de 100 mil habitantes. Pacientes graves são transferidos para Uberlândia. Muitos não resistem ao trajeto.',
 now() - interval '8 days 7 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'falta UTI hospital Ituiutaba',
 'em_andamento', 'Ituiutaba', null, now() - interval '8 days 7 hours'),

-- Alfenas
('5535987410035', 'Matheus Ferreira',
 'O café especial de Alfenas ganhou prêmio internacional mas os produtores não conseguem certificação por falta de apoio do Estado. Temos o melhor café do Brasil e ninguém sabe!',
 now() - interval '6 days 5 hours',
 'Desenvolvimento Econômico', 'Zona Rural', 'Neutro', 'Neutro', 'café especial Alfenas sem apoio',
 'aberto', 'Alfenas', null, now() - interval '6 days 5 hours'),

-- Manhuaçu
('5533987410036', 'Conceição Moreira',
 'As estradas rurais de Manhuaçu estão destruídas. Os cafeicultores perdem toneladas de café porque os caminhões não conseguem passar. Região do café sem infraestrutura é um contrassenso!',
 now() - interval '5 days 7 hours',
 'Infraestrutura & Obras', 'Zona Rural', 'Urgente', 'Negativo', 'estradas rurais Manhuaçu café',
 'aberto', 'Manhuaçu', null, now() - interval '5 days 7 hours'),

-- Paracatu
('5538987410037', 'Joaquim Pereira',
 'A mineradora Kinross em Paracatu está expandindo sem consultar a comunidade. Bairros inteiros estão sendo afetados pela poeira e vibração das explosões. Cadê a fiscalização ambiental?',
 now() - interval '4 days 8 hours',
 'Meio Ambiente', 'Zona Norte', 'Critico', 'Negativo', 'mineração Kinross Paracatu impacto',
 'em_andamento', 'Paracatu', null, now() - interval '4 days 8 hours'),

-- Formiga
('5537987410038', 'Neusa Aparecida',
 'A escola estadual de Formiga recebeu equipamentos de informática novos graças à emenda do deputado. Nossos alunos agora têm acesso a computadores e internet. Educação de qualidade!',
 now() - interval '11 days 6 hours',
 'Saúde & Educação', 'Centro', 'Positivo', 'Positivo', 'computadores escola Formiga',
 'resolvido', 'Formiga', (now() - interval '10 days')::text, now() - interval '11 days 6 hours'),

-- Araxá
('5534987410039', 'Cláudio Henrique',
 'O complexo termal de Araxá precisa de restauração urgente. O Grande Hotel está deteriorado e perde turistas. Com investimento adequado, Araxá pode ser referência em turismo de saúde no Brasil!',
 now() - interval '7 days 7 hours',
 'Desenvolvimento Econômico', 'Centro', 'Neutro', 'Neutro', 'turismo termal Araxá restauração',
 'aberto', 'Araxá', null, now() - interval '7 days 7 hours'),

-- Itajubá
('5535987410040', 'Carolina Braga',
 'A UNIFEI em Itajubá está desenvolvendo tecnologia de drones para agricultura. Com mais verba, esse projeto pode revolucionar a produção rural de Minas. O deputado pode articular apoio?',
 now() - interval '9 days 2 hours',
 'Desenvolvimento Econômico', 'Centro', 'Neutro', 'Positivo', 'tecnologia drones UNIFEI Itajubá',
 'aberto', 'Itajubá', null, now() - interval '9 days 2 hours'),

-- São João del-Rei
('5532987410041', 'Helena Magalhães',
 'O patrimônio histórico de São João del-Rei está sendo vandalizado. Igrejas pichadas, museus fechados. Precisamos de programa de educação patrimonial e mais vigilância!',
 now() - interval '6 days 8 hours',
 'Infraestrutura & Obras', 'Centro', 'Urgente', 'Negativo', 'vandalismo patrimônio São João del-Rei',
 'aberto', 'São João del-Rei', null, now() - interval '6 days 8 hours'),

-- Leopoldina
('5532987410042', 'Milton Santos',
 'O programa de coleta seletiva implantado em Leopoldina com apoio do deputado é exemplo para toda a Zona da Mata. 70% do lixo já é reciclado. Meio ambiente agradece!',
 now() - interval '13 days 6 hours',
 'Meio Ambiente', 'Centro', 'Positivo', 'Positivo', 'coleta seletiva Leopoldina sucesso',
 'resolvido', 'Leopoldina', (now() - interval '12 days')::text, now() - interval '13 days 6 hours'),

-- Curvelo
('5538987410043', 'Raimunda Silva',
 'Curvelo precisa de mais médicos no SUS. A UBS do meu bairro atende 15 mil pessoas com apenas 1 médico. Filas enormes, gente passando mal esperando. Isso não é saúde pública!',
 now() - interval '3 days 9 hours',
 'Saúde & Educação', 'Zona Norte', 'Urgente', 'Negativo', 'falta médicos UBS Curvelo',
 'aberto', 'Curvelo', null, now() - interval '3 days 9 hours'),

-- Januária
('5538987410044', 'Francisco das Chagas',
 'A seca no norte de Minas está matando o gado em Januária. Perdemos 40% do rebanho esse ano. Precisamos de programa emergencial de distribuição de água e ração. É questão de sobrevivência!',
 now() - interval '2 days 9 hours',
 'Assistência Social', 'Zona Rural', 'Critico', 'Negativo', 'seca mata gado Januária',
 'em_andamento', 'Januária', null, now() - interval '2 days 9 hours'),

-- Janaúba
('5538987410045', 'Dalila Oliveira',
 'A creche municipal de Janaúba que pegou fogo em 2017 ainda não foi totalmente reconstruída. As famílias das vítimas ainda esperam por justiça. O deputado pode cobrar celeridade?',
 now() - interval '8 days 8 hours',
 'Saúde & Educação', 'Centro', 'Critico', 'Negativo', 'reconstrução creche Janaúba',
 'aberto', 'Janaúba', null, now() - interval '8 days 8 hours'),

-- Patrocínio
('5534987410046', 'Geraldo Nunes',
 'Patrocínio é a capital do café mas os produtores estão endividados por causa do câmbio desfavorável. Precisamos de política de preço mínimo eficiente para salvar a cafeicultura mineira.',
 now() - interval '5 days 8 hours',
 'Desenvolvimento Econômico', 'Zona Rural', 'Neutro', 'Negativo', 'cafeicultores endividados Patrocínio',
 'aberto', 'Patrocínio', null, now() - interval '5 days 8 hours'),

-- Itaúna
('5537987410047', 'Marta Rodrigues',
 'O programa cultural que o deputado trouxe para Itaúna está transformando jovens. Oficinas de teatro, música e dança tirando meninos da rua. Cultura salva vidas!',
 now() - interval '14 days 6 hours',
 'Assistência Social', 'Centro', 'Positivo', 'Positivo', 'programa cultural jovens Itaúna',
 'resolvido', 'Itaúna', (now() - interval '13 days')::text, now() - interval '14 days 6 hours'),

-- Lagoa Santa
('5531987410048', 'Renato Vieira',
 'O aeroporto de Confins trouxe progresso para Lagoa Santa mas também trouxe problemas. O barulho dos aviões está afetando a saúde dos moradores. Precisamos de zona de amortecimento acústico!',
 now() - interval '7 days 8 hours',
 'Meio Ambiente', 'Zona Norte', 'Neutro', 'Negativo', 'barulho aviões Lagoa Santa',
 'aberto', 'Lagoa Santa', null, now() - interval '7 days 8 hours'),

-- Pedro Leopoldo
('5531987410049', 'Angélica Souza',
 'A água de Pedro Leopoldo está com gosto ruim há semanas. A Copasa diz que é normal mas os moradores estão preocupados. Precisamos de análise independente da qualidade da água!',
 now() - interval '4 days 9 hours',
 'Meio Ambiente', 'Centro', 'Urgente', 'Negativo', 'qualidade água Pedro Leopoldo',
 'em_andamento', 'Pedro Leopoldo', null, now() - interval '4 days 9 hours'),

-- Vespasiano
('5531987410050', 'Luís Fernando',
 'Vespasiano precisa de uma delegacia de polícia civil própria. Compartilhamos delegacia com Lagoa Santa e o atendimento é precário. 120 mil habitantes sem delegacia é absurdo!',
 now() - interval '6 days 9 hours',
 'Segurança Pública', 'Centro', 'Urgente', 'Negativo', 'sem delegacia própria Vespasiano',
 'aberto', 'Vespasiano', null, now() - interval '6 days 9 hours'),

-- ===================== FEEDBACKS ADICIONAIS PARA CIDADES GRANDES =====================

-- Belo Horizonte (extras)
('5531911111101', 'Fernanda Moreira',
 'O metrô de Belo Horizonte tem apenas uma linha! Uma cidade de 2,5 milhões de habitantes merece transporte sobre trilhos decente. O projeto de expansão já foi engavetado 5 vezes.',
 now() - interval '7 days 4 hours',
 'Transporte & Mobilidade', 'Centro', 'Neutro', 'Negativo', 'expansão metrô BH engavetada',
 'aberto', 'Belo Horizonte', null, now() - interval '7 days 4 hours'),

('5531911111102', 'Antônio Marcos',
 'A ocupação irregular na Serra do Curral em BH está destruindo nascentes de água. Se nada for feito, BH vai enfrentar crise hídrica em 5 anos. Meio ambiente é prioridade!',
 now() - interval '9 days 3 hours',
 'Meio Ambiente', 'Zona Sul', 'Critico', 'Negativo', 'ocupação irregular Serra Curral BH',
 'em_andamento', 'Belo Horizonte', null, now() - interval '9 days 3 hours'),

-- Uberlândia (extras)
('5534911111103', 'Raquel Santos',
 'As creches públicas de Uberlândia têm fila de espera de 2 anos. Sou mãe solo e não consigo trabalhar porque não tenho onde deixar meu filho de 2 anos. Precisamos de mais vagas!',
 now() - interval '4 days 4 hours',
 'Saúde & Educação', 'Zona Oeste', 'Urgente', 'Negativo', 'fila creches 2 anos Uberlândia',
 'aberto', 'Uberlândia', null, now() - interval '4 days 4 hours'),

-- Contagem (extras)
('5531911111104', 'Douglas Oliveira',
 'O programa de regularização fundiária que chegou em Contagem está legalizando 500 casas no bairro Sapucaias. Depois de 20 anos, finalmente vamos ter escritura! Obrigado deputado!',
 now() - interval '6 days 7 hours',
 'Assistência Social', 'Zona Sul', 'Positivo', 'Positivo', 'regularização fundiária Contagem',
 'resolvido', 'Contagem', (now() - interval '5 days')::text, now() - interval '6 days 7 hours'),

-- Juiz de Fora (extras)
('5532911111105', 'Patrícia Lima',
 'O transporte público de Juiz de Fora é caríssimo e péssimo. Ônibus lotados, horários irregulares e tarifa de R$5,50. Uma das mais caras do estado para o pior serviço.',
 now() - interval '5 days 3 hours',
 'Transporte & Mobilidade', 'Zona Norte', 'Neutro', 'Negativo', 'transporte caro péssimo JF',
 'aberto', 'Juiz de Fora', null, now() - interval '5 days 3 hours'),

-- Gov. Valadares (extras)
('5533911111106', 'Lourdes Aparecida',
 'O programa de recuperação do Rio Doce em Governador Valadares após o desastre de Mariana está parado. A água ainda não é segura para consumo. Quando vamos ter nosso rio de volta?',
 now() - interval '3 days 4 hours',
 'Meio Ambiente', 'Centro', 'Critico', 'Negativo', 'recuperação Rio Doce GV parada',
 'em_andamento', 'Governador Valadares', null, now() - interval '3 days 4 hours'),

-- Ipatinga (extras)
('5531911111107', 'Thiago Pereira',
 'O projeto de ciclovias em Ipatinga que o deputado apoiou ficou excelente! 15km de ciclovias conectando os bairros ao centro. Qualidade de vida para os moradores. Parabéns!',
 now() - interval '11 days 4 hours',
 'Transporte & Mobilidade', 'Centro', 'Positivo', 'Positivo', 'ciclovias Ipatinga aprovadas',
 'resolvido', 'Ipatinga', (now() - interval '10 days')::text, now() - interval '11 days 4 hours'),

-- Montes Claros (extras)
('5538911111108', 'Francisca Oliveira',
 'O programa Bolsa Atleta do Estado que chegou em Montes Claros está revelando talentos. 3 jovens da cidade foram selecionados para a seleção mineira de atletismo. Esporte transforma!',
 now() - interval '12 days 5 hours',
 'Assistência Social', 'Zona Leste', 'Positivo', 'Positivo', 'Bolsa Atleta Montes Claros',
 'resolvido', 'Montes Claros', (now() - interval '11 days')::text, now() - interval '12 days 5 hours'),

-- Sete Lagoas (extra)
('5531911111109', 'Pedro Paulo',
 'A criminalidade em Sete Lagoas aumentou 60% nos últimos 2 anos. Os jovens estão sendo recrutados pelo tráfico por falta de oportunidade. Precisamos de políticas públicas urgentes para a juventude!',
 now() - interval '3 days 2 hours',
 'Segurança Pública', 'Zona Norte', 'Urgente', 'Negativo', 'criminalidade jovens Sete Lagoas',
 'em_andamento', 'Sete Lagoas', null, now() - interval '3 days 2 hours'),

-- Betim (extra)
('5531911111110', 'Claudete Ferreira',
 'O programa de horta comunitária em Betim está alimentando 200 famílias. Iniciativa simples mas que faz diferença enorme. Minha família economiza R$300 por mês em verduras!',
 now() - interval '9 days 6 hours',
 'Assistência Social', 'Zona Norte', 'Positivo', 'Positivo', 'horta comunitária Betim',
 'resolvido', 'Betim', (now() - interval '8 days')::text, now() - interval '9 days 6 hours'),

-- Uberaba (extra)
('5534911111111', 'Wilson Guimarães',
 'O transporte intermunicipal entre Uberaba e Uberlândia precisa de mais horários. São apenas 4 ônibus por dia para atender milhares de estudantes e trabalhadores. Absurdo!',
 now() - interval '6 days 2 hours',
 'Transporte & Mobilidade', 'Centro', 'Neutro', 'Negativo', 'transporte intermunicipal Uberaba',
 'aberto', 'Uberaba', null, now() - interval '6 days 2 hours'),

-- Ribeirão das Neves (extra)
('5531911111112', 'Jéssica Almeida',
 'Sou professora em Ribeirão das Neves e as escolas estaduais estão sem material básico. Sem giz, sem papel, sem toner para impressora. Os professores tiram do próprio bolso. Até quando?',
 now() - interval '4 days 6 hours',
 'Saúde & Educação', 'Zona Norte', 'Urgente', 'Negativo', 'escolas sem material Rib Neves',
 'aberto', 'Ribeirão das Neves', null, now() - interval '4 days 6 hours'),

-- Divinópolis (extra)
('5537911111113', 'Ronaldo Braga',
 'O polo moveleiro de Divinópolis precisa de apoio para exportação. Temos qualidade para competir internacionalmente mas falta capacitação em comércio exterior e logística.',
 now() - interval '10 days 3 hours',
 'Desenvolvimento Econômico', 'Distrito Industrial', 'Neutro', 'Neutro', 'polo moveleiro Divinópolis exportação',
 'aberto', 'Divinópolis', null, now() - interval '10 days 3 hours'),

-- Santa Luzia (extra)
('5531911111114', 'Michele Rodrigues',
 'A BR-381 que corta Santa Luzia é conhecida como "Rodovia da Morte". Acidentes diários, sem acostamento, sem iluminação. Quantas mortes mais para tomarem providência?',
 now() - interval '1 day 9 hours',
 'Infraestrutura & Obras', 'Zona Rural', 'Critico', 'Negativo', 'BR-381 Rodovia Morte Santa Luzia',
 'em_andamento', 'Santa Luzia', null, now() - interval '1 day 9 hours'),

-- Extras variados para volume

('5531911111115', 'Amanda Cristina',
 'Sou moradora do bairro Venda Nova em Belo Horizonte. O esgoto está transbordando na rua há 1 semana. Já liguei na Copasa 5 vezes e nada foi feito. Crianças brincam nessa água contaminada!',
 now() - interval '14 hours',
 'Infraestrutura & Obras', 'Zona Norte', 'Critico', 'Negativo', 'esgoto transbordando Venda Nova BH',
 'aberto', 'Belo Horizonte', null, now() - interval '14 hours'),

('5534911111116', 'Márcio Henrique',
 'O projeto de inclusão digital que chegou nas escolas rurais de Uberlândia é fantástico! 20 escolas receberam laboratórios de informática. As crianças do campo agora têm acesso ao mundo digital.',
 now() - interval '12 days 4 hours',
 'Saúde & Educação', 'Zona Rural', 'Positivo', 'Positivo', 'inclusão digital rural Uberlândia',
 'resolvido', 'Uberlândia', (now() - interval '11 days')::text, now() - interval '12 days 4 hours'),

('5531911111117', 'Débora Souza',
 'Contagem precisa de mais creches! Estou na fila há 1 ano e meio para conseguir vaga para minha filha. Sem creche não consigo trabalhar. É um ciclo vicioso de pobreza.',
 now() - interval '9 days 4 hours',
 'Saúde & Educação', 'Zona Leste', 'Urgente', 'Negativo', 'fila creche 1 ano Contagem',
 'aberto', 'Contagem', null, now() - interval '9 days 4 hours'),

('5532911111118', 'Henrique Bastos',
 'O corredor verde que foi implantado na zona sul de Juiz de Fora melhorou muito a qualidade do ar. Árvores frutíferas nas calçadas, jardins nos canteiros. Cidade mais humana!',
 now() - interval '15 days 4 hours',
 'Meio Ambiente', 'Zona Sul', 'Positivo', 'Positivo', 'corredor verde Juiz de Fora',
 'resolvido', 'Juiz de Fora', (now() - interval '14 days')::text, now() - interval '15 days 4 hours'),

('5531911111119', 'Elisa Campos',
 'O bairro Citrolândia em Betim não tem posto de saúde. 30 mil moradores sem atendimento básico. Precisamos ir até a sede do município para uma consulta simples. É desumano!',
 now() - interval '8 days 4 hours',
 'Saúde & Educação', 'Zona Oeste', 'Urgente', 'Negativo', 'sem posto saúde Citrolândia Betim',
 'aberto', 'Betim', null, now() - interval '8 days 4 hours'),

('5538911111120', 'Josefa Maria',
 'Moro em Montes Claros e o programa de cisternas que o deputado trouxe para o norte de Minas salvou nossa comunidade. 50 famílias agora têm água para beber e cozinhar. Simples e eficiente!',
 now() - interval '16 days',
 'Infraestrutura & Obras', 'Zona Rural', 'Positivo', 'Positivo', 'cisternas norte Minas Montes Claros',
 'resolvido', 'Montes Claros', (now() - interval '15 days')::text, now() - interval '16 days');
