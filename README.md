# Entrelinhas — Livraria

Aplicação Python/Flask para as 31 User Stories dos épicos E1–E6: descoberta
de livros, visita à loja, reservas, fidelidade, comunidade e preferências.

A fonte única de verdade é [docs/specs/livraria.md](docs/specs/livraria.md),
que contém as histórias, decisões de escopo, contrato HTTP e 36 cenários
Gherkin. O histórico inicial está em [docs/specs/tasks.md](docs/specs/tasks.md).

A aplicação utiliza **quatro camadas**: apresentação, aplicação, domínio e
infraestrutura. A separação e o fluxo de publicação de avaliações estão em
[Arquitetura multicamadas](docs/arquitetura.md).

## Avaliações de livros

Abra os detalhes de um livro, escolha uma nota de 1 a 5, escreva seu comentário
e selecione **Publicar avaliação**. A publicação fica visível para outros leitores.
Cada cliente, identificado pela sessão do navegador, pode publicar uma avaliação
por livro; não há edição ou exclusão. Se o envio falhar, o formulário preserva
o rascunho e mostra o erro para permitir uma nova tentativa.

## Executar neste workspace

O ambiente virtual já está instalado. No PowerShell, dentro desta pasta:

```powershell
.venv\Scripts\python.exe app.py
```

Abra <http://127.0.0.1:5000>. Para encerrar, pressione `Ctrl+C`.

## Instalar em outro ambiente

Requer Python 3.10 ou superior. Com Python instalado:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Alternativamente, usando [uv](https://docs.astral.sh/uv/):

```powershell
uv venv --python 3.13
uv pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Também é possível iniciar pelo Flask:

```powershell
.venv\Scripts\python.exe -m flask --app app run
```

## Testes e rastreabilidade

```powershell
.venv\Scripts\python.exe -m pytest -q
```

`test_livraria.py` reúne testes unitários, integração com o cliente HTTP
do Flask e os cenários BDD. Durante a coleta, o bloco Gherkin de
`livraria.md` é extraído para uma pasta temporária do sistema. Os steps
Given/When/Then executam o domínio real com relógio fixo e dados isolados.
Assim, editar um cenário na spec altera o BDD executado, sem uma cópia `.feature`.
Cada cenário tem uma etiqueta correspondente à sua User Story.

`test_avaliacoes.py` verifica domínio, casos de uso, repositórios reais, HTTP,
concorrência e fronteiras de dependência entre as camadas.
`test_interface_avaliacoes.py` verifica o novo formulário em desktop e celular.

Os quatro testes marcados `interface` usam um navegador real. São opcionais e
ficam como ignorados quando Playwright ou o navegador não estiver instalado.
Para executá-los com Chrome/Edge instalado:

```powershell
uv pip install playwright
.venv\Scripts\python.exe -m pytest -q -m interface
```

Em outros sistemas, informe o executável em `PLAYWRIGHT_BROWSER_EXECUTABLE`.
Os testes abrem o navegador em modo invisível e um servidor temporário
somente em localhost. Verificam desktop, celular, ações, texto seguro e
uma atualização simultânea à consulta periódica.

Os exemplos de [lab05_tdd](https://github.com/Ckenz0/lab05_tdd) fundamentam
os testes de filtragem e o contrato `filtrar_livros(livros, **criterios)`.
Os exemplos de [lab05_bdd](https://github.com/Ckenz0/lab05_bdd) fundamentam
os seis cenários iniciais e as classes `Catalogo` e `RepositorioLivros`.
Os cenários BDD foram adaptados de Behave para pytest-bdd.

O pytest fica na versão 8, compatível com pytest-bdd 8. O aviso de
depreciação de `maxsplit` do parser Gherkin no Python 3.13 é filtrado
especificamente em `pytest.ini`; os demais avisos permanecem habilitados.

## Estrutura

```text
docs/specs/
  livraria.md
  tasks.md
docs/
  arquitetura.md
  validacao-multicamadas.md
  validacao-mvc.md
controllers/
  __init__.py
  livraria_controller.py
services/
  __init__.py
  livraria_service.py
domain/
  __init__.py
  regras.py
  avaliacao.py
repositories/
  __init__.py
  livros.py
  estado.py
templates/
  index.html
static/
  css/app.css
  js/app.js
models/                 # compatibilidade com os imports anteriores
livraria.py              # compatibilidade com os exemplos anteriores
demonstracao.py          # composição dos dados ilustrativos
app.py                  # configuração e inicialização
test_livraria.py
test_avaliacoes.py
test_interface_avaliacoes.py
requirements.txt
pytest.ini
README.md
.gitignore
```

Os endereços HTTP e as regras anteriores foram preservados, com uma nova rota
para publicação de avaliações. `livraria.py` e `models/` reexportam os nomes
públicos anteriores para manter os exemplos e testes compatíveis.
Os resultados atuais estão no [registro de validação](docs/validacao-multicamadas.md).
O arquivo `docs/validacao-mvc.md` registra a verificação histórica da versão MVC.

## Uso e limites da demonstração

O catálogo inicia com livros, horários, eventos e um clube ilustrativos.
Cada sessão recebe uma compra física e um cupom fictícios para demonstrar
histórico, pontos, cartão digital, recomendações e notificações.

Os dados estão em memória: reiniciar o servidor apaga as alterações.
Cada navegador usa uma sessão própria; a sessão não implementa login.
O servidor inicia apenas em `127.0.0.1`, sem modo de depuração.

As notificações ficam no aplicativo. A página atualiza o estado a cada
15 segundos enquanto estiver visível; não há push, SMS ou envio de e-mail.
Prazos, pontos, validade e datas de aviso são dados informados, sem taxas
ou limites comerciais presumidos. Cupons não são resgatados online.

Reposição, separação de reservas, compras físicas e cupons são entradas
da loja por métodos de `Livraria`, não endpoints administrativos públicos.
Os testes exercitam essas entradas. Não há integração com caixa ou pagamentos.

A câmera exige suporte a `BarcodeDetector` e permissão do navegador;
localhost é aceito como contexto seguro. Código manual ou leitor USB
funciona pelo mesmo campo quando a câmera não estiver disponível.

Arquivos de ferramentas de desenvolvimento não fazem parte da entrega.
