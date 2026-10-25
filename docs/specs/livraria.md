# Especificação da livraria

Este documento é a fonte única de verdade para o domínio, a API, a interface
e os testes. O objetivo é ajudar clientes a planejar e aproveitar a visita à
livraria física. O aplicativo não realiza pagamentos ou vendas online.

## Arquitetura e limites

- Apresentação: `controllers/`, `templates/` e `static/`; HTTP, sessão e interface.
- Aplicação: `services/`; coordenação dos casos de uso e operações atômicas.
- Domínio: `domain/`; regras de datas, quantidades, reservas, preferências e avaliações.
- Infraestrutura: `repositories/`; armazenamento e consultas dos dados em memória.
- `app.py` e `demonstracao.py`: configuração, composição e dados iniciais ilustrativos.
- `livraria.py` e `models/`: compatibilidade com os imports públicos anteriores.
- `test_livraria.py`: testes unitários, integração HTTP e cenários BDD extraídos
  diretamente do bloco Gherkin deste documento.
- `docs/specs/tasks.md`: plano e registro da execução.
- [Arquitetura multicamadas](../arquitetura.md): responsabilidades e fluxo da aplicação.
- Python 3.10 ou superior; dependências declaradas em `requirements.txt`.
- Os dados ficam em memória e são reiniciados com o servidor. O catálogo,
  compras, cupons, horários e eventos iniciais são exemplos demonstrativos.
- Cada navegador recebe uma sessão própria. Não há cadastro, senha ou
  integração com um sistema de caixa, pois essas funcionalidades não foram
  solicitadas. A sessão não constitui autenticação para uso em produção.
- Notificações são exibidas no aplicativo. Reposição, separação de reservas,
  compras e concessão de cupons são entradas da loja no serviço de domínio;
  não são comandos administrativos disponíveis aos clientes na API.
- A leitura pela câmera usa `BarcodeDetector` quando disponível; entrada
  manual ou leitor USB permite consultar o mesmo código sem câmera.

## Decisões para requisitos sem política comercial definida

Estas decisões tornam as histórias verificáveis sem criar taxas ou limites:

1. Título e autor aceitam busca parcial sem diferenciar maiúsculas/minúsculas.
   O filtro de gênero usa correspondência completa, também sem diferenciar
   maiúsculas/minúsculas. Uma busca sem resultado devolve uma lista vazia.
   A função `filtrar_livros(livros, **criterios)` preserva a correspondência
   exata e a combinação de critérios do exemplo de TDD.
2. A loja identifica os lançamentos da semana com o campo `lancamento`, como
   no exemplo de BDD. Não é inferida uma data de publicação de livros antigos.
3. Recomendações mostram livros ainda não comprados dos gêneros das compras
   anteriores e das preferências explícitas. Sem esses dados, a lista fica
   vazia. Não há ranking, desconto ou recomendação aleatória.
4. Uma reserva separa um exemplar: reduz a disponibilidade em uma unidade.
   Não é possível reservar estoque zero. O cliente informa um prazo futuro;
   não há limite comercial de prazo ou de reservas. Cancelar devolve o
   exemplar uma única vez. Reservas canceladas não podem ficar prontas.
   Não há cancelamento automático por prazo ou cobrança de embrulho.
5. A reserva fica `pendente` até a loja informar a separação, quando passa a
   `pronta` e produz uma notificação. O embrulho é uma escolha booleana da
   própria reserva. O cliente pode alterar o prazo de uma reserva ativa.
6. O sistema recebe pontos e eventual validade junto ao registro da compra
   física; não calcula uma taxa de conversão. O saldo soma créditos ainda
   válidos. A data de aviso de expiração também é informada pela loja.
   Os cupons exibem os termos fornecidos, sem inventar validade ou percentual.
   O cartão digital exibe o identificador do cliente, sem QR obrigatório.
7. Horários de atendimento são disponibilizados pela loja; um horário ocupado
   não é oferecido a outro cliente. A fila informa a posição na ordem de
   entrada e mantém uma única entrada ativa por cliente. Lotação e horário
   de funcionamento são valores informados, sem estimativa de espera.
8. Eventos possuem data, local e, quando fornecida, capacidade. Inscrição é
   única por cliente/evento e respeita as vagas informadas. Sem capacidade
   informada, não é inventado um limite. A loja fornece `lembrar_em`; não
   existe uma antecedência fixa presumida para lembretes.
9. Clube de leitura permite adesão e publicação de opiniões identificadas
   pelo cliente. Avaliações de livros podem ser consultadas e publicadas
   conforme as regras da E1-08. A lista de desejos não duplica livros.
10. As preferências de notificação usam temas `estoque`, `reservas`,
    `fidelidade` e `eventos`. `None` significa todos; uma lista vazia significa
    nenhum. Avisos são gerados uma vez e seguem a escolha vigente no momento
    do envio. Lembretes são processados quando o app consulta o estado,
    incluindo a atualização periódica da página enquanto estiver aberta.
11. Identificadores inexistentes, datas inválidas, quantidades negativas e
    dados malformados produzem erro legível sem alterar o estado. Um cliente
    só acessa suas reservas, histórico, pontos, lista e notificações.
    As alterações de estoque são atômicas dentro do processo do servidor.
12. Avaliações de livros exigem nota inteira de 1 a 5 e comentário não vazio.
    Cada cliente, identificado pela sessão, pode publicar uma vez por livro,
    sem edição ou exclusão. A publicação é pública, mas não contém o identificador
    bruto da sessão. Avaliações ilustrativas antigas permanecem sem nota.
    Não há exigência de compra prévia. Publicações simultâneas do mesmo cliente
    não geram duplicação. O comentário é exibido como texto, sem executar HTML.

## User Stories

### E1 — Descoberta e disponibilidade de livros

- **E1-01:** Como cliente da livraria, eu quero buscar um livro pelo título ou autor no app para saber se ele está disponível antes de ir até a loja.
- **E1-02:** Como cliente da livraria, eu quero ver a quantidade de exemplares disponíveis em estoque para saber se vale a pena ir à loja hoje.
- **E1-03:** Como cliente da livraria, eu quero filtrar livros por gênero/categoria no app para descobrir opções dentro do meu interesse.
- **E1-04:** Como cliente da livraria, eu quero ver os lançamentos da semana no app para me manter atualizada sobre novidades.
- **E1-05:** Como cliente da livraria, eu quero receber uma notificação quando um livro esgotado voltar ao estoque para não perder a chance de comprá-lo.
- **E1-06:** Como cliente da livraria, eu quero ver recomendações personalizadas com base nas minhas compras anteriores para descobrir novos livros do meu interesse.
- **E1-07:** Como cliente da livraria, eu quero ler avaliações de outros clientes sobre um livro para decidir se quero comprá-lo.
- **E1-08:** Como cliente da livraria, eu quero publicar uma avaliação de livro com nota e comentário para compartilhar minha experiência com outros leitores.

### E2 — Localização e experiência na loja

- **E2-01:** Como cliente da livraria, eu quero ver em qual seção/prateleira um livro está localizado para encontrá-lo rapidamente dentro da loja.
- **E2-02:** Como cliente da livraria, eu quero escanear o código de barras de um livro na loja para ver mais informações sobre ele (sinopse, avaliações, preço).
- **E2-03:** Como cliente da livraria, eu quero entrar em uma fila virtual pelo app ao chegar na loja para não precisar esperar em pé no caixa.
- **E2-04:** Como cliente da livraria, eu quero agendar um horário de atendimento com um livreiro especializado para receber recomendações personalizadas.
- **E2-05:** Como cliente da livraria, eu quero ver o horário de funcionamento e a lotação atual da loja para escolher o melhor momento de visitar.

### E3 — Reserva e retirada

- **E3-01:** Como cliente da livraria, eu quero reservar um livro pelo app para garantir que ele esteja separado quando eu chegar à loja.
- **E3-02:** Como cliente da livraria, eu quero definir um prazo de retirada da reserva para não perder o livro caso eu me atrase.
- **E3-03:** Como cliente da livraria, eu quero receber uma notificação quando minha reserva estiver pronta para retirada para saber o momento certo de ir à loja.
- **E3-04:** Como cliente da livraria, eu quero cancelar uma reserva pelo app caso eu mude de ideia.

### E4 — Fidelidade e recompensas

- **E4-01:** Como cliente da livraria, eu quero acumular pontos de fidelidade a cada compra na loja física para trocar por descontos futuros.
- **E4-02:** Como cliente da livraria, eu quero ver meu saldo de pontos de fidelidade no app para acompanhar meus benefícios.
- **E4-03:** Como cliente da livraria, eu quero receber cupons de desconto exclusivos para usar na loja física.
- **E4-04:** Como cliente da livraria, eu quero apresentar meu cartão fidelidade digital no caixa para não precisar carregar um cartão físico.
- **E4-05:** Como cliente da livraria, eu quero ser avisada quando meus pontos estiverem prestes a expirar para não perder os benefícios.

### E5 — Eventos e comunidade

- **E5-01:** Como cliente da livraria, eu quero ver a agenda de eventos da loja (bate-papos com autores, clubes de leitura) para participar dos que me interessam.
- **E5-02:** Como cliente da livraria, eu quero me inscrever em um evento pelo app para garantir minha vaga.
- **E5-03:** Como cliente da livraria, eu quero receber uma notificação de lembrete antes de um evento em que me inscrevi para não esquecer de comparecer.
- **E5-04:** Como cliente da livraria, eu quero participar de um clube de leitura vinculado à loja para trocar opiniões sobre livros com outros clientes.

### E6 — Conta, preferências e histórico

- **E6-01:** Como cliente da livraria, eu quero criar uma lista de desejos no app para guardar livros que quero comprar depois.
- **E6-02:** Como cliente da livraria, eu quero ver meu histórico de compras feitas na loja física para lembrar quais livros já comprei.
- **E6-03:** Como cliente da livraria, eu quero configurar minhas preferências de gênero literário para receber recomendações mais relevantes.
- **E6-04:** Como cliente da livraria, eu quero optar por receber notificações apenas sobre os temas do meu interesse para não ser incomodada com avisos irrelevantes.
- **E6-05:** Como cliente da livraria, eu quero adicionar um livro como presente com embrulho especial, reservando-o para retirada na loja, para agilizar a compra de presentes.

## Critérios de aceite executáveis

O catálogo dos cenários contém `1984` (George Orwell, Distopia, estoque 3),
`A Revolução dos Bichos` (George Orwell, Distopia, estoque 2), `O Hobbit`
(J.R.R. Tolkien, Fantasia, estoque 5), `O Novo Reino` (Ana Silva, Fantasia,
estoque 4 e lançamento) e `Livro Esgotado` (estoque 0).
O relógio dos testes é fixado em 27/09/2026 às 12:00 UTC.

```gherkin
Feature: Visitar e aproveitar a livraria física
  Como cliente da livraria
  Quero consultar livros e organizar minha visita
  Para aproveitar os serviços da loja física

  Background:
    Given que existem livros cadastrados no catálogo
    And que sou a cliente "ana"

  @E1-01
  Scenario: Buscar um livro existente pelo título
    When eu buscar pelo título "1984"
    Then o livro "1984" deve ser retornado

  @E1-01
  Scenario: Buscar livros pelo autor
    When eu buscar pelo autor "George Orwell"
    Then devem ser retornados 2 livros

  @E1-01
  Scenario: Buscar um livro inexistente
    When eu buscar pelo título "Livro Inexistente"
    Then nenhum livro deve ser retornado

  @E1-02
  Scenario: Consultar quantidade disponível em estoque
    When eu consultar a disponibilidade do livro "1984"
    Then devem ser informados 3 exemplares disponíveis

  @E1-03
  Scenario: Filtrar livros por gênero
    When eu filtrar os livros pelo gênero "Fantasia"
    Then devem ser retornados apenas livros do gênero "Fantasia"

  @E1-04
  Scenario: Consultar lançamentos da semana
    When eu consultar os lançamentos da semana
    Then deve ser retornado 1 lançamento

  @E1-05
  Scenario: Avisar quando um livro voltar ao estoque
    Given que acompanho a reposição de "Livro Esgotado"
    When a loja repuser 2 exemplares de "Livro Esgotado"
    Then devo receber uma notificação do tema "estoque"

  @E1-06
  Scenario: Recomendar livros com base nas compras anteriores
    Given que comprei "1984" e recebi 20 pontos
    When eu consultar minhas recomendações
    Then o livro "A Revolução dos Bichos" deve ser retornado
    And o livro "1984" não deve ser retornado

  @E1-07
  Scenario: Ler avaliações de outros clientes
    When eu consultar os detalhes de "1984"
    Then devo ver a avaliação "Uma leitura marcante."

  @E2-01
  Scenario: Encontrar o livro dentro da loja
    When eu consultar os detalhes de "1984"
    Then devo ver a seção "Literatura" e a prateleira "A1"

  @E2-02
  Scenario: Consultar informações pelo código de barras
    When eu consultar o código de barras "9788535914849"
    Then devo ver a sinopse "Uma sociedade sob vigilância."
    And devo ver o preço de 49.90 reais
    And devo ver a avaliação "Uma leitura marcante."

  @E2-03
  Scenario: Entrar na fila virtual
    When eu entrar na fila virtual
    Then minha posição na fila deve ser 1

  @E2-04
  Scenario: Agendar atendimento especializado
    Given que há um horário do livreiro "Carlos" em "2026-09-28T14:00:00+00:00"
    When eu agendar esse atendimento
    Then meu atendimento deve estar confirmado com "Carlos"

  @E2-05
  Scenario: Consultar funcionamento e lotação
    When eu consultar as informações da loja
    Then devo ver o horário "Seg–Sáb, 09h às 19h"
    And devo ver a lotação atual de 12 pessoas

  @E3-01
  Scenario: Reservar um exemplar disponível
    When eu reservar "1984" até "2026-09-29T18:00:00+00:00"
    Then minha reserva deve estar "pendente"
    And devem restar 2 exemplares de "1984"

  @E3-01
  Scenario: Não reservar um livro esgotado
    When eu tentar reservar "Livro Esgotado"
    Then a operação deve ser recusada
    And devem restar 0 exemplares de "Livro Esgotado"

  @E3-02
  Scenario: Alterar o prazo de retirada de uma reserva
    Given que reservei "1984" até "2026-09-29T18:00:00+00:00"
    When eu alterar o prazo para "2026-09-30T18:00:00+00:00"
    Then minha reserva deve ter prazo "2026-09-30T18:00:00+00:00"

  @E3-03
  Scenario: Avisar quando a reserva estiver separada
    Given que reservei "1984" até "2026-09-29T18:00:00+00:00"
    When a loja marcar minha reserva como pronta
    Then minha reserva deve estar "pronta"
    And devo receber uma notificação do tema "reservas"

  @E3-04
  Scenario: Cancelar uma reserva
    Given que reservei "1984" até "2026-09-29T18:00:00+00:00"
    When eu cancelar minha reserva
    Then minha reserva deve estar "cancelada"
    And devem restar 3 exemplares de "1984"

  @E4-01
  Scenario: Acumular os pontos informados na compra física
    When a loja registrar minha compra de "1984" com 20 pontos
    Then meu saldo de pontos deve ser 20

  @E4-02
  Scenario: Consultar saldo de fidelidade
    Given que comprei "1984" e recebi 20 pontos
    And que comprei "O Hobbit" e recebi 15 pontos
    When eu consultar minha fidelidade
    Then meu saldo de pontos deve ser 35

  @E4-03
  Scenario: Receber um cupom da loja
    When a loja conceder o cupom "LEITURA" com os termos "Desconto informado no caixa"
    Then devo ver o cupom "LEITURA"

  @E4-04
  Scenario: Apresentar o cartão digital
    When eu consultar minha fidelidade
    Then meu cartão digital deve identificar "ana"

  @E4-05
  Scenario: Receber aviso de pontos próximos da expiração
    Given que tenho 20 pontos válidos até "2026-09-30T12:00:00+00:00" com aviso em "2026-09-27T12:00:00+00:00"
    When o aplicativo processar os lembretes
    Then devo receber uma notificação do tema "fidelidade"

  @E5-01
  Scenario: Consultar a agenda de eventos
    Given que há um evento chamado "Conversa com autores"
    When eu consultar a agenda de eventos
    Then devo ver o evento "Conversa com autores"

  @E5-02
  Scenario: Garantir uma vaga no evento
    Given que há um evento chamado "Conversa com autores"
    When eu me inscrever nesse evento
    Then minha inscrição deve estar confirmada

  @E5-03
  Scenario: Receber lembrete de evento
    Given que há um evento chamado "Conversa com autores"
    And que estou inscrita nesse evento
    When o aplicativo processar os lembretes
    Then devo receber uma notificação do tema "eventos"

  @E5-04
  Scenario: Trocar opiniões no clube de leitura
    Given que há um clube chamado "Leituras compartilhadas"
    When eu participar desse clube e publicar "Gostei muito do livro do mês."
    Then o clube deve exibir minha opinião "Gostei muito do livro do mês."

  @E6-01
  Scenario: Guardar um livro na lista de desejos
    When eu adicionar "O Hobbit" à lista de desejos
    Then minha lista de desejos deve conter "O Hobbit"

  @E6-02
  Scenario: Consultar compras feitas na loja física
    Given que comprei "1984" e recebi 20 pontos
    When eu consultar meu histórico de compras
    Then meu histórico deve conter "1984"

  @E6-03
  Scenario: Configurar gêneros de interesse
    When eu escolher o gênero preferido "Fantasia"
    Then minhas recomendações devem incluir "O Hobbit"

  @E6-04
  Scenario: Receber apenas temas selecionados
    Given que aceito apenas notificações de "eventos"
    And que acompanho a reposição de "Livro Esgotado"
    When a loja repuser 2 exemplares de "Livro Esgotado"
    Then não devo receber notificações

  @E6-05
  Scenario: Reservar um presente com embrulho especial
    When eu reservar "O Hobbit" como presente até "2026-09-29T18:00:00+00:00"
    Then minha reserva deve ter embrulho especial

  @E1-08
  Scenario: Publicar uma avaliação visível a outros leitores
    When eu avaliar "1984" com nota 5 e comentário "Uma leitura excelente."
    Then outra cliente deve ver minha avaliação de "1984" com nota 5

  @E1-08
  Scenario: Recusar uma nota fora da escala
    When eu avaliar "1984" com nota 0 e comentário "Uma leitura excelente."
    Then a avaliação deve ser recusada com status 400
    And não deve existir uma avaliação minha de "1984"

  @E1-08
  Scenario: Impedir a repetição da avaliação pelo mesmo cliente
    When eu avaliar "1984" com nota 5 e comentário "Uma leitura excelente."
    And eu avaliar "1984" com nota 4 e comentário "Outra opinião."
    Then a avaliação deve ser recusada com status 409
    And deve existir apenas uma nova avaliação de "1984"
```

## Contrato HTTP

Todos os caminhos abaixo pertencem à sessão atual. POST/PATCH recebem JSON.
Sucesso retorna JSON; criação retorna 201. Erros retornam `{"erro": "..."}`:
400 para entrada inválida, 404 para recurso inexistente e 409 para
indisponibilidade ou conflito. Rotas administrativas não são públicas.

| Método | Caminho | Entrada / saída |
|---|---|---|
| GET | `/` | Página HTML |
| GET | `/api/estado` | Cliente, livros, reservas, fidelidade, loja, eventos, clubes, notificações e recomendações |
| GET | `/api/livros` | Query `q`, `genero`, `lancamentos=1`; lista de livros |
| GET | `/api/livros/<id>` | Detalhes, avaliações públicas e `ja_avaliou` da sessão atual |
| POST | `/api/livros/<id>/avaliacoes` | `nota` inteira de 1 a 5 e `texto` não vazio; avaliação criada com 201 |
| GET | `/api/codigo/<codigo>` | Detalhes pelo código de barras |
| POST | `/api/avisos-estoque` | `livro_id` |
| POST | `/api/reservas` | `livro_id`, `prazo`, `embrulho` opcional |
| PATCH | `/api/reservas/<id>` | `prazo` |
| POST | `/api/reservas/<id>/cancelar` | Reserva cancelada |
| POST | `/api/fila` | Posição na fila |
| POST | `/api/agendamentos` | `horario_id` |
| POST | `/api/eventos/<id>/inscricoes` | Inscrição no evento |
| POST | `/api/clubes/<id>/participar` | Adesão ao clube |
| POST | `/api/clubes/<id>/opinioes` | `texto` |
| POST | `/api/desejos` | `livro_id` |
| PATCH | `/api/preferencias` | `generos` e/ou `temas_notificacao` como listas de strings |

Uma avaliação pública contém `id`, `cliente` (identificador público de leitor),
`nota`, `texto` e `data`. A autoria interna vem da sessão, e o POST aceita apenas
`nota` e `texto`. Publicação repetida retorna 409; entrada inválida, 400;
livro inexistente, 404. As avaliações são compartilhadas entre os leitores;
o campo `ja_avaliou` é específico da sessão que consulta o livro.

## Referências metodológicas

- [lab05_tdd](https://github.com/Ckenz0/lab05_tdd): testes `pytest` para
  filtragem por autor, ano, gênero, combinação e ausência de resultados.
- [lab05_bdd](https://github.com/Ckenz0/lab05_bdd): Gherkin e separação entre
  `Catalogo` e `RepositorioLivros`; os seis primeiros cenários seguem os
  exemplos de descoberta e estoque. Os steps são adaptados a `pytest-bdd`
  para reunir os testes e evitar duplicar a especificação.

Esses repositórios orientam a técnica e a compatibilidade dos exemplos;
não substituem esta especificação como fonte de regras de negócio.
