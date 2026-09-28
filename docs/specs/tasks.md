# Plano de implementação da livraria

Objetivo: entregar as 30 User Stories e seus critérios de aceite usando
exclusivamente [livraria.md](livraria.md) como especificação funcional.

Arquitetura: domínio Python em memória, HTTP Flask e uma página HTML com
CSS e JavaScript locais. Testes unitários e BDD usam o mesmo serviço real.
O Gherkin executado é extraído da especificação, sem cópia mantida à parte.

## Restrições globais

- Preservar a estrutura de arquivos solicitada.
- Não calcular taxas de pontos, antecedências ou limites comerciais ausentes.
- Não incluir arquivos de ferramentas de desenvolvimento no repositório.
- Não disponibilizar operações da loja como ações de clientes.
- Isolar dados de clientes por sessão e validar antes de modificar o estado.
- Publicar em um remoto somente mediante solicitação explícita do usuário.

## Atenção na revisão

Estoque zero e reservas concorrentes; repetição de cancelamentos e inscrições;
datas inválidas e limites de expiração; JSON malformado e booleanos como
quantidade; dados de outro cliente e texto HTML em opiniões.

## Task 1 — Especificação e exemplos dos laboratórios

Arquivos: `docs/specs/livraria.md`, `docs/specs/tasks.md`.

- [x] Ler os exemplos de TDD e BDD dos repositórios fornecidos.
- [x] Preservar as 30 histórias e escrever critérios Gherkin rastreáveis.
- [x] Documentar entradas da loja e escolhas técnicas sem políticas presumidas.

## Task 2 — Catálogo e testes de descoberta

Arquivos: `test_livraria.py`, `livraria.py`.
Produz: `filtrar_livros(livros, **criterios)`, `RepositorioLivros(livros)`,
`Catalogo(repositorio)` e `Livraria(livros, agora=None)`.

- [x] Escrever testes dos cinco exemplos TDD e dos seis exemplos BDD.
- [x] Executar os testes antes da implementação e confirmar a falha esperada.
- [x] Implementar busca, estoque, gênero, lançamento e detalhes (E1, E2-01/02).
- [x] Executar `python -m pytest -q` e registrar o resultado.

## Task 3 — Serviços dos clientes e da loja

Arquivos: `test_livraria.py`, `livraria.py`.
Consome: `Livraria`, catálogo e relógio injetável da Task 2.
Produz: reservas, fila, horários, compras/pontos, cupons, eventos, clubes,
lista de desejos, preferências, recomendações e notificações.

- [x] Escrever testes de cada história e de estado/validação/isolamento.
- [x] Verificar falhas por funcionalidades ausentes.
- [x] Implementar E1-05/06, E2-03/04/05 e E3–E6 sem taxas presumidas.
- [x] Executar `python -m pytest -q` e registrar o resultado.

## Task 4 — BDD executável da especificação

Arquivo: `test_livraria.py`; entrada: bloco Gherkin de `livraria.md`.
Consome: serviço real das Tasks 2/3 e `pytest-bdd`.

- [x] Extrair o Gherkin para um arquivo temporário externo ao repositório.
- [x] Implementar Given/When/Then, incluindo os exemplos dos laboratórios.
- [x] Executar todos os cenários etiquetados por US.
- [x] Conferir que todas as 30 histórias têm cenários executados.

## Task 5 — Backend Flask e interface

Arquivos: `app.py`, `templates/index.html`, `test_livraria.py`.
Consome: domínio das Tasks 2/3. Produz: `create_app(livraria=None)` e
rotas da tabela HTTP; `app` utilizável pelo comando `flask --app app run`.

- [x] Escrever testes HTTP para consulta, reservas, preferências e erros.
- [x] Confirmar falhas antes de implementar as rotas.
- [x] Expor API JSON, criar sessão de cliente e tratar erros sem vazamentos.
- [x] Construir catálogo, detalhes, reserva/presente, loja, fidelidade,
      eventos/clube, desejos/histórico, preferências e notificações.
- [x] Conferir teclado, estados vazios, saída HTML segura e tela pequena.
- [x] Executar `python -m pytest -q` e verificar sintaxe do JavaScript.

## Task 6 — Entrega e verificação

Arquivos de apoio: `requirements.txt`, `.gitignore`, `README.md`.

- [x] Documentar instalação, execução, testes e limitações da demonstração.
- [x] Executar a suíte completa e conferir todos os endpoints.
- [x] Fazer revisão final de aderência à spec e corrigir falhas com regressão.
- [x] Atualizar este registro com os resultados observados.

## Registro de execução

- Projeto iniciado em uma pasta vazia; sem repositório Git local detectável.
- Implementação inicial feita no diretório solicitado, sem commits ou publicação.
- Gherkin e plano ficam nos caminhos da atividade; nenhum arquivo de ferramenta
  de desenvolvimento integra a entrega.
- Task 2: 10 testes falharam pela ausência do domínio e passaram após o catálogo.
- Task 3: 37 testes novos falharam por métodos ausentes; a implementação passou
  nos 47 testes acumulados, incluindo a disputa concorrente do último exemplar.
- Task 4: 33 cenários falharam por steps ausentes e passaram com os steps reais;
  80 testes acumulados. As 30 etiquetas de US estão cobertas.
- Task 5: 14 testes HTTP falharam antes do Flask/HTML; 94 testes passaram após
  a implementação e a sintaxe JavaScript foi validada com Node.
- Revisão independente: reproduzidos e corrigidos retorno de evento fora de
  ordem, JSON malformado em ações sem campos e datas não suportadas pelo Windows.
  Sete regressões passaram após falhar contra o código original.
- Interface: dois testes reais no Chrome verificaram os fluxos desktop/mobile
  e a atualização durante uma consulta pendente. Eles reproduziram e confirmaram
  as correções do botão da fila e da atualização perdida durante o polling.
- Decisão de compatibilidade: datas extremas são aceitas quando a plataforma
  consegue convertê-las; erro de conversão retorna 400, sem limite comercial novo.
- Revisão de escopo: opiniões públicas identificadas pertencem ao clube;
  os dados privados de clientes continuam isolados. Não foram adicionadas
  políticas comerciais ou integrações de produção.
- Task 6: verificação final em 27/09/2026: **103 testes passaram**, incluindo
  os 33 cenários Gherkin e os dois testes de navegador. Comando executado:
  `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --tb=short`.
  O cache foi desabilitado nessa execução por restrições de permissões do
  ambiente de verificação; isso não altera a coleta ou os testes.
- Compilação dos três arquivos Python e análise sintática do JavaScript
  concluídas sem erro. As capturas desktop e mobile foram inspecionadas.
- Rastreabilidade: 30 User Stories, 30 etiquetas cobertas, 33 cenários,
  nenhuma lacuna. Todos os itens do plano foram concluídos.
- Publicação posteriormente solicitada pelo usuário para
  `https://github.com/Ckenz0/lab05_sdd.git`, na branch `main`, com autoria
  exclusiva de Cauê Kenzo Adaniya, conforme a identidade configurada no Git.
  Ambientes, caches e arquivos de ferramentas de desenvolvimento são ignorados.
