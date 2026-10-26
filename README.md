# Entrelinhas — Livraria

Aplicação Python/Flask para as 32 User Stories dos épicos E1–E6: descoberta
de livros, visita à loja, reservas, fidelidade, comunidade e preferências.

A fonte única de verdade é [docs/specs/livraria.md](docs/specs/livraria.md),
que contém as histórias, decisões de escopo, contrato HTTP e 39 cenários
Gherkin. O histórico inicial está em [docs/specs/tasks.md](docs/specs/tasks.md).

A aplicação utiliza **Clean Architecture e DIP**: entidades e casos de uso
dependem de contratos internos, enquanto Flask e o armazenamento são conectados
na composição externa. Os dados são persistidos em **TXT**. Veja
[Clean Architecture](docs/arquitetura.md).

## Avaliações de livros

Abra os detalhes de um livro, escolha uma nota de 1 a 5, escreva seu comentário
e selecione **Publicar avaliação**. A publicação fica visível para outros leitores.
Cada cliente, identificado pela sessão do navegador, pode publicar uma avaliação
por livro. Para atualizar a própria nota e comentário, selecione **Editar avaliação**,
altere o formulário preenchido e use **Salvar alterações**. **Cancelar edição**
mantém a publicação original. Não há exclusão. Se o envio falhar, o formulário
preserva o rascunho e mostra o erro para permitir uma nova tentativa.

## Persistência em TXT

A execução normal cria `instance/livraria.txt`, com JSON legível em UTF-8 e versão
do formato. Catálogo, estoque, reservas, preferências, compras, pontos, eventos,
avaliações e os demais dados continuam disponíveis após reiniciar o servidor.
Os dados demonstrativos são criados somente na primeira inicialização.

A chave de sessão é mantida em `instance/chave_sessao.key`, para que o mesmo
navegador continue identificado depois de reiniciar. `SECRET_KEY` pode fornecer
uma chave externamente. O caminho do TXT pode ser configurado pela variável
`LIVRARIA_ARQUIVO_DADOS`; a chave local fica junto desse arquivo.

Alterações são gravadas por substituição atômica do TXT. Falhas de escrita
revertem a operação e preservam o arquivo anterior. Um arquivo inválido gera erro
sem ser sobrescrito pelos dados de demonstração. A pasta `instance/` e seus
arquivos de execução são locais e não integram o código entregue.

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

`test_clean.py` verifica edição, autoria, ports e fronteiras do núcleo.
`test_persistencia.py` usa TXT reais em diretórios temporários, incluindo leitura
em outro processo, falhas de gravação, rollback e recuperação da sessão.
`test_interface_edicao.py` verifica a edição e o reinício pelo navegador.

Os seis testes marcados `interface` usam um navegador real. São opcionais e
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
  validacao-clean.md
  validacao-multicamadas.md
  validacao-mvc.md
entities/
  regras.py
  avaliacao.py
use_cases/
  ports.py
  livraria.py
interface_adapters/
  http.py
  repositories.py
infrastructure/
  composition.py
  transactions.py
  txt.py
  web.py
templates/
  index.html
static/
  css/app.css
  js/app.js
models/                 # compatibilidade com os imports anteriores
domain/                 # compatibilidade das regras
services/               # compatibilidade dos serviços
repositories/           # compatibilidade dos repositórios
controllers/            # compatibilidade do registro HTTP
livraria.py              # compatibilidade com os exemplos anteriores
demonstracao.py          # composição dos dados ilustrativos
app.py                  # configuração e inicialização
test_livraria.py
test_avaliacoes.py
test_interface_avaliacoes.py
test_clean.py
test_persistencia.py
test_interface_edicao.py
requirements.txt
pytest.ini
README.md
.gitignore
```

Os endereços HTTP anteriores foram preservados, com uma nova rota PATCH para
editar a avaliação própria. Os módulos de compatibilidade preservam os imports
dos exemplos anteriores. Os resultados atuais estão no
[registro de validação](docs/validacao-clean.md); os registros MVC e multicamadas
descrevem as versões anteriores.

## Uso e limites da demonstração

O catálogo inicia com livros, horários, eventos e um clube ilustrativos.
Cada sessão recebe uma compra física e um cupom fictícios para demonstrar
histórico, pontos, cartão digital, recomendações e notificações.

Os dados são persistidos em TXT. Cada navegador usa uma sessão própria;
a sessão não implementa login ou autenticação de contas.
O servidor inicia apenas em `127.0.0.1`, sem modo de depuração.

Para executar a factory com dados isolados em memória, use
`create_app(arquivo_dados=None)`; uma livraria injetada em `create_app(livraria)`
também preserva o isolamento dos testes. O módulo pode ser importado sem criar
arquivos; a composição ocorre ao chamar a factory ou iniciar o servidor.

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
