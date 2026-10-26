# Histórico da validação multicamadas e das avaliações

Este registro descreve a versão anterior com armazenamento em memória.
A verificação atual está em [Validação Clean](validacao-clean.md).

Verificação local em 25/10/2026, com Python 3.12.15, Flask 3.1.3,
pytest 8.4.2, pytest-bdd 8.1.0 e Playwright 1.64.1 com Chrome instalado.

## Suíte automatizada

```powershell
.venv\Scripts\python.exe -m pytest -q
```

- Base MVC: 104 testes passaram.
- Evolução multicamadas: **143 testes passaram**, sem testes ignorados.
- Os 34 testes novos de regras, casos de uso, armazenamento e HTTP falharam
  contra a base antes da implementação e passaram depois da nova funcionalidade.
- Os dois testes novos de navegador falharam pela ausência do formulário e
  passaram após a integração da interface.
- Há 36 cenários Gherkin executados a partir da especificação, incluindo os
  três novos cenários de publicação, nota inválida e duplicidade.
- Os quatro testes de navegador verificam os fluxos existentes e o formulário
  de avaliação em desktop e celular.

## Garantias verificadas

- Nota inteira de 1 a 5 e comentário obrigatório; recusa de booleanos,
  floats, textos como nota e comentários vazios ou de tipo inválido.
- Uma publicação por cliente/livro, inclusive com duas chamadas concorrentes.
- Publicação visível para outras sessões, sem expor a autoria interna na avaliação.
- Dois clientes podem avaliar o mesmo livro; duas aplicações não compartilham dados.
- Repositórios reais injetados recebem a avaliação e permitem recuperá-la em
  outro serviço que compartilhe as mesmas dependências.
- Fronteiras estáticas: domínio não importa Flask, serviços ou repositórios;
  infraestrutura não importa apresentação ou serviços; serviços não importam HTTP;
  controladores não importam implementações de repositórios.
- Respostas HTTP 201, 400, 404 e 409 conforme o contrato e retorno JSON para erros.
- Interface mantém o rascunho ao falhar o envio, permite nova tentativa e
  apresenta confirmação após publicar. A publicação continua visível após recarregar.
- A confirmação usa a resposta do POST: uma indisponibilidade na consulta de
  detalhes não apresenta uma publicação já aceita como falha nem permite reenviá-la.
- Comentários com HTML e JavaScript aparecem como texto, sem execução no navegador.
- Não há transbordamento horizontal da página ou do diálogo nas larguras testadas.

## Limites

Os dados continuam em memória; o isolamento é por instância do serviço.
Os testes de concorrência cobrem threads no mesmo processo, não múltiplos servidores.
A sessão é uma identificação da demonstração, sem autenticação de contas.
Não foram adicionados banco de dados, edição ou exclusão de avaliações.

O comportamento funcional está em [livraria.md](specs/livraria.md), e a separação
das responsabilidades está em [Arquitetura multicamadas](arquitetura.md).
