# Validação Clean, TXT e edição de avaliações

Verificação local em 25/10/2026, com Python 3.12.15, Flask 3.1.3,
pytest 8.4.2, pytest-bdd 8.1.0 e Playwright 1.64.1 com Chrome instalado.

## Execução

```powershell
.venv\Scripts\python.exe -m pytest -q
```

- Base multicamadas: 143 testes passaram.
- Evolução Clean: **194 testes passaram**, sem testes ignorados.
- Os testes incluem 39 cenários Gherkin da especificação e seis casos de navegador.
- Os 21 testes novos de núcleo, edição e HTTP falharam antes da implementação.
- Os testes de persistência observaram falhas por funcionalidades ausentes e
  verificam arquivos reais em diretórios temporários.
- Os dois testes de interface de edição falharam pela ausência da ação Editar;
  os três cenários BDD novos falharam por ausência dos steps antes da integração.

## Clean Architecture e DIP

- Entidades e casos de uso não importam Flask, adaptadores, infraestrutura,
  serialização JSON, caminhos de arquivos ou locks.
- Os casos de uso recebem `LivrosPort`, `EstadoPort` e `TransacaoPort`.
- A mesma edição funciona com transação em memória e com TXT, sem alterar o núcleo.
- Um processo separado importa o núcleo sem carregar as camadas externas.
- Os imports públicos anteriores e os fluxos já existentes continuam cobertos.

## Dados e recuperação

- Um TXT real preserva catálogo, estoque, clientes, preferências, desejos,
  reservas, acompanhamentos, fila, horários, eventos, clubes, opiniões,
  compras, pontos, cupons, notificações e avaliações.
- Conjuntos de inscritos, membros, interessados e destinatários avisados são
  reconstruídos; lembretes e avisos processados não são duplicados após recarregar.
- A avaliação editada também é recuperada por outro processo Python.
- Duas instâncias no mesmo processo leem os dados mais recentes e preservam
  publicações concorrentes. Consultas do catálogo também atualizam seu estado.
- Erros de gravação preservam o TXT anterior e restauram os dados de trabalho;
  a API retorna 503 e não confirma uma edição que o disco recusou.
- A primeira sessão só é confirmada após gravar seus dados demonstrativos.
- TXT vazio, inválido ou de versão incompatível é recusado sem sobrescrita.
- Livros armazenados no histórico de compras também têm seus campos obrigatórios
  validados. Ausência, tipo incorreto ou gênero vazio geram 503, preservando os
  bytes do TXT e impedindo que outra operação regrave o estado incompatível.
- Importar a factory não cria dados de execução. Testes usam memória ou pastas
  temporárias, sem acessar os dados normais da aplicação.

## Edição e interface

- Apenas a sessão autora pode editar, preservando id, autor público e data original.
- Nota e comentário são validados; booleanos, valores fora da escala, tipos
  incorretos e tentativa de escolher outra autoria são recusados.
- O formulário abre preenchido; cancelar mantém a publicação original.
- Falha de envio mantém nota e comentário para tentar novamente.
- A resposta do PATCH confirma a alteração, mesmo com a consulta de detalhes
  indisponível. O comentário editado é exibido como texto seguro.
- Os fluxos de desktop e celular reiniciam o servidor e recuperam a avaliação
  própria com o mesmo navegador. Outra sessão visualiza o conteúdo público,
  mas não recebe ação para editar a avaliação alheia.
- Não houve transbordamento horizontal nas larguras verificadas.

## Limites

A concorrência testada cobre threads e instâncias no mesmo processo.
Não há coordenação entre múltiplos workers, autenticação de contas ou exclusão
de avaliações. Os arquivos de dados e a chave de sessão ficam fora da entrega.

O comportamento está em [livraria.md](specs/livraria.md), e as responsabilidades
estão em [Clean Architecture](arquitetura.md).
