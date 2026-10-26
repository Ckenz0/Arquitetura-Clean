# Histórico da validação MVC

Este registro corresponde à base MVC anterior à arquitetura multicamadas.
A verificação atual está em [Validação Clean](validacao-clean.md).

Verificação local em 25/10/2026, com Python 3.12.15, Flask 3.1.3, pytest 8.4.2
e pytest-bdd 8.1.0. Playwright instalado para executar os testes no navegador.

## Suíte automatizada

```powershell
.venv\Scripts\python.exe -m pytest -q
```

- Antes da refatoração: **103 testes passaram**.
- Após a separação MVC: **104 testes passaram**, sem testes ignorados.
- A suíte inclui os 33 cenários Gherkin da especificação e dois testes de navegador.
- O teste adicional verifica se o HTML referencia CSS e JavaScript e se esses
  arquivos são entregues com resposta 200, conteúdo não vazio e tipo correto.
  Ele falhou na versão anterior à extração e passou com os arquivos em `static/`.

Os testes de navegador verificam busca e filtros, detalhes, código manual,
reserva com embrulho, alteração de prazo, cancelamento, fila, agendamento,
eventos, clube, preferências, desejos, avisos e notificações. Também verificam
a largura da página em celular, saída segura de texto e atualização da
interface durante uma consulta pendente.

## Verificações da separação MVC

- Importar `models.livraria` não carrega Flask.
- Duas chamadas a `create_app()` produzem Models distintos: alterar o estoque
  de uma aplicação não altera o estoque da outra.
- Erros globais 404 e 405 continuam retornando JSON após a extração do Blueprint.
- O código do domínio foi movido integralmente; os estilos e o JavaScript
  foram extraídos do template, sem alteração de comportamento.

O comportamento funcional e o contrato HTTP permanecem definidos em
[livraria.md](specs/livraria.md). As responsabilidades estão descritas em
[Arquitetura da aplicação](arquitetura.md).
