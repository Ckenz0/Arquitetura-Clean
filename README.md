# Entrelinhas — Livraria

Aplicação Python/Flask para as 30 User Stories dos épicos E1–E6: descoberta
de livros, visita à loja, reservas, fidelidade, comunidade e preferências.

A fonte única de verdade é [docs/specs/livraria.md](docs/specs/livraria.md),
que contém as histórias, decisões de escopo, contrato HTTP e 33 cenários
Gherkin. O plano está em [docs/specs/tasks.md](docs/specs/tasks.md).

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

Os dois testes marcados `interface` usam um navegador real. São opcionais e
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
O BDD foi adaptado de Behave para pytest-bdd para respeitar a estrutura da atividade.

O pytest fica na versão 8, compatível com pytest-bdd 8. O aviso de
depreciação de `maxsplit` do parser Gherkin no Python 3.13 é filtrado
especificamente em `pytest.ini`; os demais avisos permanecem habilitados.

## Estrutura

```text
docs/specs/
  livraria.md
  tasks.md
templates/
  index.html
livraria.py
app.py
test_livraria.py
requirements.txt
pytest.ini
README.md
.gitignore
```

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
